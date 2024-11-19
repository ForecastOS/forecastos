import forecastos as fos

from scipy.stats.mstats import winsorize
from sklearn.preprocessing import StandardScaler
import pandas as pd
import numpy as np

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

    if add_recommended_delay:
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
