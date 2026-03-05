<h1>Hivemind: Universes</h1>

## What Are Hivemind Universes?

Hivemind universes allow users to define custom sets of companies and the time periods during which those companies are active. By specifying tickers with optional start and end dates, users control which companies are in the universe and when.

Universes are used when generating company exposures to control which companies are included.

## UI Access

Universes can be explored, created, customized, and downloaded in the ForecastOS UI.

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