import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.chat import router as chat_router
from app.api.knowledge import router as knowledge_router, init_qdrant_collection
from app.db.session import init_db

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description="Backend di controllo per l'assistente Athena AI locale."
)

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Per sviluppo, consente connessione da qualsiasi origine (Next.js)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(chat_router, prefix="/api")
app.include_router(knowledge_router, prefix="/api")

@app.on_event("startup")
def on_startup():
    print("Inizializzazione database...")
    init_db()
    print("Database inizializzato con successo!")
    print("Inizializzazione collezione Qdrant...")
    init_qdrant_collection()

@app.get("/")
def read_root():
    return {
        "status": "online",
        "project": settings.PROJECT_NAME,
        "version": settings.PROJECT_VERSION
    }

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
