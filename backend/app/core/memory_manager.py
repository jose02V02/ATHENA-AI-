import uuid
from qdrant_client import QdrantClient
from langchain_community.embeddings import HuggingFaceEmbeddings

class MemoryManager:
    def __init__(self):
        # Connessione al database locale Qdrant (crea la cartella qdrant_db)
        self.client = QdrantClient(path="./qdrant_db")
        self._embeddings = None  # Non caricare subito il modello

    @property
    def embeddings(self):
        # Carica il modello solo alla prima vera richiesta
        if self._embeddings is None:
            self._embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        return self._embeddings

    def add_memory(self, text: str, metadata: dict):
        vector = self.embeddings.embed_query(text)
        point_id = str(uuid.uuid4())
        self.client.upsert(
            collection_name="athena_memory",
            points=[{
                "id": point_id,
                "vector": vector,
                "payload": {"text": text, **metadata}
            }]
        )
        return point_id

    def search_memory(self, query: str, limit: int = 3):
        query_vector = self.embeddings.embed_query(query)
        results = self.client.search(
            collection_name="athena_memory",
            query_vector=query_vector,
            limit=limit
        )
        return [hit.payload for hit in results]

# Istanza lazy: creata solo alla prima chiamata di get_memory()
_memory_instance = None

def get_memory():
    global _memory_instance
    if _memory_instance is None:
        _memory_instance = MemoryManager()
    return _memory_instance