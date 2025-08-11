from forecastos.utils.readable import Readable
from forecastos.utils.feature_engineering_mixin import FeatureEngineeringMixin
import pandas as pd
import io


class Exposure(Readable, FeatureEngineeringMixin):
    def __init__(self, *args, **kwargs):
        pass

    @classmethod
    def get_df(cls, id):
        res = cls.get_request(path=f"/exposures/company/{id}", use_team_key=True)

        if res.ok:
            df = pd.read_csv(io.StringIO(res.text))
            df[["poll_start_at", "poll_end_at", "filing_date"]] = df[["poll_start_at", "poll_end_at", "filing_date"]].apply(pd.to_datetime).apply(lambda col: col.dt.tz_localize(None))
            return df
        else:
            print(res)
            return False

    @classmethod
    def create_exposure_df(cls, config={}, base_df=None, merge_asof=True):
        df = base_df.copy()
        print("Sorting base df.")
        df = df.sort_values(["datetime", "id"])

        # Get raw features
        for exposure_name, exposure in config.get('exposures', []).items():
            print(f"Getting {exposure_name}.")
            tmp_exposure_df = cls.get_df(exposure["id"]).rename(columns={
                "answer": exposure_name,
                "filing_date": "datetime",
            })[["ticker", "datetime", exposure_name]]

            for formula_name, arg_li in exposure.get("adjustments_pre_join", config.get("exposure_adjustments_pre_join", {})).items(): 
                tmp_exposure_df = cls.apply_formula(tmp_exposure_df, exposure_name, formula_name, arg_li)
        
            print(f"Merging {exposure_name}.")
            if merge_asof:
                tmp_exposure_df = tmp_exposure_df.sort_values(["datetime", "id"])
                df = pd.merge_asof(df, tmp_exposure_df, on="datetime", by="id", direction='backward')
            else:
                tmp_exposure_df = tmp_exposure_df.drop(columns="datetime")
                df = df.merge(tmp_exposure_df, on="id", how="left")
        
        df = df.drop_duplicates()

        # D Calculate raw derived features
        df = cls.apply_feature_engineering_logic(df, config, "exposures_derived", logic_dict_key='formula', calculate_with="raw")

        # Run adjustments on all (excl. normalized derived features)
        df = cls.apply_feature_engineering_logic(df, config, "exposures", logic_dict_key='adjustments')
        df = cls.apply_feature_engineering_logic(df, config, "exposures_derived", logic_dict_key='adjustments', calculate_with="raw")

        # Run normalization on all (excl. normalized derived features)
        df = cls.apply_feature_engineering_logic(df, config, "exposures", logic_dict_key='normalization', global_logic_dict_key='exposure_normalization')
        df = cls.apply_feature_engineering_logic(df, config, "exposures_derived", logic_dict_key='normalization', calculate_with="raw", global_logic_dict_key='exposure_normalization')

        # Run post-norm adjustments on all (excl. normalized derived features)
        df = cls.apply_feature_engineering_logic(df, config, "exposures", logic_dict_key='adjustments_post_normalization')
        df = cls.apply_feature_engineering_logic(df, config, "exposures_derived", logic_dict_key='adjustments_post_normalization', calculate_with="raw")

        # D Calculate normalized derived features
        df = cls.apply_feature_engineering_logic(df, config, "exposures_derived", logic_dict_key='formula', calculate_with="normalized")

        return df