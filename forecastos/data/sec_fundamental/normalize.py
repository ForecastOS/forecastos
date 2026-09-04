"""Putting extracted statements onto a comparable timeline, and merging them.

Filings do not report comparable periods. A 10-K income statement covers the
full year, so Q4 only exists as the year minus the three quarters already
filed. Cash flow statements are often cumulative from the start of the fiscal
year, so Q3 as filed is really nine months. Balance sheets are instants, so a
period's opening position is the previous filing's close.

All three repairs need the same lookup: for a row, the same company's filing
from N months earlier. `adjacent` does it as one merge per offset, replacing a
per-row scan that made the pipeline quadratic in row count.
"""

import numpy as np
import pandas as pd

# How far a filing may sit from where the offset puts it and still count as a
# match. Fiscal calendars drift and filing dates move around holidays, so an
# exact date would match almost nothing.
ADJACENCY_TOLERANCE = pd.Timedelta(days=30)

# Quarterly or annual if within this many months of 3 or 12. Reported periods
# are rarely exactly that long.
PERIOD_TOLERANCE = 1.0

# What makes a reported figure distinct. Income and cash flow describe the same
# period, so they join on all of them.
PERIOD_KEYS = ['cik', 'fy', 'fp', 'form',
               'accn', 'start', 'end', 'period', 'filed']

# The balance sheet is an instant, so it joins on the period's close only.
PIT_MERGE_KEYS = ['cik', 'fy', 'form', 'accn', 'end', 'filed']


def normalize(wide: pd.DataFrame, statement) -> pd.DataFrame:
    """Reduce an extracted statement to keys and datapoints, then repair periods."""
    keep = statement.key_columns + ['frame'] + statement.datapoint_names
    wide = wide[[c for c in keep if c in wide.columns]].copy()

    if wide.empty:
        return wide

    for step in _steps(statement):
        wide = step(wide, statement)

    return wide


def _steps(statement) -> list:
    """The repairs this statement needs, in the order they have to happen.

    Cash flow stubs cumulative periods before implying Q4: that arithmetic
    subtracts three quarters, which have to be quarters first.
    """
    if statement.is_pit:
        return [_imply_starting_values]
    if statement.name == 'cashflow_statement':
        return [_add_period, _imply_quarterly,
                _imply_q4, _keep_quarterly_and_annual]
    return [_add_period, _keep_quarterly_and_annual, _imply_q4]


# === Finding the filing N months back === #


def adjacent(df: pd.DataFrame, months: int, value_cols: list) -> pd.DataFrame:
    """For each row, the same company's filing about `months` earlier.

    Args:
        df: rows to look back from. Needs cik, end, filed.
        months: how far back to look.
        value_cols: columns to carry over from the matched row.

    Returns:
        A frame on `df`'s index holding the matched row's end and `value_cols`,
        all null where nothing matched.
    """
    position = _match_positions(df, months)
    return (df[['end'] + value_cols]
            .iloc[np.maximum(position, 0)]
            .set_axis(df.index)
            .where(pd.Series(position >= 0, index=df.index), axis=0))


def _match_positions(df: pd.DataFrame, months: int) -> np.ndarray:
    """Row offset of each row's counterpart `months` back, or -1 if there is none.

    Both dates have to line up. The period end alone is ambiguous: a quarter
    appears in its own filing and again as a comparative in later ones, and
    only the filing date tells those apart.

    Neither date is unique alone, so candidates come from bucketing period ends
    into tolerance-wide bins and joining a row against the three bins its
    target could land in - a handful of comparisons per row within one company.
    """
    n = len(df)
    end, filed = df['end'], df['filed']

    usable = (end.notna() & filed.notna()).to_numpy()
    out = np.full(n, -1, dtype='int64')
    if not usable.any():
        return out

    keys = {'_row': np.flatnonzero(usable), 'cik': df['cik'].to_numpy()[usable]}
    left = pd.DataFrame({
        **keys,
        'target_end': (end - pd.DateOffset(months=months)).to_numpy()[usable],
        'target_filed': (filed - pd.DateOffset(months=months)).to_numpy()[usable],
    })
    right = pd.DataFrame({
        **keys,
        'match_end': end.to_numpy()[usable],
        'match_filed': filed.to_numpy()[usable],
    }).rename(columns={'_row': '_pos'})

    width = ADJACENCY_TOLERANCE.value
    right['_bin'] = right['match_end'].astype('int64') // width
    target_bin = left['target_end'].astype('int64') // width

    # A target near a bin edge lands in the neighbouring bin, so all three have
    # to be probed to cover the window.
    candidates = pd.concat(
        [left.assign(_bin=target_bin + offset).merge(
            right, on=['cik', '_bin'], how='inner')
         for offset in (-1, 0, 1)],
        ignore_index=True,
    )

    within = (
        (candidates['match_end'] - candidates['target_end']).abs()
        .lt(ADJACENCY_TOLERANCE)
        & (candidates['match_filed'] - candidates['target_filed']).abs()
        .lt(ADJACENCY_TOLERANCE)
    )
    # Two filings where the prior quarter should be means we cannot say which
    # it is, and a wrong pick would silently corrupt the subtraction.
    candidates = candidates[within].drop_duplicates('_row', keep=False)

    out[candidates['_row'].to_numpy()] = candidates['_pos'].to_numpy()
    return out


# === Period repairs === #


def _add_period(df: pd.DataFrame, _statement) -> pd.DataFrame:
    """Length of each row's period, in months."""
    df['period'] = _months_between(df['start'], df['end'])
    return df


def _keep_quarterly_and_annual(df: pd.DataFrame, _statement) -> pd.DataFrame:
    """Drop periods that are neither a quarter nor a year.

    Filings carry other spans - six month stubs, transition periods,
    life-to-date totals - that line up with nothing else.
    """
    period = df['period']
    return df[(period - 3.0).abs().lt(PERIOD_TOLERANCE)
              | (period - 12.0).abs().lt(PERIOD_TOLERANCE)]


def _imply_quarterly(df: pd.DataFrame, statement) -> pd.DataFrame:
    """Turn cumulative year-to-date figures into the quarter alone.

    Q2 and Q3 cash flow usually runs from the start of the fiscal year, so the
    quarter is the filing minus the one before it.
    """
    names = statement.datapoint_names
    prior = adjacent(df, 3, names)

    cumulative = (
        df['fp'].ne('FY')
        & df['fp'].ne('Q1')
        & (df['period'] - 3.0).abs().gt(PERIOD_TOLERANCE)
        & prior['end'].notna()
    )

    df.loc[cumulative, names] = (
        df.loc[cumulative, names] - prior.loc[cumulative, names])
    df.loc[cumulative, 'start'] = (
        prior.loc[cumulative, 'end'] + pd.Timedelta(days=1))
    df.loc[cumulative, 'period'] = _months_between(
        df.loc[cumulative, 'start'], df.loc[cumulative, 'end'])

    # Some companies report the stubbed figure themselves, so our stub can
    # reproduce a row that is already there.
    return df.drop_duplicates(subset=PERIOD_KEYS, keep='first')


def _imply_q4(df: pd.DataFrame, statement) -> pd.DataFrame:
    """Add a fourth quarter, which no filing reports on its own.

    Q4 is the 10-K's full year less the three quarters already filed - only
    where all three were found, since a missing one would turn into a
    year-sized quarter.
    """
    names = statement.datapoint_names
    q3, q2, q1 = (adjacent(df, months, names) for months in (3, 6, 9))

    full_year = (
        df['fp'].eq('FY')
        & (df['period'] - 12.0).abs().lt(PERIOD_TOLERANCE)
        & q1['end'].notna() & q2['end'].notna() & q3['end'].notna()
    )
    if not full_year.any():
        return df

    fourth = df.loc[full_year].copy()
    fourth['fp'] = 'Q4'
    fourth['start'] = q3.loc[full_year, 'end'] + pd.Timedelta(days=1)
    fourth['period'] = _months_between(fourth['start'], fourth['end'])
    # SEC's label belongs to the reported period, not to one we derived.
    fourth['frame'] = np.nan
    fourth[names] = df.loc[full_year, names] - (
        q3.loc[full_year, names]
        + q2.loc[full_year, names]
        + q1.loc[full_year, names])

    return pd.concat([df, fourth], ignore_index=True)


def _imply_starting_values(df: pd.DataFrame, statement) -> pd.DataFrame:
    """Rename instant values to the period's close, and imply its open.

    A period opens where the previous filing closed - the prior year for an
    annual row, the prior quarter for a quarterly one.
    """
    names = statement.datapoint_names
    end_cols = [f'end_{name}' for name in names]
    df = df.rename(columns=dict(zip(names, end_cols)))

    annual = adjacent(df, 12, end_cols)[end_cols].to_numpy(dtype='float64')
    quarterly = adjacent(df, 3, end_cols)[end_cols].to_numpy(dtype='float64')
    df[[f'start_{name}' for name in names]] = np.where(
        df['fp'].eq('FY').to_numpy()[:, None], annual, quarterly)

    return df


# === Merging === #


def merge_statements(statements: dict) -> pd.DataFrame:
    """One row per company-period, carrying every statement's datapoints.

    Args:
        statements: normalized frames keyed by statement name.

    Returns:
        The merged frame, or an empty one if there was nothing to join.
    """
    income, cashflow = (statements['income_statement'],
                        statements['cashflow_statement'])
    if income.empty or cashflow.empty:
        return pd.DataFrame()

    merged = income.merge(
        # Both sides carry the same `frame`, so take the income statement's.
        cashflow.drop(columns='frame'),
        on=PERIOD_KEYS,
        how='outer',
    )

    balance = statements['balance_sheet']
    if not balance.empty:
        merged = merged.merge(
            # `fp` already came from the flow statements and is not in the join.
            balance.drop(columns=['fp', 'frame']),
            on=PIT_MERGE_KEYS,
            how='left',
        )

    merged = _clean_fiscal_year(merged)
    merged = _fill_from_earlier_filings(merged)
    return _flag_latest(merged)


def _clean_fiscal_year(df: pd.DataFrame) -> pd.DataFrame:
    """Label each period by the year it covers, not the year it was filed in.

    A period repeated in a later filing carries that filing's fiscal year,
    which would put one period under two labels.
    """
    df['fy'] = df.groupby(
        ['cik', 'fp', 'start', 'end'], dropna=False)['fy'].transform('min')
    return df


def _fill_from_earlier_filings(df: pd.DataFrame) -> pd.DataFrame:
    """Fill gaps in a restatement from the filing that reported the period first.

    A comparative often repeats only part of a period. The rest was not
    withdrawn, it simply was not restated.
    """
    df = df.sort_values('filed')
    group = ['cik', 'fy', 'fp', 'form', 'start', 'end']
    fixed = set(group) | {'accn', 'period', 'filed', 'frame'}
    fill_cols = [c for c in df.columns if c not in fixed]

    df[fill_cols] = df.groupby(group, dropna=False)[fill_cols].ffill()
    return df


def _flag_latest(df: pd.DataFrame) -> pd.DataFrame:
    """Mark the most recently filed version of each period.

    Which version is correct depends on when you are asking, so this labels
    the newest rather than dropping the rest.
    """
    latest = df.groupby(
        ['cik', 'start', 'end', 'period'], dropna=False)['filed'].transform('max')
    df['is_latest'] = df['filed'].eq(latest)
    return df


def _months_between(start: pd.Series, end: pd.Series) -> pd.Series:
    """Length of a period in whole months, null if either end is missing."""
    return ((end.dt.year - start.dt.year) * 12
            + (end.dt.month - start.dt.month)
            + (end.dt.day - start.dt.day) / 30).round(0)
