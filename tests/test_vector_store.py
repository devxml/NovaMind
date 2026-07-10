import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from qdrant_client import models

from app.services.vector_store import MultiTenantVectorStore


class DummyCollectionInfo:
    def __init__(self, payload_schema=None):
        self.payload_schema = payload_schema or {}


class DummyClient:
    def __init__(self, payload_schema=None):
        self.payload_schema = payload_schema or {}
        self.created_indexes = []
        self.created_collections = []

    def get_collections(self):
        return SimpleNamespace(collections=[])

    def create_collection(self, **kwargs):
        self.created_collections.append(kwargs)

    def get_collection(self, collection_name):
        return DummyCollectionInfo(payload_schema=self.payload_schema)

    def create_payload_index(self, collection_name, field_name, field_schema=None, **kwargs):
        self.created_indexes.append((collection_name, field_name, field_schema))


class VectorStorePayloadIndexTests(unittest.TestCase):
    def test_ensure_payload_indexes_creates_only_missing_fields(self):
        client = DummyClient(payload_schema={"metadata.tenant_id": {"type": "keyword"}})
        store = MultiTenantVectorStore.__new__(MultiTenantVectorStore)
        store.client = client
        store.collection_name = "test_collection"
        store.embedding_size = 768
        store.embedding = Mock()

        store._ensure_payload_indexes()

        self.assertEqual(
            client.created_indexes,
            [
                ("test_collection", "metadata.user_id", models.PayloadSchemaType.KEYWORD),
                ("test_collection", "metadata.chat_id", models.PayloadSchemaType.KEYWORD),
            ],
        )


if __name__ == "__main__":
    unittest.main()
