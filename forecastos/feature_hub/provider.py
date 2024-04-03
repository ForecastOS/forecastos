from forecastos.saveable import Saveable


class Provider(Saveable):
    def __init__(self, name, *args, **kwargs):
        self.name = name
        self.website = kwargs.get("website")

    @classmethod
    def find(cls, query=""):
        return cls.get(
            path="/providers",
            params={"q": query},
            fh=True,
        )

    def create(self):
        return self.save_record(
            path="/providers",
            body=self.fh_params(),
            fh=True,
        )

    def fh_params(self):
        return {
            "provider": {
                "name": self.name,
                "website": self.website,
            }
        }
