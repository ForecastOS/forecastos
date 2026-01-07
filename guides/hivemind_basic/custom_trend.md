<h1>Hivemind: Custom Trends</h1>

## What Are Hivemind Custom Trends?

Hivemind custom trends allow users to define their own concepts and narratives and measure them consistently through time. By specifying keywords, phrases, or semantic descriptions, users can create bespoke trend signals that reflect portfolio-specific risks, themes, or investment theses.

Custom trends are point-in-time and constructed using the same underlying Hivemind ingestion and scoring framework as system-defined trends.

## UI Access

Custom trends can be created and explored in the ForecastOS UI, where users define concepts, review historical behavior, and compare custom narratives against existing Hivemind trends.

![Hivemind Custom Trends](/screenshot_custom_trends.png)

## API Access

Custom trends are available through the ForecastOS API for automated creation, updating, and retrieval.

### Example: Fetching Popularity Evolution For Custom Trend

```bash
curl -X POST "https://api.forecastos.com/api/v1/trends/custom" \
-H "Authorization: Bearer YOUR_API_TOKEN" \
-H "Content-Type: application/json" \
-d '{
  "trend": {
    "text": "artificial intelligence",
    "sensitivity": "medium",
    "start_date": "2020-01-01"
  }
}'
```

**Parameters**

| Parameter   | Type    | Default       | Required | Description                                                                                   |
|------------|---------|---------------|----------|-----------------------------------------------------------------------------------------------|
| text       | string  | —             | Yes      | The text for which to calculate the custom trend. This is used to generate the embedding.    |
| sensitivity| string  | "medium"      | No       | Determines the rolling sum calculation sensitivity. Options: "low", "medium", "high", "exact", "fuzzy". |
| start_date | string  | "2015-01-01"  | No       | Optional start date (YYYY-MM-DD) for the trend calculation. Defaults to 2015-01-01 if not provided. |


**Response**

```json
{
  "rolling_90d_popularity": {
    "2026-01-01": "0.0",
    "2026-01-02": "0.0",
    "2026-01-03": "0.0",
    "2026-01-04": "0.0",
    "2026-01-05": "0.0",
    "2026-01-06": "0.0"
  },
  "rolling_365d_popularity": {
    "2026-01-01": "0.0",
    "2026-01-02": "0.0",
    "2026-01-03": "0.0",
    "2026-01-04": "0.0",
    "2026-01-05": "0.0",
    "2026-01-06": "0.0"
  }
}
```

## Open-Source Access

The open-source ForecastOS Python library provides helpers for submitting custom trend definitions and consuming the resulting time series in research workflows.

Concept embedding, scoring, and source processing are handled within the managed Hivemind platform.

## Next: Hivemind Company Exposures

Let's explore [Hivemind Company Exposures](/guides/hivemind_basic/exposure) next.