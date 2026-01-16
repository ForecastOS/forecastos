from forecastos.utils.readable import Readable
from forecastos.utils.feature_engineering_mixin import FeatureEngineeringMixin
import time
import pandas as pd


class PersistentTrend(Readable, FeatureEngineeringMixin):
    def __init__(self, *args, **kwargs):
        pass

    @classmethod
    def get_df(cls, min_days_market_relevant=None, filter_start_date=None, filter_end_date=None):
        max_iterations = 1000
        data = []
        current_page = 1

        # Build params, throw away any keys = None
        params = {k: v for k, v in {
            "min_days_market_relevant": min_days_market_relevant,
            "filter_start_date": filter_start_date,
            "filter_end_date": filter_end_date
        }.items() if v is not None}

        for _ in range(max_iterations):
            res = cls.get_request(
                path="/persistent_trends",
                params={**params, "page": current_page},
                use_team_key=True
            )
            if not res.ok:
                print(res.text)
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
            time.sleep(0.1)  # dont overload our apis!

        return pd.DataFrame.from_dict(data)
