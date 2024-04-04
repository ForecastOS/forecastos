from forecastos.saveable import Saveable


class Provider(Saveable):
    def __init__(self, name="", *args, **kwargs):
        self.name = name
        self.website = kwargs.get("website")

    @classmethod
    def list(cls, params={}):
        res = cls.get_request(
            path="/providers",
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

    def create(self):
        res = self.save_record(
            path="/providers",
            body=self.fh_params(),
            fh=True,
        )

        if res.ok:
            return self.sync_return(res.json())
        else:
            print(res)
            return False

    def fh_params(self):
        return {
            "provider": {
                "name": self.name,
                "website": self.website,
            }
        }
