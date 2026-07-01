import chromadb
from chromadb.config import Settings as ChromaSettings
from app.core.config import settings
import ollama
from typing import List, Tuple

class RAGService:
    def __init__(self):
        self.client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)
        self.collection = self.client.get_or_create_collection(
            name="athena_docs",
            metadata={"hnsw:space": "cosine"}
        )
    
    def embed_text(self, text: str) -> List[float]:
        """Genera embedding usando Ollama"""
        response = ollama.embeddings(
            model=settings.EMBEDDING_MODEL,
            prompt=text
        )
        return response["embedding"]
    
    def add_document(self, doc_id: str, text: str, metadata: dict = None):
        """Aggiunge documento al vector DB"""
        chunks = self._split_text(text)
        embeddings = [self.embed_text(chunk) for chunk in chunks]
        
        self.collection.add(
            documents=chunks,
            embeddings=embeddings,
            ids=[f"{doc_id}_{i}" for i in range(len(chunks))],
            metadatas=[metadata or {}] * len(chunks)
        )
    
    def search(self, query: str, n_results: int = None) -> List[str]:
        """Cerca chunks rilevanti"""
        n = n_results or settings.MAX_CONTEXT_CHUNKS
        query_embedding = self.embed_text(query)
        
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n
        )
        return results["documents"][0] if results["documents"] else []
    
    def _split_text(self, text: str) -> List[str]:
        """Split intelligente con overlap"""
        chunks = []
        start = 0
        while start < len(text):
            end = start + settings.CHUNK_SIZE
            chunk = text[start:end]
            chunks.append(chunk)
            start += settings.CHUNK_SIZE - settings.CHUNK_OVERLAP
        return chunks

rag = RAGService()
