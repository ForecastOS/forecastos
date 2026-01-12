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

### Example: Fetching Trends

```bash
curl -X GET "https://api.forecastos.com/api/v1/trends" \
-H "Authorization: Bearer YOUR_API_TOKEN" \
-H "Content-Type: application/json"
```

**Query Parameters**

| Parameter          | Type    | Default | Required | Description                                               |
|-------------------|---------|---------|----------|-----------------------------------------------------------|
| page              | integer | 1       | No       | Page number for pagination.                                |
| market_relevant   | boolean | false   | No       | Return trends that are only flagged as market relevant or not. |


**Response**

```json
{
  "data": [
    {
      "id": 21141,
      "start_date": "2025-05-24T00:00:00.000Z",
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

## Open-Source Access

The open-source ForecastOS Python library provides helpers to fetch, normalize, transform, and align Hivemind trend time series data for research and modeling workflows.

Core trend construction and source ingestion remain managed services.

## Next: Hivemind Persistent Trends

Let's explore [Hivemind Persistent Trends](/guides/hivemind_basic/persistent_trend) next.
