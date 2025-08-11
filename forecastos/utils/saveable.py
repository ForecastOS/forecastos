import forecastos
import requests


class Saveable:
    def __init__(self):
        pass

    @classmethod
    def post_request(self, path="/", body={}, use_team_key=True):
        if use_team_key:
            api_key = forecastos.api_key_team            
        else:
            api_key = forecastos.api_key

        request_headers = {
            "Authorization": f"Bearer {api_key}",
        }

        response = requests.post(
            f"{forecastos.api_endpoint}{path}",
            headers=request_headers,
            json=body,
        )

        if not response.ok:  # Check if the status code is in the 200 range
            print(
                f"{self.__class__.__name__} save failed with status code: {response.status_code}"
            )

        return response
    
    def _save_chart(self, json_body):
        response = requests.post(
            f"{forecastos.api_endpoint}/charts/create_or_update",
            headers={
                "Authorization": f"Bearer {forecastos.api_key}",
            },
            json=json_body,
        )

        if (
            response.status_code // 100 == 2
        ):  # Check if the status code is in the 200 range
            chart_id = response.json().get("id")
            print(f"Chart {chart_id} saved.")
        else:
            print(f"Chart creation failed with status code: {response.status_code}")
