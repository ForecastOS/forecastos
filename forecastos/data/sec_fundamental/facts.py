"""Reading the companyfacts archive into one fact per row.

The archive holds one JSON member per filer, nested
taxonomy -> tag -> unit -> [facts]. Two filters run here, before any DataFrame
is built:

  - only tags the schema can reference, ~150 against a median of ~270 us-gaap
    tags per company;
  - only 10-K and 10-Q facts, which doubles as the entity filter - funds,
    trusts and shells file N-CSR and 10-D, never a 10-K, so they drop out
    without needing the 1.4 GB submissions archive.

Members are read out of the zip in place: one company is a seek and a single
deflate stream, rather than 17 GB of disk to unpack the whole thing.
"""

import json
import zipfile
from typing import Optional

import numpy as np
import pandas as pd

# Everything else describes a period we cannot place or an entity we are not
# collecting.
WANTED_FORMS = frozenset({'10-K', '10-Q'})

# `dei` carries EntityCommonStockSharesOutstanding, the fallback share count.
WANTED_TAXONOMIES = ('us-gaap', 'dei')

FACT_COLS = [
    'cik', 'tag', 'start', 'end', 'val',
    'accn', 'fy', 'fp', 'form', 'filed', 'frame',
]


def read_facts(
    archive_path,
    tags: frozenset,
    ciks: Optional[list] = None,
) -> pd.DataFrame:
    """Every fact in the archive that `tags` names, as one long frame.

    Args:
        archive_path: path to companyfacts.zip.
        tags: XBRL tags to keep. The rest is discarded before becoming a row -
            the single largest reduction in the pipeline.
        ciks: restrict to these filers. None reads all ~19k.

    Returns:
        One row per fact: cik, tag, start, end, val, accn, fy, fp, form, filed,
        frame. Dates are datetime64; `cik` is the padded 10-digit string.
    """
    with zipfile.ZipFile(archive_path) as archive:
        names = ([_member_name(cik) for cik in ciks] if ciks
                 else [n for n in archive.namelist() if n.endswith('.json')])

        frames = []
        for i, name in enumerate(names, 1):
            frames.append(_read_member(archive, name, tags))
            if i % 250 == 0 or i == len(names):
                print(f'\r  parsed {i} / {len(names)} companies', end='')
    print()

    # Companies reporting none of the wanted tags contribute an empty frame,
    # whose all-null columns would otherwise decide the result's dtypes.
    frames = [f for f in frames if not f.empty] or [pd.DataFrame(columns=FACT_COLS)]
    return _clean(pd.concat(frames, ignore_index=True))


def _read_member(
    archive: zipfile.ZipFile,
    name: str,
    tags: frozenset,
) -> pd.DataFrame:
    """Decompress one company's member and flatten the tags we want out of it."""
    try:
        payload = archive.read(name)
    except KeyError:
        # A filer with no XBRL facts has no member - a data answer, not a
        # corrupt archive.
        raise ValueError(
            f'{name} is not in the archive - that filer has no XBRL facts'
        ) from None

    return _to_facts(json.loads(payload), tags, _pad_cik(name))


def _pad_cik(value) -> str:
    """The digits of `value`, zero-padded to the 10 SEC keys filers by."""
    digits = ''.join(c for c in str(value) if c.isdigit())
    if not digits:
        raise ValueError(f'not a cik: {value!r}')
    return digits.zfill(10)


def _member_name(cik) -> str:
    """Members are named by the padded CIK, e.g. 'CIK0000320193.json'."""
    return f'CIK{_pad_cik(cik)}.json'


def _to_facts(company: dict, tags: frozenset, member_cik: str) -> pd.DataFrame:
    """Flatten one company into a row per fact, keeping only wanted tags.

    The tag and form tests run against the parsed dicts, before any row is
    built, which keeps the intermediate about a quarter of its full size.
    """
    records, tag_labels, counts = [], [], []

    # Some members are an empty object - a filer SEC has an entry for and no
    # facts under.
    facts = company.get('facts', {})
    for taxonomy in WANTED_TAXONOMIES:
        for tag, body in facts.get(taxonomy, {}).items():
            if tag not in tags:
                continue
            for unit_facts in body.get('units', {}).values():
                kept = [f for f in unit_facts if f.get('form') in WANTED_FORMS]
                if not kept:
                    continue
                records.extend(kept)
                tag_labels.append(tag)
                counts.append(len(kept))

    if not records:
        return pd.DataFrame(columns=FACT_COLS)

    # One batch to pandas, with the tag repeated over its own run afterwards.
    # A row dict per fact would copy every record back through Python.
    df = pd.DataFrame(records)
    df['tag'] = np.repeat(np.array(tag_labels, dtype=object), counts)

    # From the member name, which is authoritative - the CIK field is a string
    # in about a quarter of members. Padded so a CIK read back from a csv still
    # joins against SEC's ticker mappings.
    df['cik'] = member_cik

    # reindex, not a column select: `start` and `frame` are absent from most
    # records and can be missing from a company entirely, and the shape should
    # not depend on which company was asked for.
    return df.reindex(columns=FACT_COLS)


def _clean(facts: pd.DataFrame) -> pd.DataFrame:
    """Type the columns once, here, rather than per statement downstream."""
    for col in ('start', 'end', 'filed'):
        facts[col] = pd.to_datetime(facts[col], errors='coerce')

    facts['val'] = pd.to_numeric(facts['val'], errors='coerce')

    # A missing fiscal year is no reason to drop the fact - `start`/`end` carry
    # the period, `fy` only labels the filing it arrived in.
    facts['fy'] = facts['fy'].fillna(0).astype('int64')

    return facts
