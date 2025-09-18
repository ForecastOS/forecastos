from forecastos.utils.readable import Readable
import pandas as pd
import numpy as np
from forecastos.utils.feature_engineering_mixin import FeatureEngineeringMixin


class Feature(Readable, FeatureEngineeringMixin):
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
    def create_feature_df(cls, config={}, base_df=None, merge_asof=True):
        df = base_df.copy()
        print("Sorting base df.")
        df = df.sort_values(["datetime", "id"])

        # Get raw features
        for ft_name, ft in config.get('features', []).items():
            print(f"Getting {ft_name}.")
            tmp_ft_df = cls.get(ft["uuid"]).get_df().rename(columns={"value": ft_name})

            for formula_name, arg_li in ft.get("adjustments_pre_join", config.get("feature_adjustments_pre_join", {})).items(): 
                tmp_ft_df = cls.apply_formula(tmp_ft_df, ft_name, formula_name, arg_li)
        
            print(f"Merging {ft_name}.")
            if merge_asof:
                tmp_ft_df = tmp_ft_df.sort_values(["datetime", "id"])
                df = pd.merge_asof(df, tmp_ft_df, on="datetime", by="id", direction='backward')
            else:
                tmp_ft_df = tmp_ft_df.drop(columns="datetime")
                df = df.merge(tmp_ft_df, on="id", how="left")
        
        # D Calculate raw derived features
        df = cls.apply_feature_engineering_logic(df, config, "features_derived", logic_dict_key='formula', calculate_with="raw")

        # Run adjustments on all (excl. normalized derived features)
        df = cls.apply_feature_engineering_logic(df, config, "features", logic_dict_key='adjustments')
        df = cls.apply_feature_engineering_logic(df, config, "features_derived", logic_dict_key='adjustments', calculate_with="raw")

        # Run normalization on all (excl. normalized derived features)
        df = cls.apply_feature_engineering_logic(df, config, "features", logic_dict_key='normalization', global_logic_dict_key='feature_normalization')
        df = cls.apply_feature_engineering_logic(df, config, "features_derived", logic_dict_key='normalization', calculate_with="raw", global_logic_dict_key='feature_normalization')

        # Run post-norm adjustments on all (excl. normalized derived features)
        df = cls.apply_feature_engineering_logic(df, config, "features", logic_dict_key='adjustments_post_normalization', global_logic_dict_key='feature_adjustments_post_normalization')
        df = cls.apply_feature_engineering_logic(df, config, "features_derived", logic_dict_key='adjustments_post_normalization', calculate_with="raw", global_logic_dict_key='feature_adjustments_post_normalization')

        # D Calculate normalized derived features
        df = cls.apply_feature_engineering_logic(df, config, "features_derived", logic_dict_key='formula', calculate_with="normalized")

        return df
