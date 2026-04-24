<h1>Hivemind: Trends</h1>

## What Are Hivemind Trends?

Hivemind trends are point-in-time measurements of how frequently and how strongly specific macro, thematic, or narrative concepts appear in aggregated discussion.

They quantify evolving focus on ideas such as inflation, AI, geopolitics, regulations, etc.

Trends update continuously and are designed to capture drivers of risk and return that are not well explained by traditional style or factor models.

## UI Access

Hivemind Trends can be explored directly in the ForecastOS UI, where users can browse trend histories, compare trends over time, and inspect how narratives evolve across market regimes.

![Hivemind Trends](/screenshot_trends.png)

## API Access

Hivemind trends are available via the ForecastOS API for programmatic access and integration into research and portfolio workflows.

### Example: Fetching Trends via API

```bash
curl -X GET "https://app.forecastos.com/api/v1/trends" \
-H "Authorization: Bearer YOUR_API_TOKEN" \
-H "Content-Type: application/json"
```

**Query Parameters**

| Parameter          | Type    | Default | Required | Description                                               |
|-------------------|---------|---------|----------|-----------------------------------------------------------|
| page              | integer | 1       | No       | Page number for pagination.                                |
| market_relevant   | boolean | false   | No       | Only return trends that are flagged as market relevant or not. |
| identified\_on\_start   | string | -   | No       | Only return trends that were identified after or on this date. Must be in YYYY-MM-DD format. |
| identified\_on\_end   | string | -   | No       | Only return trends that were identified before or on this date. Must be in YYYY-MM-DD format. |

**Response**

```json
{
  "data": [
    {
      "id": 21141,
      "end_date": "2025-06-23T00:00:00.000Z",
      "title": "debate, argument, arguments, debates",
      "market_relevant": false,
      "trend_rank": 72,
      "topic_size_rank": 117,
      "short_term_growth_rank": 211,
      "long_term_growth_rank": 116,
      "short_term_growth": 1.0320599421203407,
      "long_term_growth": 1.1348288716421182
    }
  ],
  "meta": {
    "page": 1,
    "per_page": 2500,
    "total_count": 54600,
    "total_pages": 22
  }
}
```

### Example: Fetching Associated Exposures via API

This returns company exposures associated with a trend, sorted by similarity (highest first).

```bash
curl -X GET "https://app.forecastos.com/api/v1/trends/<TREND_ID>/associated_exposures" \
-H "Authorization: Bearer YOUR_API_TOKEN" \
-H "Content-Type: application/json"
```

**Query Parameters**

| Parameter          | Type    | Default | Required | Description                                               |
|-------------------|---------|---------|----------|-----------------------------------------------------------|
| page              | integer | 1       | No       | Page number for pagination.                                |

**Response**

```json
{
  "data": [
    {
        "id": 1,
        "created_at": "2026-03-09T23:37:30.466Z",
        "updated_at": "2026-03-09T23:37:30.466Z",
        "exposure_topic": "Venezuela"
    }
  ],
  "meta": {
      "page": 1,
      "per_page": 5000,
      "total_count": 2,
      "total_pages": 1
  }
}
```

## Open-Source Access

The open-source ForecastOS Python library provides helpers to fetch, normalize, transform, and align Hivemind trend time series data for research and modeling workflows.

Core trend construction and source ingestion remain managed services.

### Example: Fetching Trends via OS
```python
import forecastos as fos

df_trend = fos.Trend.get_df(
  market_relevant=True,
  identified_on_start='2025-11-09',
  identified_on_end='2025-11-10'
)
```

**Parameters**

| Parameter          | Type    | Default | Required | Description                                               |
|-------------------|---------|---------|----------|-----------------------------------------------------------|
| market_relevant   | boolean | false   | No       | Only return trends that are flagged as market relevant or not. |
| identified\_on\_start   | string | -   | No       | Only return trends that were identified after or on this date. Must be in YYYY-MM-DD format. |
| identified\_on\_end   | string | -   | No       | Only return trends that were identified before or on this date. Must be in YYYY-MM-DD format. |

This returns a time-series DataFrame for all the trends matching the filter parameters.

## Next: Hivemind Persistent Trends

Let's explore [Hivemind Persistent Trends](/guides/hivemind_basic/persistent_trend) next.
