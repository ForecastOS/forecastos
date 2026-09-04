"""Turning reported facts into datapoint columns.

Facts arrive one per row. Pivoting them gives a row per filing-period with a
column per tag - the shape datapoints are defined over - so a datapoint is
numpy over whole columns rather than a Python call per row. Across ~45
datapoints and millions of rows, that difference dominated the pipeline.

The tag columns live only between the pivot and the evaluation; nothing
downstream reads them.
"""

import numpy as np
import pandas as pd

# A mostly-empty row is rarely a real statement - usually one figure disclosed
# for a period the rest of the filing does not cover.
MAX_NULL_SHARE = 0.5


def extract(facts: pd.DataFrame, statement) -> pd.DataFrame:
    """One row per filing-period, with a column per datapoint.

    Args:
        facts: the long frame from `read_facts`.
        statement: a `StatementSchema`.

    Returns:
        The statement's key columns, SEC's `frame` label where it assigned one,
        and a column per datapoint. Rows more than half null are dropped.
    """
    names = statement.datapoint_names
    wide = _pivot(facts, statement)
    if wide.empty:
        return wide.reindex(columns=list(wide.columns) + names)

    for datapoint, sums in statement.mappings.items():
        wide[datapoint] = _datapoint_values(wide, sums)

    _apply_overrides(wide, statement)

    # Calculations derive a datapoint from other datapoint columns and only
    # fill where the mapped value was null. Declaration order matters - one can
    # read a column another writes.
    for datapoint, sums in statement.calculations.items():
        derived = pd.Series(
            _datapoint_values(wide, sums), index=wide.index)
        wide[datapoint] = (wide[datapoint].fillna(derived)
                           if datapoint in wide.columns else derived)

    return wide[wide[names].isna().mean(axis=1) <= MAX_NULL_SHARE]


def _pivot(facts: pd.DataFrame, statement) -> pd.DataFrame:
    """Facts for one statement, reshaped to a row per filing-period."""
    keys = statement.key_columns

    rows = facts[facts['tag'].isin(statement.required_tags)]
    # A fact missing part of its key cannot be placed on a timeline.
    rows = rows.dropna(subset=keys + ['tag', 'val'])
    # One tag can appear twice under a key if reported in two units. First wins.
    rows = rows.drop_duplicates(subset=keys + ['tag'], keep='first')

    if rows.empty:
        return pd.DataFrame(columns=keys + ['frame'])

    return (rows.pivot(index=keys, columns='tag', values='val')
            .rename_axis(None, axis=1)
            # `frame` belongs to the period, not to any one tag, so it is
            # collapsed alongside the pivot instead of becoming a column in it.
            .join(rows.groupby(keys, sort=False)['frame'].first())
            .reset_index())


def _apply_overrides(wide: pd.DataFrame, statement) -> None:
    """Recompute the few CIKs whose filings need their own tag order.

    Each override already carries the shared sums as a fallback (see
    `_compile_statement`). Only the overridden company's rows are touched - a
    few thousand out of millions, cheap enough to redo rather than thread
    through the pass above.
    """
    for cik, datapoints in statement.overrides.items():
        mask = (wide['cik'] == cik).to_numpy()
        rows = wide.loc[mask]
        for datapoint, sums in datapoints.items():
            wide.loc[mask, datapoint] = _datapoint_values(rows, sums)


def _datapoint_values(frame: pd.DataFrame, sums) -> np.ndarray:
    """First sum that yields a value, per row."""
    out = np.full(len(frame), np.nan)
    for sum_ in sums:
        missing = np.isnan(out)
        # Every row filled - later sums have nothing left to do.
        if not missing.any():
            break
        out = np.where(missing, _sum_values(frame, sum_), out)
    return out


def _sum_values(frame: pd.DataFrame, sum_) -> np.ndarray:
    """Total of the sum's terms, or null where there is no total to give."""
    terms = np.vstack([_term_values(frame, t) for t in sum_.terms])

    if sum_.require_all_terms:
        # A missing term propagates through the total, so no partial sums.
        return terms.sum(axis=0)

    # A missing term contributes nothing; the total fails only if all are.
    return np.where(np.isnan(terms).all(axis=0), np.nan, np.nansum(terms, axis=0))


def _term_values(frame: pd.DataFrame, tags) -> np.ndarray:
    """First of `tags` that the filing reported, per row."""
    out = np.full(len(frame), np.nan)

    for tag in tags:
        if tag.name in frame.columns:
            col = frame[tag.name].to_numpy(dtype='float64') * tag.multiplier
        else:
            # A company that never uses this tag is normal - that is what
            # the next one in the list is for.
            col = np.full(len(frame), np.nan)

        if tag.default is not None:
            col = np.where(np.isnan(col), tag.default, col)

        if tag.ignore_if_zero:
            # A zero here means the company files the tag but folds the real
            # figure into another, so it should not end the search.
            col = np.where(col == 0, np.nan, col)

        out = np.where(np.isnan(out), col, out)

    return out
