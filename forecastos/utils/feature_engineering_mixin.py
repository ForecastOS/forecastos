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
        qs = (
            df.groupby(group_by, observed=True)[ft_name]
            .quantile([lower_q, upper_q])
            .unstack(level=-1)
            .rename(columns={lower_q: f'__{ft_name}_lo', upper_q: f'__{ft_name}_hi'})
        )
        df = df.join(qs, on=group_by)
        df[ft_name] = df[ft_name].clip(lower=df[f'__{ft_name}_lo'], upper=df[f'__{ft_name}_hi'])
        df.drop(columns=[f'__{ft_name}_lo', f'__{ft_name}_hi'], inplace=True)
        
        return df

    @classmethod
    def apply_standardize(cls, df: pd.DataFrame, ft_name: str, arg_li: list):
        stats = (
            df.groupby(arg_li, observed=True)[ft_name]
            .agg(['mean', 'std'])
            .rename(columns={'mean': f'__{ft_name}_mu', 'std': f'__{ft_name}_sd'})
        )
        df = df.join(stats, on=arg_li)
        sd = df[f'__{ft_name}_sd'].replace(0, np.nan)
        df[ft_name] = (df[ft_name] - df[f'__{ft_name}_mu']) / sd
        df.drop(columns=[f'__{ft_name}_mu', f'__{ft_name}_sd'], inplace=True)
        
        return df

    @classmethod
    def apply_log(cls, df: pd.DataFrame, ft_name: str, arg_li: list):
        min_val = df[ft_name].min()
        shift = 1

        if min_val <= 0:
            # Shift ensures no log(0); only applied if min value <= 0
            df[ft_name] = df[ft_name] + abs(min_val) + shift

        df[ft_name] = np.log10(df[ft_name])

        return df

    @classmethod
    def apply_shift(cls, df: pd.DataFrame, ft_name: str, arg_li: list):
        shift_i = arg_li[0]
        shift_sort_values_li = arg_li[1]
        shift_group_by = arg_li[2]

        df = df.sort_values(shift_sort_values_li)

        df[ft_name] = df.groupby(shift_group_by)[ft_name].shift(shift_i)        

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