<h1>UI vs API vs Open-Source</h1>

ForecastOS is designed to meet users where they are in the research-to-production lifecycle. You can interact with the platform through the **UI**, the **API**, or **open-source PyPI module** (which uses the API).

Below is a practical guide to choosing the right interface.

### When to Use the UI

The ForecastOS UI is best suited for **discovery, exploration, and decision-making**, especially when you want fast iteration without writing code.

**Ideal use cases**

* Exploring trends, narratives, and exposures interactively
* Validating hypotheses
* Comparing factors, signals, and historical behaviour visually
* Sharing insights with teammates, PMs, or stakeholders

**Why the UI works well**

* Point-and-click access to complex datasets and derived signals
* Built-in visualization
* Designed for collaboration

**Typical users**

* Portfolio managers
* Researchers doing exploratory analysis
* Investment committees

### When to Use the API / Open-Source

The ForecastOS API and open-source are designed for **automation, production workflows, and technical research**.

**Ideal use cases**

* Integrating ForecastOS data into live or backtesting pipelines
* Systematic portfolio construction and optimisation
* Large-scale historical analysis or research
* Extending ForecastOS outputs with internal data

**Why the API / Open-Source works well**

* Bulk access to data / outputs (especially via open-source)
* Designed for institutional data workflows
* Freedom to modify and extend

**Typical users**

* Quant researchers
* Data scientists
* Engineers
* Systematic investment teams

### A Common Pattern: UI → API / Open-Source

A typical workflow looks like this:

1. **Explore ideas in the UI**
2. **Operationalise the signals via the API or open-source**

When possible, the UI is great for quick exploration.

### Summary

If you’re unsure where to start: **start in the UI**, then move to the API / open-source as your use case matures or you need to download and work with all of the data.

## Next: The Choice Is Yours

What's next is up to you:

- Check out [Why Hivemind](/guides/hivemind_basic/why_hivemind) if you want to dive into Hivemind.
- Check out [Why FeatureHub](/guides/featurehub/why_featurehub) if you want to explore FeatureHub.
- Check out [Why InvestOS](/guides/investos/why_investos) if you want to check out our open-source portfolio construction and backtesting solution.