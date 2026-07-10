from typing import List, Dict, Any, Optional

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from qdrant_client import QdrantClient, models
from langchain_qdrant import QdrantVectorStore

FILTERED_PAYLOAD_FIELDS = [
    "metadata.tenant_id",
    "metadata.user_id",
    "metadata.chat_id",
]

from app.core.config import settings
from app.utils.logger import setup_logger
from app.utils.qdrant import format_chat_results

logger = setup_logger(__name__)


class MultiTenantVectorStore:
    """A multi-tenant vector store using Qdrant for efficient semantic search with tenant isolation.
    
    This class implements the approach from the tutorial on building multi-tenant chatbots
    with Qdrant. It uses payload partitioning with tenant_id for data isolation.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MultiTenantVectorStore, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(
        self,
        collection_name: str = "multi_tenant_chat_history",
        embedding: Optional[Embeddings] = GoogleGenerativeAIEmbeddings(
            model="models/gemini-embedding-001",
            google_api_key=settings.GOOGLE_API_KEY,
            output_dimensionality=768
        ),
    ):
        """Initialize the multi-tenant vector store.
        
        Args:
            collection_name: Name of the Qdrant collection to use
            embedding: LangChain embedding model to use (default to Gemini embeddings)
        """
        if self._initialized:
            return
        self.client = QdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY,
        )
        self.collection_name = collection_name
        self.embedding_size = 768
        self.embedding = embedding

        self._ensure_collection_exists()
        self._initialized = True

    def _ensure_collection_exists(self) -> None:
        """Create the collection if it doesn't exist and ensure payload indexes exist."""
        collections = self.client.get_collections().collections
        collection_names = [collection.name for collection in collections]

        if self.collection_name not in collection_names:
            logger.info(f"Creating new collection: {self.collection_name}")
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(
                    size=self.embedding_size,
                    distance=models.Distance.COSINE
                )
            )
        else:
            logger.info(f"Collection {self.collection_name} already exists")

        self._ensure_payload_indexes()

    def _ensure_payload_indexes(self) -> None:
        """Create required payload indexes for every filtered field, idempotently."""
        try:
            collection_info = self.client.get_collection(self.collection_name)
        except Exception as exc:
            logger.error(f"Unable to read Qdrant collection info for {self.collection_name}: {exc}")
            raise

        payload_schema = getattr(collection_info, "payload_schema", {}) or {}
        existing_fields = set(payload_schema.keys())

        for field_name in FILTERED_PAYLOAD_FIELDS:
            if field_name in existing_fields:
                logger.info(f"Payload index exists: {field_name}")
                continue

            try:
                logger.info(f"Creating payload index: {field_name}")
                self.client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name=field_name,
                    field_schema=models.PayloadSchemaType.KEYWORD,
                )
                logger.info(f"Payload index created: {field_name}")
            except Exception as exc:
                if "already exists" in str(exc).lower() or "already indexed" in str(exc).lower():
                    logger.info(f"Payload index already exists: {field_name}")
                    continue
                logger.error(f"Failed to create payload index {field_name}: {exc}")
                raise

            try:
                refreshed_collection_info = self.client.get_collection(self.collection_name)
                refreshed_payload_schema = getattr(refreshed_collection_info, "payload_schema", {}) or {}
                existing_fields = set(refreshed_payload_schema.keys())
            except Exception as refresh_exc:
                logger.warning(f"Unable to refresh payload schema after creating {field_name}: {refresh_exc}")

        logger.info("✓ Connected to Qdrant Cloud")
        logger.info(f"✓ Collection exists: {self.collection_name}")
        for field_name in FILTERED_PAYLOAD_FIELDS:
            if field_name in existing_fields:
                logger.info(f"✓ Payload index exists: {field_name}")
            else:
                logger.info(f"✓ Payload index verified: {field_name}")
    
    def store_conversation(
        self, 
        question: str, 
        answer: str, 
        tenant_id: str, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """Store a conversation in the vector store with tenant isolation"""
        doc = Document(
            page_content=f"User: {question}\nAssistant: {answer}",
            metadata=metadata or {}
        )

        doc.metadata["tenant_id"] = tenant_id

        vector_store = QdrantVectorStore(
            client=self.client,
            collection_name=self.collection_name,
            embedding=self.embedding
        )

        return vector_store.add_documents([doc])
        
    def get_chats_by_user_id(
        self,
        user_id: str,
        tenant_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get all chat messages for a specific user, with pagination"""
        response = self.client.scroll(
            collection_name=self.collection_name,
            scroll_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="metadata.tenant_id",
                        match=models.MatchValue(value=tenant_id)
                    ),
                    models.FieldCondition(
                        key="metadata.user_id",
                        match=models.MatchValue(value=str(user_id))
                    )
            ]),
            limit=limit,
            offset=offset,
            with_payload=True,
            with_vectors=False
        )

        results = format_chat_results(response[0])
        results.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return results
        
    def get_chat_by_id(
        self,
        chat_id: str,
        tenant_id: str,
        user_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get all messages for a specific chat ID belonging to a user"""
        response = self.client.scroll(
            collection_name=self.collection_name,
            scroll_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="metadata.tenant_id",
                        match=models.MatchValue(value=tenant_id)
                    ),
                    models.FieldCondition(
                        key="metadata.user_id",
                        match=models.MatchValue(value=str(user_id))
                    ),
                    models.FieldCondition(
                        key="metadata.chat_id",
                        match=models.MatchValue(value=chat_id)
                    )
            ]),
            limit=limit,
            offset=offset,
            with_payload=True,
            with_vectors=False
        )

        results = format_chat_results(response[0])
        results.sort(key=lambda x: x.get("timestamp", ""))
        return results
