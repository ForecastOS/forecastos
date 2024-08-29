import os

api_key = os.environ.get("FORECASTOS_API_KEY", "")
api_endpoint = "https://app.forecastos.com/api/v1"

from forecastos.feature import *
from forecastos.provider import *
from forecastos.global_utils import *
