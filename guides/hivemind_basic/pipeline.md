<h1>Hivemind: Custom Pipelines</h1>

## What Are Hivemind Custom Pipelines?

Hivemind custom pipelines expose the full set of tools used internally to construct company exposures.

They allow users to build end-to-end pipelines by combining structured data (from FeatureHub and elsewhere), unstructured data, and GenAI-driven transformations into custom, point-in-time derived signals.

Pipelines are fully configurable, with user-defined inputs, processing nodes / instructions, and outputs.

They can be used to create bespoke exposures, risk / alpha signals, or entirely new analytical artifacts beyond the standard Hivemind objects.

## UI Access

Custom pipelines can be built and inspected in the ForecastOS UI, where users visually compose nodes, configure transformations, and access outputs.

![Hivemind Custom Pipeline](/screenshot_exposure_pipeline.png)

## API Access

Pipeline run creation and associated outputs are accessible via API.

### Example: Running Pipelines

```bash
curl -X POST "https://api.forecastos.com/api/v1/pipelines/<PIPELINE_ID>/runs" \
-H "Authorization: Bearer YOUR_API_TOKEN" \
-H "Content-Type: application/json" \
-d '{
  "generate_charts": true,
  "use_latest_data_only": false,
  "start_date": "2025-01-01",
  "end_date": "2026-01-01",
  "variables": {
    "var1": "value1",
    "var2": "value2"
  }
}'
```

**Body Parameters**

| Parameter              | Type    | Default             | Required | Description                                                                                       |
|------------------------|---------|---------------------|----------|---------------------------------------------------------------------------------------------------|
| generate_charts        | boolean | pipeline default    | No       | If true, charts will be automatically generated once pipeline results are complete.                                               |
| use\_latest\_data\_only   | boolean | pipeline default    | No       | If true, only the latest available data will be used for the pipeline run. Otherwise, a start and end date can be provided to limit the data range. ||
| latest\_data\_as\_of\_date | string  | current date        | No       | The reference date for the latest filings, set this if use\_latest\_data\_only is true. Must be in YYYY-MM-DD format.                        |
| start_date | string | "2016-01-01" | No | Only include data published from this date. Set this if use\_latest\_data\_only is false. Must be in YYYY-MM-DD format. |
| end_date | string | current date | No | Only include data published up to this date. Set this if use\_latest\_data\_only is false. Must be in YYYY-MM-DD format. |                         |
| variables              | object  | - | Yes      | A dictionary of variables for the pipeline. Must include keys for all expected pipeline variables. |

### Example: Fetching Pipeline Run Results

```bash
curl -X GET "https://api.forecastos.com/api/v1/pipelines/<PIPELINE_ID>/runs/<PIPELINE_RUN_ID>" \
-H "Authorization: Bearer YOUR_API_TOKEN" \
-H "Content-Type: application/json"
```

This returns a time-series CSV containing company-level results for your pipeline run.

## Open-Source Access

The open-source ForecastOS Python library provides helpers for consuming pipeline outputs and integrating them into downstream research, risk, and portfolio workflows.

## Next: Hivemind Risk Applications

Let's explore [Hivemind Risk Applications](/guides/hivemind_advanced/risk_applications) next.