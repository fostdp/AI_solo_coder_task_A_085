from pymongo import MongoClient
from django.conf import settings

def get_db():
    client = MongoClient(
        settings.MONGODB_DATABASES['default']['host'],
        settings.MONGODB_DATABASES['default']['port']
    )
    return client[settings.MONGODB_DATABASES['default']['name']]

def get_collection(collection_name):
    db = get_db()
    return db[collection_name]
