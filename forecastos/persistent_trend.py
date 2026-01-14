from forecastos.utils.readable import Readable
from forecastos.utils.feature_engineering_mixin import FeatureEngineeringMixin
import pandas as pd
import io
import time


class PersistentTrend(Readable, FeatureEngineeringMixin):
    def __init__(self, *args, **kwargs):
        pass

    @classmethod
    def get_df(cls, params={}):
        data = []
        current_page = params.get('page', 1)
        max_iterations = 1000

        while True:
            res = cls.get_request(
                path=f"/persistent_trends",
                params={**params, "page": current_page},
                use_team_key=True
            )
            if not res.ok:
                print(res)
                return False
            res_body = res.json()

            page_data = res_body.get('data')
            if page_data is None or len(page_data) == 0:
                # No data left
                break

            data.extend(page_data)

            total_pages = res_body.get('meta', {}).get('total_pages')
            if total_pages is None or current_page >= total_pages:
                # Current page is last page
                break

            current_page += 1
            if current_page >= max_iterations:
                # Failsafe against infinite loop
                break

            # dont overload our apis!
            time.sleep(0.1)

        df = pd.DataFrame.from_dict(data)
        return df
