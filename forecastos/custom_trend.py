from forecastos.utils.readable import Readable
from forecastos.utils.feature_engineering_mixin import FeatureEngineeringMixin
import pandas as pd


class CustomTrend(Readable, FeatureEngineeringMixin):
    def __init__(self, *args, **kwargs):
        pass

    @classmethod
    def get_df(cls, json={}):
        res = cls.post_request(
            path="/trends/custom",
            json=json,
            use_team_key=True
        )
        if not res.ok:
            print(res.text)
            return False

        res_body = res.json()

        df_columns = ['date', 'popularity_score']
        rolling_90_df = pd.DataFrame(
            list(res_body.get('rolling_90d_popularity', {}).items()),
            columns=df_columns
        )
        rolling_90_df['rolling_type'] = 'rolling_90d'

        rolling_365_df = pd.DataFrame(
            list(res_body.get('rolling_365d_popularity', {}).items()),
            columns=df_columns
        )
        rolling_365_df['rolling_type'] = 'rolling_365d'
        return pd.concat([rolling_90_df, rolling_365_df], ignore_index=True)
