"""Extract trades from an IEX TOPS capture.

A capture is a gzipped pcap of one trading day - quotes, system messages and
trades interleaved, over 10 GB when busy - of which trades are a small part.

Parsing message by message spends almost all its time decoding messages it then
discards (~15 min on ~14 GB). This module instead treats the decompressed stream
as bytes: every trade report opens with the same three-byte signature, so it
scans for that literal, copies the matching records, and reinterprets them as a
numpy record array in one pass (~60 sec on ~10 GB).

The tradeoff: packet headers are skipped, so IEX-TP `seq` is unavailable.
`trade_id` is monotonic and orders trades just as well.
"""

import gzip
import re
import time
from pathlib import Path
import numpy as np
import pandas as pd


# --- TOPS specification consts --- #
# Links to TOPS specification docs:
#   current (1.6 as of 2026-08) => https://www.iex.io/documents/iex-tops-specification
#   1.5 => https://www.iex.io/documents/tops-v1-5

# A trade report is length-prefixed ("<length><type>"): 38 bytes on TOPS 1.6, 42
# on 1.5, type 'T' in both. That pair is a far more selective scan target than
# the bare 0x54, which occurs constantly inside prices, sizes and timestamps.
TRADE_SIGNALS = {
    '1.6': b'\x26\x00T',
    '1.5': b'\x2a\x00T'
}

# Prices are fixed point with 4 implied decimals.
PRICE_SCALE = 10_000

# Only the first 38 bytes of a match are copied, so 1.5's four trailing bytes
# fall away and both versions share this dtype. Verified against IEX-TP framing
# on 2017-09-06, published in both formats: the 890,789 leading-38-byte records
# are identical between the two, and 1.5's trailing bytes are zero in every one.
TRADE_REC = np.dtype({
    'names':    ['flags', 'ts', 'sym', 'size', 'price', 'trade_id'],
    'formats':  ['u1', '<i8', 'S8', '<u4', '<i8', '<i8'],
    'offsets':  [1, 2, 10, 18, 22, 30],
    'itemsize': 38,
})

LEN_PREFIX = 2  # bytes of "<length>" ahead of the message body
REC_SPAN = LEN_PREFIX + TRADE_REC.itemsize

# The sale condition flags that bear on pricing: TOPS's trade eligibility
# guidelines require both to be 0 for last-sale and for high/low eligibility.
# Volume has no such rule - every trade counts toward it. See the
# "Trade Eligibility Guidelines" section in the TOPS specification docs.
PRICE_ELIGIBLE_SALE_CONDITION_FLAGS = {
    'extended_hours': 0x40,
    'odd_lot': 0x20,
}

# All above flags must be false (0) for trade to be price eligible
PRICE_ELIGIBLE_MASK = sum(PRICE_ELIGIBLE_SALE_CONDITION_FLAGS.values())

# --- scan tuning ------------------------------------------------------------
SCAN_CHUNK = 8 << 20
SCAN_TAIL = 64  # > longest trade message + prefix, so none is lost at a chunk edge

# Timestamps are wall-clock trade times, so they sit within a day of the session
# date. Two days of slack absorbs timezone and pre/post-market spread.
SESSION_SLACK_NS = 2 * 86_400 * 1_000_000_000


def scan_trades(
    path: Path,
    tops_version: str,
    date: str,
    progress_every: int = 10
) -> pd.DataFrame:
    """Every trade in the capture at `path`, one row each.

    Looks up the trade signature for `tops_version`, carves every record that
    matches it, then reinterprets those bytes as trades.

    Args:
        path: gzipped pcap capture covering a single session.
        tops_version: version the capture was published under, spelled as the
            catalog spells it - '1.6' or '1.5'. Selects the trade signature.
        date: session the capture covers, as an ISO date string, 'YYYY-MM-DD'.
            Only bounds the timestamp plausibility check that rejects false
            positives.
        progress_every: print progress every N chunks; 0 to stay silent.

    Returns:
        One row per trade: symbol, ts (tz-aware UTC), size, price, trade_id, a
        bool per PRICE_ELIGIBLE_SALE_CONDITION_FLAGS entry, and price_eligible.
        Every trade is returned, odd lots and the 08:00-17:00 ET extended
        session included, so filter on `price_eligible` for prices - never for
        volume, which counts them all.

    Raises:
        ValueError: unknown `tops_version`. Field offsets and flag bits are
            version-specific, so an unrecognized one is not safe to guess at.
    """
    raw = _carve(path, _get_trade_sig(tops_version), progress_every)
    return _decode(raw, *_session_bounds(date))


def _get_trade_sig(tops_version: str) -> bytes:
    try:
        return TRADE_SIGNALS[tops_version]
    except KeyError:
        raise ValueError(
            f'unsupported TOPS version {tops_version!r}; '
            f'known: {", ".join(sorted(TRADE_SIGNALS))}'
        ) from None


def _carve(path: Path, sig: bytes, progress_every: int) -> bytes:
    """Stream the capture and concatenate the body of every signature match.

    Returns one flat bytestring of fixed-width records, ready for `np.frombuffer`
    to reinterpret without copying again.
    """
    pattern = re.compile(re.escape(sig))
    total = Path(path).stat().st_size
    blobs, carry = [], b''
    started = time.time()

    with gzip.open(path, 'rb') as f:
        chunk_no = 0
        while True:
            block = f.read(SCAN_CHUNK)
            last = not block
            buf = carry + block

            # a match starting inside the final SCAN_TAIL bytes may be truncated;
            # defer it to the next round, where `carry` presents it in full
            limit = len(buf) if last else max(0, len(buf) - SCAN_TAIL)

            # skip the length prefix and take exactly TRADE_REC.itemsize bytes,
            # so every record is the same width whatever the TOPS version
            records = [buf[o + LEN_PREFIX:o + REC_SPAN]
                       for o in (m.start() for m in pattern.finditer(buf))
                       if o < limit and o + REC_SPAN <= len(buf)]
            if records:
                blobs.append(b''.join(records))

            if last:
                break
            carry = buf[limit:]

            chunk_no += 1
            if progress_every and chunk_no % progress_every == 0:
                _print_progress(f.fileobj.tell(), total, started)

    return b''.join(blobs)


def _session_bounds(date: str) -> tuple[int, int]:
    """Plausible timestamp window, in ns since the epoch, for session `date`."""
    midnight = pd.Timestamp(date).normalize()
    if midnight.tz is not None:
        midnight = midnight.tz_convert(None)
    return midnight.value - SESSION_SLACK_NS, midnight.value + SESSION_SLACK_NS


def _decode(raw: bytes, ts_lo: int, ts_hi: int) -> pd.DataFrame:
    """Reinterpret carved bytes as records, drop false positives, build the frame."""
    trades = np.frombuffer(raw, dtype=TRADE_REC)

    # ~30 false positives per million hits survive the byte signature; reject them
    # on field plausibility. Deliberately no symbol-charset test — constraining it
    # silently dropped every "GSAH=" trade, and `=` `^` `#` `*` are all legal.
    trades = trades[(trades['size'] > 0) & (trades['price'] > 0)
                    & (trades['ts'] > ts_lo) & (trades['ts'] < ts_hi)]

    # ns since the POSIX epoch on the wire; surfaced as tz-aware UTC so callers
    # need not rediscover the unit and epoch. int64 -> datetime64 is exact.
    return pd.DataFrame({
        'symbol': np.char.strip(trades['sym']).astype(str),
        'ts': pd.to_datetime(trades['ts'].astype('int64'), unit='ns', utc=True),
        'size': trades['size'].astype('int64'),
        'price': trades['price'] / PRICE_SCALE,
        **{name: (trades['flags'] & bit) != 0
           for name, bit in PRICE_ELIGIBLE_SALE_CONDITION_FLAGS.items()},
        'price_eligible': (trades['flags'] & PRICE_ELIGIBLE_MASK) == 0,
        'trade_id': trades['trade_id'].astype('int64'),
    })


def _print_progress(done: int, total: int, started: float) -> None:
    elapsed = time.time() - started
    eta = elapsed * (total / done - 1) if done else 0
    print(f"\r  {done / 1e9:5.2f}/{total / 1e9:.2f} GB ({done / total:4.0%})"
          f"  {elapsed:5.0f}s elapsed, ~{eta:.0f}s left", end="")
