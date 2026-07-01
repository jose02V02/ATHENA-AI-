# Progetto Athena AI (v0.1)

Athena è un'intelligenza artificiale personale, autonoma e indipendente, eseguita interamente in locale.

Questa è la versione **v0.1** (Chat AI funzionante con inferenza locale).

---

## Prerequisiti

1. **Ollama**:
   - Scarica ed installa [Ollama](https://ollama.com/) per il tuo sistema operativo.
   - Avvia Ollama e scarica un modello a tua scelta (es. Qwen 2.5 o Llama 3) eseguendo nel terminale:
     ```bash
     ollama pull qwen2.5:7b
     ```
     o
     ```bash
     ollama pull llama3:8b
     ```
   - Assicurati che il servizio Ollama sia in esecuzione su `http://localhost:11434` prima di avviare il backend.

2. **Python**:
   - Assicurati di avere installato Python 3.8+ sul tuo sistema.

3. **Node.js**:
   - Assicurati di avere installato Node.js (v18+) per eseguire il frontend.

4. **Docker & Docker Desktop** (Opzionale per v0.1):
   - Per avviare PostgreSQL e Qdrant (predisposti per le prossime fasi), puoi eseguire:
     ```bash
     docker-compose -f docker/docker-compose.yml up -d
     ```

---

## Avvio del Progetto

Il progetto è suddiviso in due componenti principali: `backend/` e `frontend/`.

### 1. Avviare il Backend (FastAPI)

1. Apri un terminale nella cartella `backend/`.
2. Crea un ambiente virtuale (consigliato):
   ```bash
   python -m venv venv
   # Su Windows:
   venv\Scripts\activate
   # Su Mac/Linux:
   source venv/bin/activate
   ```
3. Installa le dipendenze:
   ```bash
   pip install -r requirements.txt
   ```
4. Avvia il server:
   ```bash
   python app/main.py
   ```
   Il server sarà attivo su `http://localhost:8000`.

### 2. Avviare il Frontend (Next.js)

1. Apri un altro terminale nella cartella `frontend/`.
2. Installa le dipendenze:
   ```bash
   npm install
   ```
3. Avvia lo strumento di sviluppo:
   ```bash
   npm run dev
   ```
   L'applicazione sarà accessibile all'indirizzo `http://localhost:3000`.

---

## Struttura del Codice

- **`backend/`**: Implementazione del server FastAPI in Python.
  - **`app/core/personalities.py`**: Configurazione delle personalità (Tutor di Diritto, Programmatore Senior, ecc.).
  - **`app/db/`**: Schema SQLAlchemy per salvare le conversazioni locali in SQLite (`athena.db`).
  - **`app/api/chat.py`**: Gestione dell'integrazione di streaming con l'API `/api/chat` di Ollama.
- **`frontend/`**: Interfaccia utente premium in Next.js + React.
  - **`src/app/page.tsx`**: Logica di gestione della chat e connessione SSE.
  - **`src/app/globals.css`**: Design di alta gamma (tema scuro, micro-animazioni).
