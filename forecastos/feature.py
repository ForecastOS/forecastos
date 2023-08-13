from forecastos.saveable import Saveable


class Feature(Saveable):
    def __init__(self, name, description, dataset_ids=[], *args, **kwargs):
        self.name = name
        self.description = description
        self.dataset_ids = dataset_ids

        self.group = kwargs.get("group")
        self.subgroup = kwargs.get("subgroup")
        self.universe = kwargs.get("universe")
        self.data_type = kwargs.get("data_type")
        self.data_location = kwargs.get("data_location")
        self.time_series = kwargs.get("time_series")

        self.tags = kwargs.get("tags", [])
        self.team_ids = kwargs.get("team_ids", [])
        self.charts = kwargs.get("charts", [])

        self.save()

    def save(self):
        return self.save_record(
            path="/features/create_or_update",
            body={
                "feature": {
                    "name": self.name,
                    "description": self.description,
                    "dataset_ids": self.dataset_ids,
                    "group": self.group,
                    "subgroup": self.subgroup,
                    "universe": self.universe,
                    "data_type": self.data_type,
                    "data_location": self.data_location,
                    "time_series": self.time_series,
                    "tags": self.tags,
                    "team_ids": self.team_ids,
                }
            },
        )

    def create_ts_percentile_chart(self, val_column, date_column, df):
        df = (
            df.groupby(date_column)[val_column]
            .quantile([0.1, 0.5, 0.9])
            .unstack()
            .dropna()
        )

        return self.save_record(
            path="/charts",
            body={
                "chart": {
                    "title": "Percentile evolution",
                    "chartable_type": "Feature",
                    "chartable_id": self.id,
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
