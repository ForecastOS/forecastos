from forecastos.saveable import Saveable
from forecastos.chart import Chart


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

    def create_ts_percentile_chart(self, *args, **kwargs):
        return Chart(
            chartable_type="Feature", chartable_id=self.id
        ).create_ts_percentile_chart(*args, **kwargs)

    def create_ts_count_chart(self, *args, **kwargs):
        return Chart(
            chartable_type="Feature", chartable_id=self.id
        ).create_ts_count_chart(*args, **kwargs)
