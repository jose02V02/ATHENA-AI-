import io
import uuid
import httpx
from fastapi import APIRouter, UploadFile, File, HTTPException
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
from qdrant_client.http.exceptions import UnexpectedResponse
from app.core.config import settings
import pypdf

router = APIRouter()

# Initialize Qdrant client
# We use a try-except to avoid crashing the server if Qdrant is not running
try:
    qdrant_client = QdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT)
except Exception as e:
    print(f"Avviso: Impossibile connettersi a Qdrant ({e}). Il RAG non funzionerà.")
    qdrant_client = None

COLLECTION_NAME = "athena_knowledge"
EMBEDDING_DIM = 768  # nomic-embed-text has 768 dimensions

def init_qdrant_collection():
    if not qdrant_client:
        return
    try:
        qdrant_client.get_collection(COLLECTION_NAME)
    except (UnexpectedResponse, Exception):
        # Collection does not exist, create it
        try:
            qdrant_client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=qmodels.VectorParams(
                    size=EMBEDDING_DIM,
                    distance=qmodels.Distance.COSINE
                )
            )
            print(f"Collezione Qdrant '{COLLECTION_NAME}' creata con successo.")
        except Exception as e:
            print(f"Errore creazione collezione Qdrant: {e}")

async def get_embedding(text: str) -> list:
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                f"{settings.OLLAMA_URL}/api/embeddings",
                json={
                    "model": settings.EMBEDDING_MODEL,
                    "prompt": text
                }
            )
            if response.status_code == 200:
                return response.json().get("embedding")
            else:
                # Try pull the model if not found
                if "not found" in response.text.lower():
                    print(f"Modello embedding '{settings.EMBEDDING_MODEL}' non trovato. Tendo a scaricarlo...")
                    await client.post(f"{settings.OLLAMA_URL}/api/pull", json={"name": settings.EMBEDDING_MODEL})
                raise HTTPException(status_code=500, detail=f"Errore generazione embedding Ollama: {response.text}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Connessione fallita a Ollama Embeddings: {str(e)}")

def extract_text_from_pdf(file_bytes: bytes) -> str:
    pdf_file = io.BytesIO(file_bytes)
    try:
        reader = pypdf.PdfReader(pdf_file)
        text = ""
        for page in reader.pages:
            t = page.extract_text()
            if t:
                text += t + "\n"
        return text
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"File PDF non valido o corrotto: {str(e)}")

def chunk_text(text: str, chunk_size: int = 800, overlap: int = 150) -> list:
    chunks = []
    # simple character-based splitting
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end].strip())
        start += chunk_size - overlap
    # Filter empty chunks
    return [c for c in chunks if len(c) > 10]

@router.post("/knowledge/upload")
async def upload_document(file: UploadFile = File(...)):
    if not qdrant_client:
        raise HTTPException(status_code=503, detail="Database vettoriale Qdrant non configurato o non raggiungibile.")

    # 1. Initialize collection
    init_qdrant_collection()

    # 2. Read file content
    contents = await file.read()
    file_name = file.filename or "documento_sconosciuto"
    
    if file_name.endswith('.pdf'):
        text = extract_text_from_pdf(contents)
    else:
        # Fallback to plain text
        try:
            text = contents.decode('utf-8')
        except UnicodeDecodeError:
            raise HTTPException(status_code=400, detail="Il file deve essere un PDF o un file di testo leggibile (UTF-8).")

    if not text.strip():
        raise HTTPException(status_code=400, detail="Il documento caricato non contiene testo estraibile.")

    # 3. Create chunks
    chunks = chunk_text(text)
    if not chunks:
        raise HTTPException(status_code=400, detail="Impossibile suddividere il testo in chunk validi.")

    # 4. Generate embeddings and upload to Qdrant
    points = []
    for i, chunk in enumerate(chunks):
        embedding = await get_embedding(chunk)
        point_id = str(uuid.uuid4())
        points.append(
            qmodels.PointStruct(
                id=point_id,
                vector=embedding,
                payload={
                    "document_name": file_name,
                    "chunk_index": i,
                    "text": chunk
                }
            )
        )

    # Batch insert to Qdrant
    try:
        qdrant_client.upsert(
            collection_name=COLLECTION_NAME,
            points=points
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore di inserimento su Qdrant: {str(e)}")

    return {
        "status": "success",
        "document_name": file_name,
        "chunks_indexed": len(chunks)
    }

@router.get("/knowledge/documents")
async def get_documents():
    if not qdrant_client:
        return []
    
    init_qdrant_collection()
    
    try:
        # Scroll to list points
        res, _ = qdrant_client.scroll(
            collection_name=COLLECTION_NAME,
            limit=200,
            with_payload=True,
            with_vectors=False
        )
        docs = {}
        for point in res:
            doc_name = point.payload.get("document_name")
            if doc_name:
                docs[doc_name] = docs.get(doc_name, 0) + 1
        
        return [
            {"name": name, "chunks": count}
            for name, count in docs.items()
        ]
    except Exception as e:
        print(f"Errore recupero documenti Qdrant: {e}")
        return []

@router.delete("/knowledge/documents/{document_name}")
async def delete_document(document_name: str):
    if not qdrant_client:
        raise HTTPException(status_code=530, detail="Qdrant non raggiungibile.")

    try:
        qdrant_client.delete(
            collection_name=COLLECTION_NAME,
            points_selector=qmodels.Filter(
                must=[
                    qmodels.FieldCondition(
                        key="document_name",
                        match=qmodels.MatchValue(value=document_name)
                    )
                ]
            )
        )
        return {"status": "success", "message": f"Documento '{document_name}' eliminato da Qdrant."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore eliminazione da Qdrant: {str(e)}")
