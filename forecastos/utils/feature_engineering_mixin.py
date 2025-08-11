# feature_methods.py
import numpy as np
import pandas as pd
import forecastos as fos

class FeatureEngineeringMixin:
    @classmethod
    def apply_feature_engineering_logic(cls, df, config, features_key, logic_dict_key='formula', calculate_with=None, global_logic_dict_key=None):
        for ft_name, ft in ((k, v) for k, v in config.get(features_key, {}).items() if not calculate_with or v.get("calculate_with") == calculate_with):
            for formula_name, arg_li in ft.get(logic_dict_key, config.get(global_logic_dict_key, {})).items(): 
                df = cls.apply_formula(df, ft_name, formula_name, arg_li)

        return df
    
    @classmethod
    def apply_formula(cls, df, ft_name, formula_name, arg_li):
        method_name = f"apply_{formula_name}"
        formula_method = getattr(cls, method_name, None)

        if formula_method is None:
            raise ValueError(f"Formula method `{method_name}` not found on `{cls.__name__}`")

        log_str = f"Applying {formula_name} for {ft_name}"
        if arg_li:
            log_str += f" using {arg_li}"

        print(log_str)

        return formula_method(df, ft_name, arg_li)

    @classmethod
    def apply_mean(cls, df: pd.DataFrame, ft_name: str, arg_li: list):
        df[ft_name] = df[arg_li].mean(axis=1)
        return df

    @classmethod
    def apply_subtract(cls, df: pd.DataFrame, ft_name: str, arg_li: list):
        df[ft_name] = df[arg_li[0]] - df[arg_li[1]]
        return df

    @classmethod
    def apply_neg_to_max(cls, df: pd.DataFrame, ft_name: str, arg_li: list):
        group_max = df.groupby(arg_li)[ft_name].transform('max')
        df[ft_name] = np.where(df[ft_name] < 0, group_max, df[ft_name])
        return df

    @classmethod
    def apply_sign_flip(cls, df: pd.DataFrame, ft_name: str, arg_li: list):
        df[ft_name] = df[ft_name] * -1
        return df

    @classmethod
    def apply_winsorize(cls, df: pd.DataFrame, ft_name: str, arg_li: list):
        lower_q, upper_q, group_by = arg_li
        df[ft_name] = (
            df.groupby(group_by)[ft_name]
            .transform(lambda x: x.clip(lower=x.quantile(lower_q), upper=x.quantile(upper_q)))
        )
        return df

    @classmethod
    def apply_standardize(cls, df: pd.DataFrame, ft_name: str, arg_li: list):
        df[ft_name] = df.groupby(arg_li)[ft_name].transform(
            lambda x: (x - x.mean()) / x.std(ddof=0)
        )
        return df

    @classmethod
    def apply_zero_fill(cls, df: pd.DataFrame, ft_name: str, arg_li: list):
        df[ft_name] = df[ft_name].fillna(0)
        return df

    @classmethod
    def apply_map_ticker_to_fsym(cls, df: pd.DataFrame, ft_name: str, arg_li: list):
        ticker_df = fos.get_feature_df(
            "79f61521-381e-4606-8020-7a9bc3130260"
        ).rename(columns={"value": "ticker"})

        ticker_df["ticker"] = ticker_df["ticker"].str.replace(r"-.*$", "", regex=True)

        return df.merge(ticker_df, on="ticker", how="left").drop(columns="ticker")

    @classmethod
    def apply_multiply_time_window_by_scalar(cls, df: pd.DataFrame, ft_name: str, arg_li: list):
        for scalar, start_str, end_str in arg_li:
            start = pd.to_datetime(start_str)
            end = pd.to_datetime(end_str)
            mask = (df['datetime'] >= start) & (df['datetime'] <= end)
            df.loc[mask, ft_name] = df.loc[mask, ft_name] * scalar

        return df