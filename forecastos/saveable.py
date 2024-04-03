import forecastos
import requests


class Saveable:
    def __init__(self):
        pass

    def save_record(self, path="/", body={}, fh=False):
        if fh:
            request_headers = {
                "Authorization": f"Bearer {forecastos.fh_api_key}",
                "Content-Type": "application/json",
            }
        else:
            request_headers = {
                "Authorization": f"Bearer {forecastos.api_key}",
                "Content-Type": "application/json",
            }

        response = requests.post(
            f"{forecastos.api_endpoint}{path}",
            headers=request_headers,
            json=body,
        )

        if (
            response.status_code // 100 == 2
        ):  # Check if the status code is in the 200 range
            self.id = response.json().get("id")
            print(f"{self.__class__.__name__} {self.id} saved")
        else:
            print(
                f"{self.__class__.__name__} save failed with status code: {response.status_code}"
            )

        return response.json()

    @classmethod
    def get(self, path="/", params={}, fh=False):
        if fh:
            request_headers = {
                "Authorization": f"Bearer {forecastos.fh_api_key}",
            }
        else:
            request_headers = {
                "Authorization": f"Bearer {forecastos.api_key}",
            }

        response = requests.get(
            f"{forecastos.api_endpoint}{path}",
            headers=request_headers,
            params=params,
        )

        if (
            response.status_code // 100 != 2
        ):  # Check if the status code is in the 200 range
            print(
                f"{self.__class__.__name__} save failed with status code: {response.status_code}"
            )

        return response.json()
