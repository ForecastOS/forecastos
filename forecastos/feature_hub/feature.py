from forecastos.saveable import Saveable


class Feature(Saveable):
    def __init__(self, name, description, *args, **kwargs):
        self.name = name
        self.description = description

        self.calc_methodology = kwargs.get("calc_methodology")
        self.category = kwargs.get("category")
        self.subcategory = kwargs.get("subcategory")

        self.suggested_delay_s = kwargs.get("suggested_delay_s", 0)
        self.suggested_delay_description = kwargs.get("suggested_delay_description")

        self.universe = kwargs.get("universe")

        self.time_delta = kwargs.get("time_delta")

        self.file_location = kwargs.get("file_location")
        self.schema = kwargs.get("schema")
        self.datetime_column = kwargs.get("datetime_column")
        self.value_type = kwargs.get("value_type")
        self.timeseries = kwargs.get("timeseries")

        self.fill_method = kwargs.get("fill_method", [])
        self.id_columns = kwargs.get("id_columns", [])
        self.provider_ids = kwargs.get("provider_ids", [])

    @classmethod
    def find(cls, query=""):
        return cls.get(
            path="/fh_features",
            params={"q": query},
            fh=True,
        )

    def create(self):
        return self.save_record(
            path="/fh_features",
            body=self.fh_feature_params(),
            fh=True,
        )

    def create_or_update(self):
        return self.save_record(
            path="/fh_features/create_or_update",
            body=self.fh_feature_params(),
            fh=True,
        )

    def fh_feature_params(self):
        return {
            "fh_feature": {
                "name": self.name,
                "description": self.description,
                "calc_methodology": self.calc_methodology,
                "category": self.category,
                "subcategory": self.subcategory,
                "suggested_delay_s": self.suggested_delay_s,
                "suggested_delay_description": self.suggested_delay_description,
                "universe": self.universe,
                "time_delta": self.time_delta,
                "file_location": self.file_location,
                "schema": self.schema,
                "datetime_column": self.datetime_column,
                "value_type": self.value_type,
                "timeseries": self.timeseries,
                "fill_method": self.fill_method,
                "id_columns": self.id_columns,
                "provider_ids": self.provider_ids,
            }
        }
