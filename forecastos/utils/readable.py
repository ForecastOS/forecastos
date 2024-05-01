import forecastos
import requests


class Readable:
    def __init__(self):
        pass

    @classmethod
    def get_request(self, path="/", params={}):
        request_headers = {
            "Authorization": f"Bearer {forecastos.api_key}",
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
    def sync_read(cls, obj):
        instance = cls()
        for key, value in obj.items():
            setattr(instance, key, value)

        return instance
