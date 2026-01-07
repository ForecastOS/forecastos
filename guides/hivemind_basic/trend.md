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

**Parameters**

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
      "long_term_growth": 1.1348288716421182,
      "centroid_binary_vector": "1001000111111000000111010110111010001000101000001100001001011110101000011001101101100111001101110010100101011001100101011101010100101111110011110101010100001011010101001011001110110111000101010111000001010011011100100101111110110011111011000111011111101100110001001111100001000010010101011110001001000010011011010101010000000110100011000011100111001111011100000101000010100100111000111101001000001110000101011111011001110011101011000001101001100111000010001010111001011111101010000101000110110001000111000000111101111001100101100000001111000110000111010010001001010000100011001001000110111001100000011010100011111001001001100000000011010101101000010010100100011100001100001110101110100000001010000110001000011000010000111110111101001011001011010000011010010011100110011010111110011000001101110011100110110100110100001000011011111010011100111101010010010111011001111001001000100111000101100010001110011101101011001001110001101000011000110101001110010011101000010100110111111010100111001101010110011010010100111000011100111000"
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
