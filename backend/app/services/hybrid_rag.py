# backend/app/services/hybrid_rag.py
import re
from typing import List, Dict, Optional
from rank_bm25 import BM25Okapi

class HybridRAGService:
    def __init__(self):
        self.bm25_corpus: List[Dict] = []
        self.bm25_index: Optional[BM25Okapi] = None
    
    def tokenize(self, text: str) -> List[str]:
        text = re.sub(r'[^\w\sàèéìòù]', ' ', text.lower())
        return [t for t in text.split() if len(t) > 2]
    
    def add_document(self, doc_id: str, text: str, metadata: dict = None):
        tokens = self.tokenize(text)
        self.bm25_corpus.append({
            "id": doc_id, 
            "text": text, 
            "tokens": tokens,
            "metadata": metadata or {}
        })
        self._rebuild_index()
    
    def remove_document(self, doc_id: str):
        self.bm25_corpus = [d for d in self.bm25_corpus if d["id"] != doc_id]
        self._rebuild_index()
    
    def _rebuild_index(self):
        if not self.bm25_corpus:
            self.bm25_index = None
            return
        self.bm25_index = BM25Okapi([doc["tokens"] for doc in self.bm25_corpus])
    
    def bm25_search(self, query: str, limit: int = 10) -> List[Dict]:
        if not self.bm25_index:
            return []
        query_tokens = self.tokenize(query)
        scores = self.bm25_index.get_scores(query_tokens)
        scored = [(i, s) for i, s in enumerate(scores) if s > 0]
        scored.sort(key=lambda x: x[1], reverse=True)
        return [{
            "id": self.bm25_corpus[i]["id"],
            "text": self.bm25_corpus[i]["text"],
            "score": float(s),
            "metadata": self.bm25_corpus[i]["metadata"]
        } for i, s in scored[:limit]]
    
    async def hybrid_search(self, query, qdrant_client, collection_name, 
                           limit=5, semantic_weight=0.7) -> List[Dict]:
        if not qdrant_client:
            return []
        
        from app.api.knowledge import get_embedding
        
        query_vector = await get_embedding(query)
        semantic_hits = qdrant_client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=limit * 3
        )
        
        keyword_hits = self.bm25_search(query, limit=limit * 3)
        
        k = 60
        fused = {}
        doc_texts = {}
        
        for rank, hit in enumerate(semantic_hits):
            doc_id = str(hit.id)
            fused[doc_id] = fused.get(doc_id, 0) + semantic_weight / (rank + k)
            doc_texts[doc_id] = hit.payload.get("text", "")
        
        for rank, hit in enumerate(keyword_hits):
            doc_id = hit["id"]
            fused[doc_id] = fused.get(doc_id, 0) + (1 - semantic_weight) / (rank + k)
            if doc_id not in doc_texts:
                doc_texts[doc_id] = hit["text"]
        
        sorted_results = sorted(fused.items(), key=lambda x: x[1], reverse=True)[:limit]
        
        return [{
            "id": doc_id,
            "text": doc_texts[doc_id][:1000],
            "score": float(score),
            "metadata": {}
        } for doc_id, score in sorted_results]

hybrid_rag = HybridRAGService()
