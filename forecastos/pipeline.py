from forecastos.utils.readable import Readable
from forecastos.utils.feature_engineering_mixin import FeatureEngineeringMixin
import pandas as pd
import io


class Pipeline(Readable, FeatureEngineeringMixin):
    def __init__(self, *args, **kwargs):
        pass

    @classmethod
    def get_df(cls, pipeline_id, run_id):
        res = cls.get_request(
            path=f"/pipelines/{pipeline_id}/runs/{run_id}", use_team_key=True)
        if not res.ok:
            print(res)
            return False

        return pd.read_csv(io.StringIO(res.text))

    @classmethod
    def run_pipeline(cls, pipeline_id, json={}):
        res = cls.post_request(
            path=f"/pipelines/{pipeline_id}/runs",
            json=json,
            use_team_key=True
        )
        if not res.ok:
            print(res)
            return False

        return res.json()
