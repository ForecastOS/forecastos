from forecastos.utils.readable import Readable
import pandas as pd
import numpy as np
import os


class Feature(Readable):
    def __init__(self, name="", description="", *args, **kwargs):
        self.name = name
        self.description = description
        self.uuid = None

        self.calc_methodology = kwargs.get("calc_methodology")
        self.category = kwargs.get("category")
        self.subcategory = kwargs.get("subcategory")

        self.suggested_delay_s = kwargs.get("suggested_delay_s", 0)
        self.suggested_delay_description = kwargs.get("suggested_delay_description")

        self.universe = kwargs.get("universe")

        self.time_delta = kwargs.get("time_delta")

        self.file_location = kwargs.get("file_location")
        self.schema = kwargs.get("schema")
        self.datetime_column = kwargs.get("datetime_column")
        self.value_type = kwargs.get("value_type")
        self.timeseries = kwargs.get("timeseries")

        self.memory_usage = kwargs.get("memory_usage")

        self.fill_method = kwargs.get("fill_method", [])
        self.id_columns = kwargs.get("id_columns", [])
        self.supplementary_columns = kwargs.get("supplementary_columns", [])
        self.provider_ids = kwargs.get("provider_ids", [])

    @classmethod
    def get(cls, uuid):
        res = cls.get_request(path=f"/fh_features/{uuid}")

        if res.ok:
            return cls.sync_read(res.json())
        else:
            print(res)
            return False

    def get_df(self):
        res = self.__class__.get_request(
            path=f"/fh_features/{self.uuid}/url",
        )

        if res.ok:
            return pd.read_parquet(res.json()["url"])
        else:
            print(res)
            return False

    @classmethod
    def list(cls, params={}):
        res = cls.get_request(
            path=f"/fh_features",
            params=params,
        )

        if res.ok:
            return [cls.sync_read(obj) for obj in res.json()]
        else:
            print(res)
            return False

    @classmethod
    def find(cls, query=""):
        return cls.list(params={"q": query})

    def info(self):
        return self.__dict__

    def __str__(self):
        return f"Feature_{self.uuid}_{self.name}"
    
    @classmethod
    def create_feature_df(cls, config={}, base_df=None):
        df = base_df.copy()
        print("Sorting base df.")
        df = df.sort_values(["datetime", "id"])

        # Get raw features
        for ft_name, ft in config.get('features', []).items():
            print(f"Getting {ft_name}.")
            tmp_ft_df = cls.get(ft["uuid"]).get_df().rename(columns={"value": ft_name})
            
            print(f"Merging {ft_name}.")
            tmp_ft_df = tmp_ft_df.sort_values(["datetime", "id"])
            df = pd.merge_asof(df, tmp_ft_df, on="datetime", by="id", direction='backward')
        
        # D Calculate raw derived features
        df = cls.apply_feature_engineering_logic(df, config, "features_derived", logic_dict_key='formula', calculate_with="raw")

        # Run adjustments on all (excl. normalized derived features)
        df = cls.apply_feature_engineering_logic(df, config, "features", logic_dict_key='adjustments')
        df = cls.apply_feature_engineering_logic(df, config, "features_derived", logic_dict_key='adjustments', calculate_with="raw")

        # Run normalization on all (excl. normalized derived features)
        df = cls.apply_feature_engineering_logic(df, config, "features", logic_dict_key='normalization', global_logic_dict_key='feature_normalization')
        df = cls.apply_feature_engineering_logic(df, config, "features_derived", logic_dict_key='normalization', calculate_with="raw", global_logic_dict_key='feature_normalization')

        # Run post-norm adjustments on all (excl. normalized derived features)
        df = cls.apply_feature_engineering_logic(df, config, "features", logic_dict_key='adjustments_post_normalization')
        df = cls.apply_feature_engineering_logic(df, config, "features_derived", logic_dict_key='adjustments_post_normalization', calculate_with="raw")

        # D Calculate normalized derived features
        df = cls.apply_feature_engineering_logic(df, config, "features_derived", logic_dict_key='formula', calculate_with="normalized")

        return df
    
    @classmethod
    def apply_feature_engineering_logic(cls, df, config, features_key, logic_dict_key='formula', calculate_with=None, global_logic_dict_key=None):
        for ft_name, ft in ((k, v) for k, v in config.get(features_key, {}).items() if not calculate_with or v.get("calculate_with") == calculate_with):
            for formula_name, arg_li in ft.get(logic_dict_key, config.get(global_logic_dict_key, {})).items(): 
                df = cls.apply_formula(df, ft_name, formula_name, arg_li)

        return df
    
    @classmethod
    def apply_formula(cls, df, ft_name, formula_name, arg_li):
        def apply_mean(df, ft_name, arg_li):
            print(f"Applying mean for {ft_name} feature using {arg_li}.")
            df[ft_name] = df[arg_li].mean(axis=1)

            return df
        
        def apply_subtract(df, ft_name, arg_li):
            print(f"Applying subtract for {ft_name} feature using {arg_li}.")
            df[ft_name] = df[arg_li[0]] - df[arg_li[1]]
            
            return df
        
        def apply_neg_to_max(df, ft_name, arg_li):
            print(f"Applying neg_to_max for {ft_name} feature using {arg_li}.")
            group_max = df.groupby(arg_li)[ft_name].transform('max')
            df[ft_name] = np.where(df[ft_name] < 0, group_max, df[ft_name])
        
            return df

        def apply_sign_flip(df, ft_name, arg_li):
            print(f"Applying sign_flip for {ft_name} feature.")
            df[ft_name] = df[ft_name] * -1
        
            return df
        
        def apply_winsorize(df, ft_name, arg_li):
            lower_q = arg_li[0]
            upper_q = arg_li[1]
            group_by = arg_li[2]
            print(f"Applying winsorize for {ft_name} feature using {lower_q} and {upper_q}, grouped by {group_by}.")

            df[ft_name] = (
                df.groupby(group_by)[ft_name]
                .transform(lambda x: x.clip(lower=x.quantile(lower_q), upper=x.quantile(upper_q)))
            )

            return df
        
        def apply_standardize(df, ft_name, arg_li):
            print(f"Applying standardize for {ft_name} feature using {arg_li}.")
            df[ft_name] = df.groupby(arg_li)[ft_name].transform(
                lambda x: (x - x.mean()) / x.std(ddof=0)
            )

            return df
        
        def apply_zero_fill(df, ft_name, arg_li):
            print(f"Applying zero_fill for {ft_name} feature.")
            df[ft_name] = df[ft_name].fillna(0)

            return df


        match formula_name:
            case "mean":
                return apply_mean(df, ft_name, arg_li)
            case "subtract":
                return apply_subtract(df, ft_name, arg_li)
            case "neg_to_max":
                return apply_neg_to_max(df, ft_name, arg_li)
            case "sign_flip": 
                return apply_sign_flip(df, ft_name, arg_li)
            case "winsorize":
                return apply_winsorize(df, ft_name, arg_li)
            case "standardize":
                return apply_standardize(df, ft_name, arg_li)
            case "zero_fill":
                return apply_zero_fill(df, ft_name, arg_li)

