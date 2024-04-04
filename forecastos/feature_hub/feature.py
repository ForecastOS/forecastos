from forecastos.saveable import Saveable
import pandas as pd
from pandas.api.types import is_object_dtype


class Feature(Saveable):
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
        self.provider_ids = kwargs.get("provider_ids", [])

    @classmethod
    def get(cls, uuid):
        res = cls.get_request(
            path=f"/fh_features/{uuid}",
            fh=True,
        )

        if res.ok:
            return cls.init_sync_return(res.json())
        else:
            print(res)
            return False

    @classmethod
    def list(cls, params={}):
        res = cls.get_request(
            path=f"/fh_features",
            params=params,
            fh=True,
        )

        if res.ok:
            return [cls.init_sync_return(obj) for obj in res.json()]
        else:
            print(res)
            return False

    @classmethod
    def find(cls, query=""):
        return cls.list(params={"q": query})

    def upload_df(self, df):
        val_col = "val"

        # Set memory_usage
        self.memory_usage = df.memory_usage(deep=True).sum() / (1024**2)

        # Enforce existence of expected columns only
        required_columns = [
            col
            for col in [*self.id_columns, self.datetime_column, val_col]
            if col != None
        ]
        invalid_cols = [col for col in df.columns if col not in required_columns]
        doesnt_include_required_cols = not all(
            column in df.columns for column in required_columns
        )
        if invalid_cols:
            print(
                f"Unexpected invalid columns in df: {invalid_cols}. Upload cancelled."
            )
            return False
        elif doesnt_include_required_cols:
            print(
                f"Doesn't include all required columns in df. Should include: {[col for col in required_columns if col not in df.columns]}. Upload cancelled."
            )
            return False

        # Ensure column is type datetime
        if self.datetime_column:
            df = df.copy()
            df[self.datetime_column] = pd.to_datetime(df[self.datetime_column])

        # Add schema info
        self.schema = df.dtypes.to_dict()

        if is_object_dtype(df[val_col]):
            print(
                "Choose more specific data type for val column, like int, float, str/text, bool, or datetime."
            )
            return False

        # [ ] Set file_location (based on uuid, env)
        # And bucket
        # [ ] create_or_update
        # [ ] Can write file as uuid_new.parquet, then mv to uuid.parquet, then remove uuid_new.parquet
        # [ ] Create_or_update

    def create(self):
        res = self.save_record(
            path="/fh_features",
            body=self.fh_feature_params(),
            fh=True,
        )

        if res.ok:
            return self.sync_return(res.json())
        else:
            print(res)
            return False

    def create_or_update(self):
        res = self.save_record(
            path="/fh_features/create_or_update",
            body=self.fh_feature_params(),
            fh=True,
        )

        if res.ok:
            return self.sync_return(res.json())
        else:
            print(res)
            return False

    def __str__(self):
        return f"Feature_{self.uuid}_{self.name}"

    def info(self):
        return self.__dict__

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
                "memory_usage": self.memory_usage,
                "fill_method": self.fill_method,
                "id_columns": self.id_columns,
                "provider_ids": self.provider_ids,
            }
        }
