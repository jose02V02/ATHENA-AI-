import json
import uuid
import httpx
import asyncio
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

router = APIRouter()

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

    # 2. Get active model
    model_to_use = chat_input.model or settings.DEFAULT_MODEL

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

    # Build messages payload for Ollama
    system_prompt = get_system_prompt(conversation.personality)
    formatted_messages = [{"role": "system", "content": system_prompt}]
    
    # Format history (excluding current user message to append it with context)
    for msg in history[:-1]:
        m_dict = {"role": msg.role, "content": msg.content}
        if msg.images:
            try:
                m_dict["images"] = json.loads(msg.images)
            except:
                pass
        formatted_messages.append(m_dict)

    # Append current message with RAG context if found
    current_content = user_msg_content
    if rag_context:
        current_content = (
            f"Usa le seguenti fonti estratte dai documenti per rispondere alla domanda dell'utente.\n"
            f"Cita sempre il nome del file della fonte ([NomeFile.pdf]) se utilizzi le sue informazioni.\n"
            f"Se le informazioni nel contesto non sono sufficienti per rispondere, rispondi al meglio delle tue conoscenze ma menziona che i documenti non contengono la risposta.\n\n"
            f"CONTESTO DOCUMENTALE:\n{rag_context}\n\n"
            f"DOMANDA DELL'UTENTE: {user_msg_content}"
        )
    
    current_msg_dict = {"role": "user", "content": current_content}
    if chat_input.images:
        current_msg_dict["images"] = chat_input.images
        
    formatted_messages.append(current_msg_dict)

    # 5. SSE generator with Agent loop
    async def event_generator():
        accumulated_content = ""
        loop_count = 0
        max_loops = 3
        
        try:
            async with httpx.AsyncClient(timeout=90.0) as client:
                while loop_count < max_loops:
                    # Request to Ollama
                    payload = {
                        "model": model_to_use,
                        "messages": formatted_messages,
                        "stream": False  # Non-streaming to easily handle tool calls in Python
                    }
                    
                    # Add tools only if no images are present (multimodal models in Ollama often don't support tools simultaneously)
                    if not chat_input.images:
                        payload["tools"] = TOOLS_DEFINITION

                    response = await client.post(
                        f"{settings.OLLAMA_URL}/api/chat",
                        json=payload
                    )
                    
                    if response.status_code != 200:
                        yield f"data: {json.dumps({'error': f'Ollama ha restituito errore {response.status_code}: {response.text}'})}\n\n"
                        return
                    
                    res_data = response.json()
                    msg_res = res_data.get("message", {})
                    tool_calls = msg_res.get("tool_calls", [])
                    
                    if tool_calls:
                        # Append the assistant's tool-call response to formatted_messages
                        formatted_messages.append(msg_res)
                        
                        for tool_call in tool_calls:
                            func = tool_call.get("function", {})
                            t_name = func.get("name")
                            t_args = func.get("arguments", {})
                            
                            # SSE Event: Tool Call Started
                            yield f"data: {json.dumps({'tool': t_name, 'args': t_args})}\n\n"
                            
                            # Execute the tool
                            loop = asyncio.get_event_loop()
                            tool_result = await loop.run_in_executor(None, execute_tool, t_name, t_args)
                            
                            # SSE Event: Tool Result
                            yield f"data: {json.dumps({'tool_result': tool_result})}\n\n"
                            
                            # Append tool response
                            formatted_messages.append({
                                "role": "tool",
                                "content": tool_result
                            })
                        
                        loop_count += 1
                    else:
                        # No tool calls, this is our final text!
                        final_content = msg_res.get("content", "")
                        accumulated_content = final_content
                        
                        # Stream the final content to the frontend to simulate streaming response
                        chunk_size = 12
                        for i in range(0, len(final_content), chunk_size):
                            chunk = final_content[i:i+chunk_size]
                            yield f"data: {json.dumps({'content': chunk})}\n\n"
                            await asyncio.sleep(0.01)  # Smooth streaming animation delay
                        break
                
                # Save assistant response to DB
                if accumulated_content.strip():
                    save_message_sync(conversation_id, "assistant", accumulated_content)
                yield f"data: {json.dumps({'status': 'done'})}\n\n"
                
        except Exception as e:
            yield f"data: {json.dumps({'error': f'Errore di connessione o esecuzione: {str(e)}'})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
