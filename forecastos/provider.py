from forecastos.utils.readable import Readable


class Provider(Readable):
    def __init__(self, name="", *args, **kwargs):
        self.name = name
        self.website = kwargs.get("website")

    @classmethod
    def list(cls, params={}):
        res = cls.get_request(
            path="/providers",
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
