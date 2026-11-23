from pymongo import MongoClient
from backend.config import Config

class Database:
    client = None
    db = None

    @classmethod
    def connect(cls):
        if cls.client is None:
            cls.client = MongoClient(Config.MONGO_URI)
            cls.db = cls.client[Config.DB_NAME]
        return cls.db

    @classmethod
    def get_collection(cls, name):
        database = cls.connect()
        return database[name]