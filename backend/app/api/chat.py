import json
import uuid
import httpx
import asyncio
import os
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.db.session import get_db, SessionLocal
from app.db.models import Conversation, Message
from app.core.config import settings
from app.core.personalities import PERSONALITIES, get_system_prompt
from app.core.tools import TOOLS_DEFINITION, execute_tool
from pydantic import BaseModel
from typing import List, Optional

# Importiamo l'SDK ufficiale di Groq
from groq import Groq

router = APIRouter()

# Inizializziamo il client Groq leggendo la chiave dalle variabili d'ambiente di Render
# Se non trova la chiave, userà una stringa vuota temporanea per evitare crash all'avvio
groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY", ""))

# Pydantic Schemas
class ConversationCreate(BaseModel):
    title: Optional[str] = "Nuova Conversazione"
    personality: Optional[str] = "athena"

class ChatInput(BaseModel):
    message: str
    model: Optional[str] = None
    images: Optional[List[str]] = None  # Base64 string list for multimodal vision

# Helper to save messages out-of-band in SSE generator
def save_message_sync(conversation_id: str, role: str, content: str):
    db = SessionLocal()
    try:
        new_msg = Message(
            id=str(uuid.uuid4()),
            conversation_id=conversation_id,
            role=role,
            content=content
        )
        db.add(new_msg)
        db.commit()
    except Exception as e:
        print(f"Errore durante il salvataggio del messaggio: {e}")
    finally:
        db.close()

# Routes
@router.get("/personalities")
def list_personalities():
    return [
        {"id": key, "name": val["name"], "description": val["description"]}
        for key, val in PERSONALITIES.items()
    ]

@router.post("/conversations")
def create_conversation(data: ConversationCreate, db: Session = Depends(get_db)):
    conv_id = str(uuid.uuid4())
    db_conv = Conversation(
        id=conv_id,
        title=data.title,
        personality=data.personality
    )
    db.add(db_conv)
    db.commit()
    db.refresh(db_conv)
    return db_conv

@router.get("/conversations")
def list_conversations(db: Session = Depends(get_db)):
    return db.query(Conversation).order_by(Conversation.created_at.desc()).all()

@router.get("/conversations/{conversation_id}/messages")
def get_messages(conversation_id: str, db: Session = Depends(get_db)):
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversazione non trovata")
    
    messages = db.query(Message).filter(Message.conversation_id == conversation_id).order_by(Message.created_at.asc()).all()
    
    # Format to return images list if present
    formatted_messages = []
    for msg in messages:
        imgs = None
        if msg.images:
            try:
                imgs = json.loads(msg.images)
            except:
                pass
        formatted_messages.append({
            "id": msg.id,
            "role": msg.role,
            "content": msg.content,
            "images": imgs,
            "created_at": msg.created_at.isoformat() if msg.created_at else None
        })
    return formatted_messages

@router.delete("/conversations/{conversation_id}")
def delete_conversation(conversation_id: str, db: Session = Depends(get_db)):
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversazione non trovata")
    db.delete(conversation)
    db.commit()
    return {"status": "success", "message": "Conversazione eliminata"}

@router.post("/conversations/{conversation_id}/stream")
async def stream_chat(
    conversation_id: str,
    chat_input: ChatInput,
    db: Session = Depends(get_db)
):
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversazione non trovata")

    user_msg_content = chat_input.message.strip()
    if not user_msg_content and not chat_input.images:
        raise HTTPException(status_code=400, detail="Il messaggio o le immagini non possono essere vuoti")

    # 1. Save user message to database
    images_json = json.dumps(chat_input.images) if chat_input.images else None
    user_msg = Message(
        id=str(uuid.uuid4()),
        conversation_id=conversation_id,
        role="user",
        content=user_msg_content,
        images=images_json
    )
    db.add(user_msg)
    
    # Auto-rename conversation
    if conversation.title == "Nuova Conversazione" or conversation.title.startswith("Athena ("):
        display_title = user_msg_content[:30] + ("..." if len(user_msg_content) > 30 else "")
        if not display_title and chat_input.images:
            display_title = "Immagine inviata"
        conversation.title = display_title
        db.add(conversation)

    db.commit()

    # 2. Forziamo il modello cloud gratuito di Groq anziché Ollama locale
    model_to_use = "llama-3.1-8b-instant"

    # 3. Retrieve historical messages for context
    history = db.query(Message).filter(Message.conversation_id == conversation_id).order_by(Message.created_at.asc()).all()
    
    # 4. Construct system prompt and run RAG if Qdrant is connected
    rag_context = ""
    from app.api.knowledge import qdrant_client, COLLECTION_NAME, get_embedding
    if qdrant_client and user_msg_content:
        try:
            collections = qdrant_client.get_collections().collections
            if any(c.name == COLLECTION_NAME for c in collections):
                query_vector = await get_embedding(user_msg_content)
                search_res = qdrant_client.search(
                    collection_name=COLLECTION_NAME,
                    query_vector=query_vector,
                    limit=3
                )
                context_parts = []
                for res in search_res:
                    if res.score > 0.45:  # Similarity threshold
                        text = res.payload.get("text", "")
                        doc = res.payload.get("document_name", "Documento")
                        context_parts.append(f"--- FONTE: {doc} (Similitudine: {res.score:.2f}) ---\n{text}\n")
                if context_parts:
                    rag_context = "\n".join(context_parts)
        except Exception as e:
            print(f"Errore RAG Qdrant: {e}")

    # Build messages payload for Groq
    system_prompt = get_system_prompt(conversation.personality)
    formatted_messages = [{"role": "system", "content": system_prompt}]
    
    # Format history
    for msg in history[:-1]:
        m_dict = {"role": msg.role, "content": msg.content}
        formatted_messages.append(m_dict)

    # Append current message with RAG context if found
    current_content = user_msg_content
    if rag_context:
        current_content = (
            f"Usa le seguenti fonti estratte dai documenti per rispondere alla domanda dell'utente.\n"
            f"Cita sempre il nome del file della fonte ([NomeFile.pdf]) se utilizzi le sei informazioni.\n"
            f"Se le informazioni nel contesto non sono sufficienti per rispondere, rispondi al meglio delle tue conoscenze ma menziona che i documenti non contengono la risposta.\n\n"
            f"CONTESTO DOCUMENTALE:\n{rag_context}\n\n"
            f"DOMANDA DELL'UTENTE: {user_msg_content}"
        )
    
    current_msg_dict = {"role": "user", "content": current_content}
    formatted_messages.append(current_msg_dict)

    # 5. SSE generator con chiamata Cloud a Groq
    async def event_generator():
        accumulated_content = ""
        loop_count = 0
        max_loops = 3
        
        try:
            # Eseguiamo la chiamata a Groq in modo asincrono per non bloccare FastAPI
            loop = asyncio.get_event_loop()
            
            while loop_count < max_loops:
                # Setup dei parametri per l'API di Groq
                kwargs = {
                    "model": model_to_use,
                    "messages": formatted_messages,
                }
                
                # Se non ci sono immagini, convertiamo le definizioni dei tuoi strumenti per Groq
                if not chat_input.images and TOOLS_DEFINITION:
                    groq_tools = []
                    for t in TOOLS_DEFINITION:
                        if "function" in t:
                            groq_tools.append({
                                "type": "function",
                                "function": t["function"]
                            })
                    if groq_tools:
                        kwargs["tools"] = groq_tools

                # Chiamata a Groq eseguita nell'executor per renderla non-blocking
                response = await loop.run_in_executor(
                    None, 
                    lambda: groq_client.chat.completions.create(**kwargs)
                )
                
                msg_res = response.choices[0].message
                tool_calls = getattr(msg_res, "tool_calls", None)
                
                if tool_calls:
                    # Registriamo la risposta con la richiesta del tool
                    formatted_messages.append({
                        "role": "assistant",
                        "content": msg_res.content or "",
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": "function",
                                "function": {
                                    "name": tc.function.name,
                                    "arguments": tc.function.arguments
                                }
                            } for tc in tool_calls
                        ]
                    })
                    
                    for tool_call in tool_calls:
                        t_name = tool_call.function.name
                        # Risoluzione argomenti stringificati
                        try:
                            t_args = json.loads(tool_call.function.arguments)
                        except:
                            t_args = tool_call.function.arguments
                        
                        # SSE Event: Tool Call Started
                        yield f"data: {json.dumps({'tool': t_name, 'args': t_args})}\n\n"
                        
                        # Esecuzione del tool sincrono
                        tool_result = await loop.run_in_executor(None, execute_tool, t_name, t_args)
                        
                        # SSE Event: Tool Result
                        yield f"data: {json.dumps({'tool_result': tool_result})}\n\n"
                        
                        # Append tool response richiesto dalle specifiche Groq/OpenAI
                        formatted_messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": t_name,
                            "content": str(tool_result)
                        })
                    
                    loop_count += 1
                else:
                    # Nessun tool, testo finale!
                    final_content = msg_res.content or ""
                    accumulated_content = final_content
                    
                    # Genera l'effetto streaming sul client
                    chunk_size = 12
                    for i in range(0, len(final_content), chunk_size):
                        chunk = final_content[i:i+chunk_size]
                        yield f"data: {json.dumps({'content': chunk})}\n\n"
                        await asyncio.sleep(0.01)
                    break
            
            # Salva la risposta dell'assistente nel DB
            if accumulated_content.strip():
                save_message_sync(conversation_id, "assistant", accumulated_content)
            yield f"data: {json.dumps({'status': 'done'})}\n\n"
                
        except Exception as e:
            yield f"data: {json.dumps({'error': f'Errore Cloud Groq o esecuzione: {str(e)}'})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
