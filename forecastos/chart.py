from forecastos.saveable import Saveable


class Chart(Saveable):
    def __init__(self, chartable_type, chartable_id, *args, **kwargs):
        self.chartable_type = chartable_type
        self.chartable_id = chartable_id

    def create_ts_percentile_chart(self, val_column, date_column, df):
        df = (
            df.groupby(date_column)[val_column]
            .quantile([0.1, 0.5, 0.9])
            .unstack()
            .dropna()
        )

        return self.save_record(
            path="/charts/create_or_update",
            body={
                "chart": {
                    "title": "Percentile evolution",
                    "chartable_type": self.chartable_type,
                    "chartable_id": self.chartable_id,
                    "chart_traces": [
                        {
                            "x_name": "Dates",
                            "y_name": "90th Percentile",
                            "x_values": [str(d) for d in df.index.tolist()],
                            "y_values": df[0.9].to_list(),
                        },
                        {
                            "x_name": "Dates",
                            "y_name": "50th Percentile",
                            "x_values": [str(d) for d in df.index.tolist()],
                            "y_values": df[0.5].to_list(),
                        },
                        {
                            "x_name": "Dates",
                            "y_name": "10th Percentile",
                            "x_values": [str(d) for d in df.index.tolist()],
                            "y_values": df[0.1].to_list(),
                        },
                    ],
                }
            },
        )

    def create_ts_count_chart(self, val_column, date_column, df):
        # Aggregation functions
        def gt_0(x):
            return (x > 0).sum()

        def lt_0(x):
            return (x < 0).sum()

        def eq_0(x):
            return (x == 0).sum()

        def is_na(x):
            return x.isna().sum()

        df = df.groupby("date")[val_column].agg([gt_0, lt_0, eq_0, is_na]).dropna()

        return self.save_record(
            path="/charts/create_or_update",
            body={
                "chart": {
                    "title": "Count evolution",
                    "chartable_type": self.chartable_type,
                    "chartable_id": self.chartable_id,
                    "chart_traces": [
                        {
                            "x_name": "Dates",
                            "y_name": "gt_0",
                            "x_values": [str(d) for d in df.index.tolist()],
                            "y_values": df["gt_0"].to_list(),
                        },
                        {
                            "x_name": "Dates",
                            "y_name": "lt_0",
                            "x_values": [str(d) for d in df.index.tolist()],
                            "y_values": df["lt_0"].to_list(),
                        },
                        {
                            "x_name": "Dates",
                            "y_name": "eq_0",
                            "x_values": [str(d) for d in df.index.tolist()],
                            "y_values": df["eq_0"].to_list(),
                        },
                        {
                            "x_name": "Dates",
                            "y_name": "is_na",
                            "x_values": [str(d) for d in df.index.tolist()],
                            "y_values": df["is_na"].to_list(),
                        },
                    ],
                }
            },
        )

    def create_scatter(self, title, x_name, y_name, config, x_values, y_values):
        return self.save_record(
            path="/charts/create_or_update",
            body={
                "chart": {
                    "title": title,
                    "chartable_type": self.chartable_type,
                    "chartable_id": self.chartable_id,
                    "config": config,
                    "chart_traces": [
                        {
                            "x_name": x_name,
                            "y_name": y_name,
                            "x_values": (
                                x_values
                                if isinstance(x_values, list)
                                else x_values.tolist()
                            ),
                            "y_values": (
                                y_values
                                if isinstance(y_values, list)
                                else y_values.tolist()
                            ),
                            "config": {"mode": "markers"},
                        },
                    ],
                }
            },
        )

    def create_histogram(self, title, x_name, x_values, config={}):
        return self.save_record(
            path="/charts/create_or_update",
            body={
                "chart": {
                    "title": title,
                    "chartable_type": self.chartable_type,
                    "chartable_id": self.chartable_id,
                    "config": config,
                    "chart_traces": [
                        {
                            "x_name": x_name,
                            "x_values": (
                                x_values
                                if isinstance(x_values, list)
                                else x_values.tolist()
                            ),
                            "config": {"type": "histogram"},
                        },
                    ],
                }
            },
        )

    def create_bar_chart(self, title, x_values, y_values, config={}):
        return self.save_record(
            path="/charts/create_or_update",
            body={
                "chart": {
                    "title": title,
                    "chartable_type": self.chartable_type,
                    "chartable_id": self.chartable_id,
                    "config": config,
                    "chart_traces": [
                        {
                            "x_values": (
                                x_values
                                if isinstance(x_values, list)
                                else x_values.tolist()
                            ),
                            "y_values": (
                                y_values
                                if isinstance(y_values, list)
                                else y_values.tolist()
                            ),
                            "config": {"type": "bar"},
                        },
                    ],
                }
            },
        )
