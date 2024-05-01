from forecastos.saveable import Saveable
import pandas as pd
from pandas.api.types import is_object_dtype
import io
import boto3
from botocore.exceptions import NoCredentialsError
import os


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
        self.supplementary_columns = kwargs.get("supplementary_columns", [])
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

    def get_df(self):
        res = self.__class__.get_request(
            path=f"/fh_features/{self.uuid}/url",
            fh=True,
        )

        if res.ok:
            return pd.read_parquet(res.json()["url"])
        else:
            print(res)
            return False

    def info(self):
        return self.__dict__

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

    def create_or_update(self, df=None):
        return self.save(df)

    def save(self, df=None):
        res = self.save_record(
            path="/fh_features/create_or_update",
            body=self.fh_feature_params(),
            fh=True,
        )

        if res.ok:
            self.sync_return(res.json())
            if df is not None:
                return self.upload_df(df)
            else:
                return self
        else:
            print(res)
            return False

    def __str__(self):
        return f"Feature_{self.uuid}_{self.name}"

    def upload_df(self, df):
        val_col = "value"

        # Set memory_usage
        self.memory_usage = df.memory_usage(deep=True).sum() / (1024**2)

        # Enforce existence of expected columns only
        required_columns = [
            col
            for col in [
                *self.id_columns,
                *self.supplementary_columns,
                self.datetime_column,
                val_col,
            ]
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
        if is_object_dtype(df[val_col]) and self.value_type != "text":
            print(
                "Choose more specific data type for val column, like int, float, str/text, bool, or datetime."
            )
            return False
        else:
            self.schema = {key: str(value) for key, value in self.schema.items()}

        # Upload file, then update record in FeatureHub
        if self.upload_df_to_s3(df):
            print("File processed successfully.")
            return self.save()
        else:
            print("File processing failed.")
            return False

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
                "supplementary_columns": self.supplementary_columns,
                "provider_ids": self.provider_ids,
            }
        }

    def upload_df_to_s3(self, df):
        """
        Upload a file to an S3 bucket to a temporary location, then move it to the final location, and finally remove the temporary file.
        :return: True if process is successful, else False
        """
        temp_object_name = f"FeatureHub/features/{self.uuid}_new.parquet"
        final_object_name = f"FeatureHub/features/{self.uuid}.parquet"
        bucket_name = os.environ.get("SKYLIGHT_FH_S3_BUCKET") or os.environ.get(
            "S3_BUCKET"
        )
        region = os.environ.get("SKYLIGHT_FH_S3_REGION") or os.environ.get("S3_REGION")
        access_key_id = os.environ.get("SKYLIGHT_FH_S3_ACCESS_KEY") or os.environ.get(
            "S3_ACCESS_KEY"
        )
        secret_access_key = os.environ.get(
            "SKYLIGHT_FH_S3_SECRET_ACCESS_KEY"
        ) or os.environ.get("S3_SECRET_ACCESS_KEY")

        # Create an S3 client with specified AWS credentials
        s3_client = boto3.client(
            "s3",
            region_name=region,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
        )
        try:
            # Convert DataFrame to Parquet format in memory
            buffer = io.BytesIO()
            df.to_parquet(buffer, index=False)
            buffer.seek(0)  # Reset buffer position to the beginning after writing

            # Step 1: Upload the file to the temporary location
            s3_client.upload_fileobj(buffer, bucket_name, temp_object_name)

            # Step 2: Copy the file from the temporary location to the final location
            copy_source = {"Bucket": bucket_name, "Key": temp_object_name}
            s3_client.copy(copy_source, bucket_name, final_object_name)

            # Step 3: Delete the temporary file
            s3_client.delete_object(Bucket=bucket_name, Key=temp_object_name)
        except NoCredentialsError as e:
            print(e)
            return False
        except Exception as e:
            print(f"Error during file operation: {e}")
            return False

        self.file_location = final_object_name
        return True
