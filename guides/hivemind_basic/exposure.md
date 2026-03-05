<h1>Hivemind: Company Exposures</h1>

## What Are Hivemind Company Exposures?

Hivemind company exposures measure how strongly each company is associated with specific trends, narratives, or themes at a given point in time. They map any custom-defined exposure onto individual securities, producing cross-sectional exposure scores that can be used for risk analysis, attribution, portfolio construction, and alpha.

## UI Access

Company exposures can be explored, created, customized, and downloaded in the ForecastOS UI, where users can analyze exposures by company, sector, or market portfolio and monitor how exposures have evolved throughout time.

![Hivemind Custom Trends](/screenshot_company_exposures.png)

## API Access

### Example: Fetching Exposures via API

```bash
curl -X GET "https://app.forecastos.com/api/v1/exposures/company/<EXPOSURE_ID>" \
-H "Authorization: Bearer YOUR_API_TOKEN" \
-H "Content-Type: application/json"
```

This returns a time-series CSV containing company-level exposure scores.

## Open-Source Access

Hivemind company exposures are accessible via the open-source `forecastos` Python library through the `Exposure` class.

This class retrieves point-in-time company exposure data from the ForecastOS API and provides helpers to merge, normalize, and transform exposures for research and portfolio workflows.

### Example: Fetching Exposures via OS

```python
import forecastos as fos

# Fetch PIT exposure df
df_exposure = fos.Exposure.get_df(id=123)
```

This returns a time-series DataFrame containing company-level exposure scores.

## Next: Hivemind Custom Pipelines

Let's explore [Hivemind Custom Pipelines](/guides/hivemind_basic/pipeline) next.