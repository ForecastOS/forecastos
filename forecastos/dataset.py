from forecastos.saveable import Saveable


class Dataset(Saveable):
    def __init__(self, name, description, *args, **kwargs):
        self.name = name
        self.description = description

        self.group = kwargs.get("group")
        self.subgroup = kwargs.get("subgroup")
        self.universe = kwargs.get("universe")
        self.data_location = kwargs.get("data_location")
        self.time_series = kwargs.get("time_series")

        self.tags = kwargs.get("tags", [])
        self.team_ids = kwargs.get("team_ids", [])
        self.process_tables(kwargs.get("tables", {}))

        self.save()

    def process_tables(self, tables):
        self.tables = []
        for name, df in tables.items():
            self.tables.append(
                {
                    "name": name,
                    "row_count": df.shape[0],
                    "columns": {col: str(df[col].dtype) for col in df.columns},
                }
            )

    def save(self):
        return self.save_record(
            path="/datasets/create_or_update",
            body={
                "dataset": {
                    "name": self.name,
                    "description": self.description,
                    "group": self.group,
                    "subgroup": self.subgroup,
                    "universe": self.universe,
                    "data_location": self.data_location,
                    "time_series": self.time_series,
                    "tags": self.tags,
                    "team_ids": self.team_ids,
                    "tables": self.tables,
                }
            },
        )
