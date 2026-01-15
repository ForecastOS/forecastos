"""
Verify that GET endpoints for hivemind api are responsive. Does not test 
endpoints that read or create db records. 

Set FOS_API_KEY and FOS_API_ENDPOINT environment variables to the desired
API key to use and server (local / prod).
"""

import os
from dotenv import load_dotenv
import pytest
import forecastos as fos

load_dotenv()


@pytest.fixture(autouse=True)
def set_fos_api_key_and_endpoint():
    def get_env_var(name):
        env_var = os.environ.get(name)
        if not env_var:
            raise RuntimeError(f"{name} not set")

        return env_var

    api_key = get_env_var("FOS_API_KEY")
    endpoint = get_env_var("FOS_API_ENDPOINT")

    fos.api_key = api_key
    fos.api_key_team = api_key
    fos.api_endpoint = endpoint
    yield


def test_custom_trend_get_df():
    df = fos.CustomTrend.get_df({
        'trend': {
            'text': 'Artificial Intelligence',
            'start_date': '2020-01-01'
        }
    })

    assert df is not False
    assert not df.empty


def test_persistent_trend_get_df():
    df = fos.PersistentTrend.get_df()

    assert df is not False
    assert not df.empty


def test_trend_get_df():
    df = fos.Trend.get_df(params={
        'market_relevant': True,
        'identified_on_start': '2025-11-10',
        'identified_on_end': '2025-11-10'
    })

    assert df is not False
    assert not df.empty
