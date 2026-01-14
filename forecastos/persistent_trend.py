from forecastos.utils.readable import Readable
from forecastos.utils.feature_engineering_mixin import FeatureEngineeringMixin


class PersistentTrend(Readable, FeatureEngineeringMixin):
    def __init__(self, *args, **kwargs):
        pass

    @classmethod
    def get_df(cls, params={}):
        return cls.get_request_data_df_paginated(
            path=f"/persistent_trends",
            params=params,
            use_team_key=True
        )
