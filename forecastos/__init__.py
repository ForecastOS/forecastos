import os

api_key = os.environ.get("FORECASTOS_API_KEY", "")
api_endpoint = "https://app.forecastos.com/api/v1"

from forecastos.dataset import *
