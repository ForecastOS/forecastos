<h1>Hivemind: Universes</h1>

## What Are Hivemind Universes?

Hivemind company exposures measure how strongly each company is associated with specific trends, narratives, or themes at a given point in time. They map any custom-defined exposure onto individual securities, producing cross-sectional exposure scores that can be used for risk analysis, attribution, portfolio construction, and alpha.

## UI Access

Company exposures can be explored, created, customized, and downloaded in the ForecastOS UI, where users can analyze exposures by company, sector, or market portfolio and monitor how exposures have evolved throughout time.

![Hivemind Custom Trends](/screenshot_company_exposures.png)

## API Access

### Example: Updating Exposure Universe via API

```bash
curl -X PATCH "https://app.forecastos.com/api/v1/universes/<UNIVERSE_ID>" \
-H "Authorization: Bearer YOUR_API_TOKEN" \
-F "companies_csv=@<PATH_TO_COMPANIES_CSV>"
```

This updates the companies in the universe using the provided CSV file. [Click here to download an example CSV.](/example_universe_upload.csv)

## Next: Hivemind PIT Context

Let's explore [Hivemind PIT Context](/guides/hivemind_basic/pit_context) next.