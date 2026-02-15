import os

__version__ = "0.3.0"

api_key = os.environ.get("FORECASTOS_API_KEY", "")
api_key_team = os.environ.get("FORECASTOS_API_KEY_TEAM", "")
api_endpoint = "https://app.forecastos.com/api/v1"

from forecastos.pipeline import *
from forecastos.custom_trend import *
from forecastos.trend import *
from forecastos.persistent_trend import *
from forecastos.exposure import *
from forecastos.feature import *
from forecastos.forecast import *
from forecastos.provider import *
from forecastos.util import *

import forecastos.portfolio