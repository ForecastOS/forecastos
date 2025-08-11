import os

api_key = os.environ.get("FORECASTOS_API_KEY", "")
api_key_team = os.environ.get("FORECASTOS_API_KEY_TEAM", "")
api_endpoint = "https://app.forecastos.com/api/v1"

from forecastos.exposure import *
from forecastos.feature import *
from forecastos.forecast import *
from forecastos.provider import *
from forecastos.global_utils import *
