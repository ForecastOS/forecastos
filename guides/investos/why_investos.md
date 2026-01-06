<h1>Why InvestOS</h1>

[InvestOS](https://investos.io), our open-source portfolio engineering and optimization engine, is built to help institutional investors turn research signals into *real, investable portfolios* with clarity, control, and discipline.

Most portfolio tools break down when real-world constraints, transaction costs, and evolving signals are introduced. InvestOS is designed from the ground up to handle those realities while remaining transparent, flexible, and production-ready.

## The Core Idea

* **Portfolio engineering, not black boxes:** InvestOS provides explicit, controllable portfolio construction logic rather than opaque optimizers.
* **Signals in, portfolios out:** combine alpha signals, risk models, constraints, and costs into a single, coherent optimization framework.
* **Built for real constraints:** handle turnover limits, position bounds, sector and factor exposures, transaction costs, and liquidity assumptions directly.
* **Research and production aligned:** the same code paths can be used in research, backtesting, and live portfolio construction.
* **Solver-flexible by design:** supports both open and closed-source optimizers via [cvxpy](https://www.cvxpy.org/), letting teams choose the solver that best fits their performance, licensing, and infrastructure needs.

## What You Can Do With It

* **Build investable portfolios:** translate factor and model outputs into portfolios that respect real-world constraints and trading realities.
* **Test portfolio decisions explicitly:** understand how constraints, costs, and risk targets affect outcomes rather than relying on heuristics.
* **Run systematic strategies at scale:** construct and rebalance portfolios consistently across universes, mandates, and frequencies.
* **Integrate seamlessly:** use InvestOS alongside ForecastOS FeatureHub and Hivemind, or plug in your own signals and risk models.

## Why It Matters Today

* **Alpha lives or dies at the portfolio layer.** Even strong signals can fail if portfolio construction is brittle or misaligned with reality.
* **Markets are more constrained.** Liquidity, crowding, and cost awareness are essential for sustainable performance.
* **Institutions need transparency.** InvestOS makes portfolio decisions auditable, explainable, and defensible to stakeholders.

## Open Source by Design

* **MIT licensed:** do whatever you want with it. Use it, modify it, extend it, or embed it in proprietary systems without restriction.
* **Fully open-source:** InvestOS is available on GitHub, allowing teams to inspect, extend, and trust the portfolio construction logic.
* **Model-agnostic:** bring your own signals, features, and risk models without being locked into proprietary assumptions.
* **Production-ready foundations:** designed for correctness, reproducibility, and long-term maintainability.

## Next: InvestOS External Guides

Let's explore the [InvestOS External Guides](/guides/investos/investos_external_guides) next.
