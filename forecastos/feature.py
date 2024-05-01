from forecastos.utils.readable import Readable
import pandas as pd
import os


class Feature(Readable):
    def __init__(self, name="", description="", *args, **kwargs):
        self.name = name
        self.description = description
        self.uuid = None

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

        self.memory_usage = kwargs.get("memory_usage")

        self.fill_method = kwargs.get("fill_method", [])
        self.id_columns = kwargs.get("id_columns", [])
        self.supplementary_columns = kwargs.get("supplementary_columns", [])
        self.provider_ids = kwargs.get("provider_ids", [])

    @classmethod
    def get(cls, uuid):
        res = cls.get_request(path=f"/fh_features/{uuid}")

        if res.ok:
            return cls.sync_read(res.json())
        else:
            print(res)
            return False

    def get_df(self):
        res = self.__class__.get_request(
            path=f"/fh_features/{self.uuid}/url",
        )

        if res.ok:
            return pd.read_parquet(res.json()["url"])
        else:
            print(res)
            return False

    @classmethod
    def list(cls, params={}):
        res = cls.get_request(
            path=f"/fh_features",
            params=params,
        )

        if res.ok:
            return [cls.sync_read(obj) for obj in res.json()]
        else:
            print(res)
            return False

    @classmethod
    def find(cls, query=""):
        return cls.list(params={"q": query})

    def info(self):
        return self.__dict__

    def __str__(self):
        return f"Feature_{self.uuid}_{self.name}"
