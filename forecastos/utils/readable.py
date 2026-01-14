import forecastos
import requests
import time
import pandas as pd


class Readable:
    def __init__(self):
        pass

    @classmethod
    def get_request(self, path="/", params={}, use_team_key=False):
        if use_team_key:
            api_key = forecastos.api_key_team
        else:
            api_key = forecastos.api_key

        request_headers = {
            "Authorization": f"Bearer {api_key}",
        }

        response = requests.get(
            f"{forecastos.api_endpoint}{path}",
            headers=request_headers,
            params=params,
        )

        if not response.ok:  # Check if the status code is in the 200 range
            print(
                f"{self.__class__.__name__} save failed with status code: {response.status_code}"
            )

        return response

    @classmethod
    def get_request_data_df_paginated(self, path="/", params={}, use_team_key=False, max_iterations=1000):
        data = []
        current_page = params.get('page', 1)

        for _ in range(max_iterations):
            res = self.get_request(
                path=path,
                params={**params, "page": current_page},
                use_team_key=use_team_key
            )
            if not res.ok:
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

    @classmethod
    def sync_read(cls, obj):
        instance = cls()
        for key, value in obj.items():
            setattr(instance, key, value)

        return instance
