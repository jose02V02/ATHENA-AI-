import uuid
from qdrant_client import QdrantClient
from langchain_community.embeddings import HuggingFaceEmbeddings

class MemoryManager:
    def __init__(self):
        # Connessione al database locale Qdrant (crea la cartella qdrant_db)
        self.client = QdrantClient(path="./qdrant_db")
        
        # Carica il modello di embedding leggero (gira in locale, niente chiamate API)
        # Questo trasforma i tuoi testi in vettori numerici
        self.embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

    def add_memory(self, text: str, metadata: dict):
        """Vettorizza il testo e lo salva nel database locale."""
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
        """Cerca i ricordi più pertinenti."""
        query_vector = self.embeddings.embed_query(query)
        
        results = self.client.search(
            collection_name="athena_memory",
            query_vector=query_vector,
            limit=limit
        )
        return [hit.payload for hit in results]

# Istanza globale
memory = MemoryManager()