from forecastos.utils.readable import Readable
from forecastos.utils.saveable import Saveable
import pandas as pd
import os


class Forecast(Readable, Saveable):
    def __init__(self, name, description, universe, algorithm, forecast_type, *args, **kwargs):
        self.name = name
        self.description = description
        self.universe = universe
        self.algorithm = algorithm
        self.forecast_type = forecast_type

        self.string_id = kwargs.get("string_id", name)
        self.time_series = kwargs.get("time_series", True)
        self.hyperparameters = kwargs.get("hyperparameters", {})
        self.performance_summary = kwargs.get("performance_summary", {})
        self.tags = kwargs.get("tags", {})
        self.fh_feature_ids = kwargs.get("fh_feature_ids", [])

    @classmethod
    def get(cls, id):
        res = cls.get_request(path=f"/forecasts/{id}", use_team_key=True)

        if res.ok:
            return cls.sync_read(res.json())
        else:
            print(res)
            return False
    
    def save(self):
        res = self.post_request(path=f"/forecasts/create_or_update", body={
            "forecast": {
                "name": self.name,
                "description": self.description,
                "universe": self.universe,
                "algorithm": self.algorithm,
                "forecast_type": self.forecast_type,
                "string_id": self.string_id,
                "time_series": self.time_series,
                "hyperparameters": self.hyperparameters,
                "performance_summary": self.performance_summary,
                "tags": self.tags,
                "fh_feature_ids": self.fh_feature_ids,
            }
        })

        if res.ok:
            print(f"Forecast {self.name} saved.")
            self.id = res.json()["id"]
            return self
        else:
            print(res)
            return self


    def info(self):
        return self.__dict__

    def __str__(self):
        return f"Forecast_{self.name}"
