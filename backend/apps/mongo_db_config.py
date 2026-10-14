from django.contrib.admin.apps import AdminConfig
from django.contrib.auth.apps import AuthConfig
from django.contrib.contenttypes.apps import ContentTypesConfig
from django.db.models.signals import post_migrate
from pymongo import MongoClient, ASCENDING


def skip_create_permissions(sender, **kwargs):
    pass


class MongoAdminConfig(AdminConfig):
    default_auto_field = "django_mongodb_backend.fields.ObjectIdAutoField"


class MongoAuthConfig(AuthConfig):
    default_auto_field = "django_mongodb_backend.fields.ObjectIdAutoField"

    def ready(self):
        # Disconnect the built-in create_permissions signal — it crashes with MongoDB
        # because ContentType instances don't get PKs assigned the same way as SQL
        from django.contrib.auth.management import create_permissions
        post_migrate.disconnect(create_permissions, sender=self)


class MongoContentTypesConfig(ContentTypesConfig):
    default_auto_field = "django_mongodb_backend.fields.ObjectIdAutoField"

# PyMongo

from pymongo import MongoClient
from django.conf import settings

def get_mongo_db():
    client = MongoClient(settings.MONGODB_URI)
    return client[settings.MONGODB_DB_NAME]

def get_collection(collection_name: str):
    db = get_mongo_db()
    return db[collection_name]

def get_knowledge_base_collection():
    col = get_collection("knowledge_base")
    col.create_index(
        [("legal_domain", ASCENDING), ("jurisdiction", ASCENDING)],
        unique=True
    )
    return col

def get_self_assessments_collection():
    col = get_collection("self_assessments")
    col.create_index(
        [("chat_id", ASCENDING)],
        unique=True
    )
    return col