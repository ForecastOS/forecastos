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
curl -X POST "https://api.forecastos.com/api/v1/pipelines/<>" \
-H "Authorization: Bearer YOUR_API_TOKEN" \
-H "Content-Type: application/json"
```

### Example: Fetching Pipeline Results

```bash
curl -X GET "https://api.forecastos.com/api/v1/pipelines/<PIPELINE_ID>" \
-H "Authorization: Bearer YOUR_API_TOKEN" \
-H "Content-Type: application/json"
```

This returns a time-series CSV containing company-level results for your pipeline.

## Open-Source Access

The open-source ForecastOS Python library provides helpers for consuming pipeline outputs and integrating them into downstream research, risk, and portfolio workflows.

## Next: Hivemind Risk Applications

Let's explore [Hivemind Risk Applications](/guides/hivemind_advanced/risk_applications) next.