from forecastos.saveable import Saveable
from forecastos.chart import Chart

import pandas as pd


class Forecast(Saveable):
    def __init__(self, name, description, feature_ids=[], *args, **kwargs):
        self.name = name
        self.description = description
        self.feature_ids = feature_ids

        self.universe = kwargs.get("universe")
        self.algorithm = kwargs.get("algorithm")
        self.forecast_type = kwargs.get("forecast_type")
        self.model_location = kwargs.get("model_location")
        self.time_series = kwargs.get("time_series")
        self.string_id = kwargs.get("string_id")

        self.hyperparameters = kwargs.get("hyperparameters", {})
        self.performance_summary = kwargs.get("performance_summary", {})

        self.tags = kwargs.get("tags", [])
        self.team_ids = kwargs.get("team_ids", [])
        self.charts = kwargs.get("charts", [])

        self.save()

    def save(self):
        return self.save_record(
            path="/forecasts/create_or_update",
            body={
                "forecast": {
                    "name": self.name,
                    "description": self.description,
                    "feature_ids": self.feature_ids,
                    "universe": self.universe,
                    "algorithm": self.algorithm,
                    "forecast_type": self.forecast_type,
                    "model_location": self.model_location,
                    "time_series": self.time_series,
                    "string_id": self.string_id,
                    "hyperparameters": self.hyperparameters,
                    "performance_summary": self.performance_summary,
                    "tags": self.tags,
                    "team_ids": self.team_ids,
                }
            },
        )

    def create_actual_vs_forecast_chart(self, *args, **kwargs):
        return Chart(chartable_type="Forecast", chartable_id=self.id).create_scatter(
            title="Actual vs Forecast",
            x_name="Actual",
            y_name="Forecast",
            config={
                "xaxis": {"title": {"text": "Actual"}},
                "yaxis": {"title": {"text": "Forecast"}},
            },
            *args,
            **kwargs
        )

    def create_forecast_vs_residual_chart(self, *args, **kwargs):
        return Chart(chartable_type="Forecast", chartable_id=self.id).create_scatter(
            title="Forecast vs Residual",
            x_name="Forecast",
            y_name="Residual",
            config={
                "xaxis": {"title": {"text": "Forecast"}},
                "yaxis": {"title": {"text": "Residual"}},
            },
            *args,
            **kwargs
        )

    def create_residuals_histogram(self, *args, **kwargs):
        return Chart(chartable_type="Forecast", chartable_id=self.id).create_histogram(
            title="Residuals Histogram", x_name="Residuals", *args, **kwargs
        )

    def create_feature_importance_chart(self, x_values, importances, *args, **kwargs):
        df_tmp = (
            pd.Series(importances, index=x_values)
            .sort_values(ascending=False)
            .iloc[:10]
        )
        return Chart(chartable_type="Forecast", chartable_id=self.id).create_bar_chart(
            title="Feature Importance",
            x_values=df_tmp.index.tolist(),
            y_values=df_tmp.values.tolist(),
            config={"xaxis": {"tickfont": {"size": 8}}},
            *args,
            **kwargs
        )
