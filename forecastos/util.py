import forecastos as fos

from scipy.stats.mstats import winsorize
from sklearn.preprocessing import StandardScaler
import pandas as pd
import numpy as np

import copy
from functools import wraps

import cvxpy as cvx


np.seterr(invalid="ignore")


def normalize(df, *args, **kwargs):
    winsorize_df = kwargs.get("winsorize", True)
    winsorize_limits = kwargs.get("winsorize_limits", (0.025, 0.025))
    standardize_df = kwargs.get("standardize", True)
    exclude_cols = kwargs.get("exclude_cols", [])
    reset_idx = kwargs.get("reset_idx", False)

    df = df.copy()

    cols_to_norm = df.columns.difference([*exclude_cols])

    if winsorize_df:
        for col in cols_to_norm:
            df.loc[:, col] = winsorize(
                df[col], limits=winsorize_limits, nan_policy="omit"
            )

    if standardize_df:
        scaler = StandardScaler()
        df.loc[:, cols_to_norm] = scaler.fit_transform(df[cols_to_norm])

    if reset_idx:
        df = df.reset_index()

    return df


def normalize_group(df, *args, **kwargs):
    groupby = kwargs.get("groupby", [])
    drop_idx_cols = kwargs.get("drop_idx_cols", ["level_1", "index"])
    reset_idx = kwargs.pop("reset_idx", True)

    df = df.groupby(groupby).apply(normalize, *args, **kwargs)

    if reset_idx:
        df = df.reset_index()
        df = df.drop(columns=[col for col in drop_idx_cols if col in df.columns])

    return df


def transform_into_quantiles(df):
    quantiles = [0.2, 0.4, 0.6, 0.8, 1.0]
    categorized_df = pd.DataFrame(index=df.index, columns=df.columns)

    for date in df.index:
        quantile_values = df.loc[date].quantile(quantiles)
        categorized_df.loc[date] = df.loc[date].apply(
            lambda x: np.argmax(x <= quantile_values.values) * 0.2
        )

    return (categorized_df - 0.4) * 2.5  # -1 to 1


def get_feature_df(uuid, *args, **kwargs):
    invert_col = kwargs.get("invert_col", False)
    log10_col = kwargs.get("log10_col", False)
    universe_ids = kwargs.get("universe_ids", False)
    sort_values = kwargs.get("sort_values", False)
    add_recommended_delay = kwargs.get("add_recommended_delay", False)
    datetime_start = kwargs.get("datetime_start", False)
    datetime_end = kwargs.get("datetime_end", False)
    merge_asof = kwargs.get("merge_asof", False)
    normalize_group = kwargs.get("normalize_group", False)
    normalize = kwargs.get("normalize", False)
    pivot = kwargs.get("pivot", False)
    convert_to_quantiles = kwargs.get("convert_to_quantiles", False)
    sort_cols = kwargs.get("sort_cols", False)
    remove_inf_cols = kwargs.get("remove_inf_cols", [])
    cast_to_float64_cols = kwargs.get("cast_to_float64_cols", [])
    fillna = kwargs.get("fillna", False)
    fillna_value = kwargs.get("fillna_value", 0)
    rename_columns = kwargs.get("rename_columns", False)
    add_delay_td = kwargs.get("add_delay_td", False)

    ft_obj = fos.Feature.get(uuid)
    df = ft_obj.get_df()

    if rename_columns:
        df = df.rename(columns=rename_columns)

    if universe_ids:
        df = df[df.id.isin(universe_ids)]

    if remove_inf_cols:
        for col in remove_inf_cols:
            df[col] = df[col].replace([np.inf, -np.inf], np.nan)

    if cast_to_float64_cols:
        for col in cast_to_float64_cols:
            df[col] = df[col].astype("float64")

    if sort_values:
        df = df.sort_values(sort_values)

    if add_delay_td:
        df.datetime = df.datetime + add_delay_td
    elif add_recommended_delay:
        df.datetime = df.datetime + pd.Timedelta(seconds=ft_obj.suggested_delay_s)

    if datetime_start:
        df = df[df.datetime >= datetime_start]

    if datetime_end:
        df = df[df.datetime <= datetime_end]

    if invert_col:
        df[invert_col] = 1 / df[invert_col]
        df[invert_col] = df[invert_col].replace([np.inf, -np.inf], np.nan)

    if log10_col:
        df[log10_col] = np.log10(df[log10_col])

    if merge_asof:
        df = pd.merge_asof(
            merge_asof["left"],
            df.sort_values(merge_asof["sort_values"]),
            tolerance=merge_asof["tolerance"],
            by=merge_asof["by"],
            on=merge_asof["on"],
            direction=merge_asof["direction"],
        )

    if normalize_group:
        df = fos.normalize_group(df, **normalize_group)
    elif normalize:
        df = fos.normalize(df, **normalize)

    if pivot:
        df = df.pivot(**pivot)

    if pivot and convert_to_quantiles:
        df = transform_into_quantiles(df)

    if sort_cols:
        df = df.sort_index(axis=1)

    if fillna:
        df = df.infer_objects(copy=False).fillna(fillna_value)

    return df


def deep_dict_merge(default_d, update_d):
    "Deep copies update_d onto default_d recursively"

    default_d = copy.deepcopy(default_d)
    update_d = copy.deepcopy(update_d)

    def deep_dict_merge_inner(default_d, update_d):
        for k in update_d.keys():
            if (
                k in default_d
                and isinstance(default_d[k], dict)
                and isinstance(update_d[k], dict)
            ):
                deep_dict_merge_inner(default_d[k], update_d[k])
            else:
                default_d[k] = update_d[k]

    deep_dict_merge_inner(default_d, update_d)
    return default_d  # With update_d values copied onto it


def get_value_at_t(source, current_time, prediction_time=None, use_lookback=False):
    """
    Obtain the value(s) of a source object at a given time.

    Parameters
    ----------
    source : callable, pd.Series, pd.DataFrame, or other object
        - If callable, returns source(current_time, prediction_time).
        - If a pandas object, returns the value at the index matching
          current_time (or (current_time, prediction_time) for MultiIndex).
        - If no matching index is found, returns the object itself unless
          use_lookback=True, in which case it returns the most recent prior index.

    current_time : np.Timestamp
        Time at which the value is desired.

    prediction_time : np.Timestamp or None
        Optional forecast time. If None, defaults to current_time.

    use_lookback : bool
        If True, and no exact index match exists, return the value at the
        closest index strictly before current_time.

    Returns
    -------
    The retrieved value or the original source object.
    """
    if prediction_time is None:
        prediction_time = current_time

    # Case 1: Callable source
    if callable(source):
        return source(current_time, prediction_time)

    # Case 2: Pandas Series/DataFrame
    if isinstance(source, (pd.Series, pd.DataFrame)):
        try:
            if isinstance(source.index, pd.MultiIndex):
                return source.loc[(current_time, prediction_time)]
            else:
                return source.loc[current_time]
        except KeyError:
            if not use_lookback:
                return source

            # Lookback mode: find the closest earlier timestamp
            time_index = source.index.get_level_values(0)
            earlier_times = time_index[time_index < current_time]

            if not earlier_times.empty:
                closest_time = earlier_times.max()
                return source.loc[closest_time]
            else:
                return source

    # Case 3: Fallback
    return source


def clip_for_dates(func):
    """
    Decorator that restricts the returned pandas object to the date range
    defined by the instance's `start_date` and `end_date`.
    """

    @wraps(func)
    def wrapper(self, *args, **kwargs):
        pd_obj = func(self, *args, **kwargs)
        return pd_obj[
            (pd_obj.index >= self.start_date) & (pd_obj.index <= self.end_date)
        ]

    return wrapper


def remove_excluded_columns_pd(arg, exclude_assets=None, include_assets=None):
    """Filter a DataFrame or Series by keeping `include_assets` if provided, otherwise dropping `exclude_assets`."""
    if include_assets:
        if isinstance(arg, pd.DataFrame):
            return arg[[col for col in include_assets if col in arg.columns]]
        elif isinstance(arg, pd.Series):
            return arg[[col for col in include_assets if col in arg]]
        else:
            return arg
    else:
        if isinstance(arg, pd.DataFrame):
            return arg.drop(columns=exclude_assets, errors="ignore")
        elif isinstance(arg, pd.Series):
            return arg.drop(exclude_assets, errors="ignore")
        else:
            return arg


def remove_excluded_columns_np(
    np_arr, holdings_cols, exclude_assets=None, include_assets=None
):
    """Filter a NumPy array by including or excluding columns based on asset names."""
    if include_assets:
        idx_incl_assets = holdings_cols.get_indexer(include_assets)
        # Filter out -1 values (i.e. assets with no match)
        idx_incl_assets = idx_incl_assets[idx_incl_assets != -1]
        # Create a boolean array of False values
        mask = np.zeros(np_arr.shape, dtype=bool)
        # Set the values at the indices to exclude to False
        mask[idx_incl_assets] = True
        return np_arr[mask]
    elif exclude_assets:
        idx_excl_assets = holdings_cols.get_indexer(exclude_assets)
        # Filter out -1 values (i.e. assets with no match)
        idx_excl_assets = idx_excl_assets[idx_excl_assets != -1]
        # Create a boolean array of True values
        mask = np.ones(np_arr.shape, dtype=bool)
        # Set the values at the indices to exclude to False
        mask[idx_excl_assets] = False
        return np_arr[mask]
    else:
        return np_arr


def get_max_key_lt_or_eq_value(dictionary, value):
    """
    Returns the maximum key in the dictionary that is less than or equal to the given value.
    If no such key exists, returns None.

    Useful for looking up values by datetime.
    """
    # Filter keys that are less than or equal to the value
    valid_keys = [k for k in dictionary.keys() if k <= value]

    # Return the max of the valid keys if the list is not empty
    if valid_keys:
        return max(valid_keys)
    else:
        return None


def _solve_and_extract_trade_weights(
    prob, weights_trades, t, solver, solver_opts, holdings
):
    try:
        prob.solve(solver=solver, **solver_opts)
        return (
            t,
            weights_trades.value,
        )  # Return the value of weights_trades after solving
    except (cvx.SolverError, cvx.DCPError, TypeError):
        return t, pd.Series(index=holdings.index, data=0.0).values  # Zero trade

