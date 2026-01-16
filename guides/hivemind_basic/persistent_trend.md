<h1>Hivemind: Persistent Trends</h1>

## What Are Hivemind Persistent Trends?

Hivemind persistent trends, or trends aggregated by similarity across time, are designed to capture narratives that remain relevant over time.

They reduce short-term noise and emphasize trends that exhibit consistency, stability, and persistence across market cycles.

## UI Access

Persistent trends are available in the ForecastOS UI, where users can compare persistent and raw trends, visualize long-run narratives, and evaluate trend durability through time.

![Hivemind Persistent Trends](/screenshot_persistent_trends.png)

## API Access

Hivemind persistent trends are accessible through the ForecastOS API for systematic research and portfolio workflows.

### Example: Fetching Persistent Trends

```bash
curl -X GET "https://api.forecastos.com/api/v1/persistent_trends" \
-H "Authorization: Bearer YOUR_API_TOKEN" \
-H "Content-Type: application/json"
```

**Query Parameters**

| Parameter                  | Type    | Default                         | Required | Description                                                                 |
|----------------------------|---------|---------------------------------|----------|-----------------------------------------------------------------------------|
| page                       | integer | 1                               | No       | Page number for paginated results.                                          |
| min\_days\_market\_relevant | integer | 1                               | No       | Minimum number of days a trend must be flagged as market relevant.          |
| filter\_start\_date         | string  | 2 years ago (UTC, date)         | No       | Start date (inclusive) for filtering trends by date.                        |
| filter\_end\_date           | string  | Today (UTC, date)               | No       | End date (inclusive) for filtering trends by date.                          |

**Response**

```json
{
  "data": [
    {
      "id": 1689,
      "title": "ai, artificial, generative, ais",
      "last_seen_at": "2025-11-10T22:22:01.039Z",
      "instance_first_seen": "2024-02-01T00:00:00.000Z",
      "instance_last_seen": "2025-11-10T00:00:00.000Z",
      "weighted_instance_count": 649
    }
  ],
  "meta": {
    "page": 1,
    "per_page": 100,
    "total_count": 118,
    "total_pages": 2
  }
}
```

## Open-Source Access

The open-source ForecastOS Python library includes utilities to retrieve persistent trend data and apply common transformations.

Persistent trend construction logic and source weighting are handled within the managed Hivemind platform.

### Example: Fetching Persistent Trends

```python
import forecastos as fos

df_persistent_trend = fos.PersistentTrend.get_df(
  min_days_market_relevant=100,
  filter_start_date='2020-01-01',
  filter_end_date='2025-01-01'
)
```

**Parameters**

| Parameter                  | Type    | Default                         | Required | Description                                                                 |
|----------------------------|---------|---------------------------------|----------|-----------------------------------------------------------------------------|
| min\_days\_market\_relevant | integer | 1                               | No       | Minimum number of days a trend must be flagged as market relevant.          |
| filter\_start\_date         | string  | 2 years ago (UTC, date)         | No       | Start date (inclusive) for filtering trends by date.                        |
| filter\_end\_date           | string  | Today (UTC, date)               | No       | End date (inclusive) for filtering trends by date.                          |

This returns a time-series DataFrame for all the persistent trends matching the filter parameters.

## Next: Hivemind Custom Trends

Let's explore [Hivemind Custom Trends](/guides/hivemind_basic/custom_trend) next.