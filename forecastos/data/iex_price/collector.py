from pathlib import Path
import pandas as pd
import requests
from ..downloader import FileDownloader, TIMEOUT_SEC
from .tops_trade_scanner import scan_trades

HIST_URL = 'https://iextrading.com/api/1.0/hist'

# Enough to identify and download a capture; the API returns more than this.
CATALOG_COLS = ['date', 'feed', 'version', 'protocol', 'size_bytes', 'link']


class IEXPrice:
    """Daily OHLCV bars built from IEX's public TOPS capture archive."""

    @classmethod
    def get_df(
        cls,
        start: str = None,
        end: str = None,
        data_dir: str = None,
        cleanup: bool = True,
    ) -> pd.DataFrame:
        """Daily OHLCV bars for every trading session in [start, end].

        Downloads one capture per session, so a wide range is a long job.
        Capture sizes vary - `fetch_tops_catalog` reports `size_bytes` per
        session, so check there before committing to a range. Download time
        depends on your connection; scanning runs ~60s per 10 GB.

        Args:
            start: earliest session as an ISO date string, 'YYYY-MM-DD'. None
                means no lower bound - the archive reaches back to 2016.
            end: latest session, same format. None means no upper bound.
                Both bounds are inclusive.
            data_dir: where capture files are downloaded. Defaults to ./data,
                resolved against the working directory as of this call.
            cleanup: If True, delete each capture file once it has been parsed.

        Returns:
            One row per symbol per session: date, symbol, open, high, low,
            close, volume. `date` is an ISO date string, 'YYYY-MM-DD'.

        Raises:
            ValueError: no session falls in the range.
        """
        catalog = cls.fetch_tops_catalog(start, end)
        if catalog.empty:
            raise ValueError(f'no TOPS sessions between {start} and {end}')

        downloader = FileDownloader(data_dir or Path.cwd() / 'data', cleanup)

        data = []
        for entry in catalog.to_dict('records'):
            with downloader.fetch(entry['link'], _capture_filename(entry)) as path:
                trades = scan_trades(path, entry['version'], entry['date'])
                data.append(_to_daily_bars(trades, entry['date']))

        return pd.concat(data, ignore_index=True)

    @classmethod
    def fetch_tops_catalog(cls, start: str = None, end: str = None) -> pd.DataFrame:
        resp = requests.get(HIST_URL, timeout=TIMEOUT_SEC)
        resp.raise_for_status()

        # The archive is keyed by session; flatten to one row per capture.
        rows = [entry for entries in resp.json().values() for entry in entries]
        df = pd.DataFrame(rows)

        # `size` arrives as text. Cast before it is used as a sort key below -
        # compared as strings, the 242-byte stub "242" outranks "11509902176".
        df['size_bytes'] = df['size'].astype('int64')
        df = df[df['feed'] == 'TOPS']

        # The archive keys sessions as 'YYYYMMDD'. Restate them as ISO here, at
        # the one point they enter the module, so everything downstream - the
        # range filter, capture filenames, the bars - speaks a single format.
        dates = pd.to_datetime(df['date'], format='%Y%m%d')
        df['date'] = dates.dt.strftime('%Y-%m-%d')

        # Either bound may be None, meaning no limit on that side
        df = df[dates.between(
            pd.Timestamp(start) if start else dates.min(),
            pd.Timestamp(end) if end else dates.max(),
        )]

        # Aug-Nov 2017 published 1.5 and 1.6 for the same session (identical
        # trades, different wire format), and rows for the retired feed can be
        # 242-byte stubs. Sorting by largest size first keeps the real capture
        # even when the newer feed is the stub; version breaks any remaining tie.
        df = (
            df.sort_values(['size_bytes', 'version'], ascending=False)
            .drop_duplicates(subset='date', keep='first')
            .sort_values('date', ascending=False)
            .reset_index(drop=True)
        )

        return df[CATALOG_COLS]


def _capture_filename(entry: dict) -> str:
    """Name captures by session rather than by the opaque tail of the link."""
    return (
        f"{entry['date']}_"
        f"{entry['protocol']}_"
        f"{entry['feed']}{entry['version']}.pcap.gz"
    )


def _to_daily_bars(trades: pd.DataFrame, date: str) -> pd.DataFrame:
    """Collapse one session's trades into a bar per symbol.

    Prices and volume come from different sets of trades. Only price-eligible
    trades may set open, high, low or close, while every trade counts toward
    volume whatever its flags.
    """
    # Volume first, over every trade, before any of it is filtered away.
    volume = trades.groupby('symbol')['size'].sum().rename('volume')

    # filter out price ineligible trades (extended hours / odd lot)
    priced = trades[trades['price_eligible']].sort_values(
        ['symbol', 'ts', 'trade_id'])

    bars = (
        # sort=False: already ordered by symbol, so skip re-sorting the groups
        priced.groupby('symbol', sort=False)
        .agg(
            open=('price', 'first'),
            high=('price', 'max'),
            low=('price', 'min'),
            close=('price', 'last'),
        )
        .join(volume, how='inner')
        .reset_index()
    )

    bars.insert(0, 'date', date)
    return bars
