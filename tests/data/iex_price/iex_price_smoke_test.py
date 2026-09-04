"""
Verify that the IEX TOPS collector is responsive and returns the expected shape.

Hits the live IEX archive at iextrading.com - no API key needed, but these are
network tests. `test_get_df` downloads a real capture and so is the slow one:
~153 MB, roughly half a minute. It uses the lightest true trading session in the
archive, which keeps the download off the multi-GB scale a normal session
reaches while still checking bars against a full day's symbol breadth.
"""

import pytest
import forecastos as fos

CATALOG_COLS = ["date", "feed", "version", "protocol", "size_bytes", "link"]
BAR_COLS = ["date", "symbol", "open", "high", "low", "close", "volume"]

# The smallest real trading session in the archive (~153 MB): a Christmas Eve
# half day. Small enough to download in a test, but a genuine session with ~5000
# symbols, so the bar assertions below are exercised against real breadth.
SESSION = "2019-12-24"

# Liquid names we expect to exist in a real session.
TICKERS = ["AAPL", "NVDA", "GOOG", "MSFT", "AMZN", "AVGO",
           "TSLA", "LLY", "XOM", "JPM", "WMT", "V"]


def test_fetch_tops_catalog():
    df = fos.data.IEXPrice.fetch_tops_catalog("2024-01-02", "2024-01-05")

    assert list(df.columns) == CATALOG_COLS
    # Four trading sessions in that range, one capture each after dedup.
    assert df["date"].tolist() == [
        "2024-01-05", "2024-01-04", "2024-01-03", "2024-01-02"
    ]
    assert (df["feed"] == "TOPS").all()
    assert (df["size_bytes"] > 0).all()


def test_get_df(tmp_path):
    df = fos.data.IEXPrice.get_df(
        start=SESSION,
        end=SESSION,
        data_dir=str(tmp_path),
    )

    assert not df.empty
    assert list(df.columns) == BAR_COLS
    assert df["date"].tolist() == [SESSION] * len(df)
    assert df["symbol"].is_unique

    missing = sorted(set(TICKERS) - set(df["symbol"]))
    assert not missing, f"no bar extracted for {missing}"

    # Prices come from trades, so a bar's extremes must bracket its ends.
    assert (df["low"] <= df[["open", "close"]].min(axis=1)).all()
    assert (df["high"] >= df[["open", "close"]].max(axis=1)).all()
    assert (df["volume"] > 0).all()

    # cleanup defaults to True, so nothing is left behind.
    assert list(tmp_path.iterdir()) == []


def test_get_df_raises_when_no_sessions():
    # The archive starts in Dec 2016, so this range holds no capture at all.
    with pytest.raises(ValueError):
        fos.data.IEXPrice.get_df(start="2015-01-01", end="2015-01-02")
