"use client";

import React, { useState, useEffect, useRef } from 'react';
import { 
  Bot, 
  Send, 
  Plus, 
  Trash2, 
  MessageSquare, 
  Sparkles, 
  Brain, 
  Terminal, 
  BookOpen, 
  Scale, 
  Settings, 
  Upload, 
  FileText, 
  Image as ImageIcon, 
  Mic, 
  MicOff, 
  Volume2, 
  VolumeX, 
  X, 
  ChevronDown, 
  ChevronUp, 
  Play,
  FileCheck
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface Conversation {
  id: string;
  title: string;
  personality: string;
  created_at: string;
}

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  images?: string[] | null;
  created_at?: string;
}

interface Personality {
  id: string;
  name: string;
  description: string;
}

interface DocumentInfo {
  name: string;
  chunks: number;
}

interface ToolExecution {
  name: string;
  args: any;
  result?: string;
  collapsed?: boolean;
}

const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const COMMON_MODELS = [
  { id: "qwen2.5:7b", name: "Qwen 2.5 (7B) - Consigliato" },
  { id: "llama3:8b", name: "Llama 3 (8B)" },
  { id: "llava:7b", name: "LLaVA (7B) - Per Immagini" },
  { id: "mistral:latest", name: "Mistral" }
];

export default function Home() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [personalities, setPersonalities] = useState<Personality[]>([]);
  const [selectedPersonality, setSelectedPersonality] = useState("athena");
  const [selectedModel, setSelectedModel] = useState("qwen2.5:7b");
  
  // Knowledge Base RAG State
  const [documents, setDocuments] = useState<DocumentInfo[]>([]);
  const [uploadingDoc, setUploadingDoc] = useState(false);
  
  // Multimodal State
  const [attachedImage, setAttachedImage] = useState<string | null>(null);
  const [isListening, setIsListening] = useState(false);
  const [speakingMessageId, setSpeakingMessageId] = useState<string | null>(null);
  
  // Agent Tools execution State
  const [toolExecutions, setToolExecutions] = useState<ToolExecution[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamedContent, setStreamedContent] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const imageInputRef = useRef<HTMLInputElement>(null);
  const recognitionRef = useRef<any>(null);

  // Load initial data
  useEffect(() => {
    fetchPersonalities();
    fetchConversations();
    fetchDocuments();
  }, []);

  // Scroll to bottom on new messages or during streaming
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamedContent, toolExecutions]);

  // Handle textarea autosize
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 160)}px`;
    }
  }, [input]);

  const fetchPersonalities = async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/personalities`);
      if (res.ok) {
        const data = await res.json();
        setPersonalities(data);
      }
    } catch (err) {
      console.error("Errore caricamento personalità:", err);
    }
  };

  const fetchConversations = async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/conversations`);
      if (res.ok) {
        const data = await res.json();
        setConversations(data);
      }
    } catch (err) {
      console.error("Errore caricamento conversazioni:", err);
    }
  };

  const fetchDocuments = async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/knowledge/documents`);
      if (res.ok) {
        const data = await res.json();
        setDocuments(data);
      }
    } catch (err) {
      console.error("Errore caricamento documenti:", err);
    }
  };

  const fetchMessages = async (convId: string) => {
    setIsLoading(true);
    setToolExecutions([]);
    try {
      const res = await fetch(`${BACKEND_URL}/api/conversations/${convId}/messages`);
      if (res.ok) {
        const data = await res.json();
        setMessages(data);
        setActiveConversationId(convId);
      }
    } catch (err) {
      console.error("Errore caricamento messaggi:", err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreateConversation = async (personalityKey = selectedPersonality) => {
    try {
      const activePersObj = personalities.find(p => p.id === personalityKey);
      const title = activePersObj ? `Athena (${activePersObj.name})` : "Nuova Conversazione";
      
      const res = await fetch(`${BACKEND_URL}/api/conversations`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: title,
          personality: personalityKey
        })
      });
      if (res.ok) {
        const newConv = await res.json();
        setConversations(prev => [newConv, ...prev]);
        setActiveConversationId(newConv.id);
        setMessages([]);
        setStreamedContent("");
        setToolExecutions([]);
        return newConv.id;
      }
    } catch (err) {
      console.error("Errore creazione conversazione:", err);
    }
    return null;
  };

  const handleDeleteConversation = async (e: React.MouseEvent, convId: string) => {
    e.stopPropagation();
    if (!confirm("Sei sicuro di voler eliminare questa conversazione?")) return;

    try {
      const res = await fetch(`${BACKEND_URL}/api/conversations/${convId}`, {
        method: 'DELETE'
      });
      if (res.ok) {
        setConversations(prev => prev.filter(c => c.id !== convId));
        if (activeConversationId === convId) {
          setActiveConversationId(null);
          setMessages([]);
          setStreamedContent("");
          setToolExecutions([]);
        }
      }
    } catch (err) {
      console.error("Errore eliminazione conversazione:", err);
    }
  };

  // Upload Document (RAG)
  const handleUploadDocument = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploadingDoc(true);
    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch(`${BACKEND_URL}/api/knowledge/upload`, {
        method: 'POST',
        body: formData
      });
      if (res.ok) {
        alert(`Documento "${file.name}" indicizzato con successo!`);
        fetchDocuments();
      } else {
        const err = await res.json();
        alert(`Errore di caricamento: ${err.detail || 'Errore sconosciuto'}`);
      }
    } catch (err) {
      console.error("Errore caricamento documento:", err);
      alert("Connessione fallita con il server di indicizzazione.");
    } finally {
      setUploadingDoc(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handleDeleteDocument = async (docName: string) => {
    if (!confirm(`Vuoi rimuovere il documento "${docName}" dalla knowledge base?`)) return;

    try {
      const res = await fetch(`${BACKEND_URL}/api/knowledge/documents/${encodeURIComponent(docName)}`, {
        method: 'DELETE'
      });
      if (res.ok) {
        setDocuments(prev => prev.filter(d => d.name !== docName));
      }
    } catch (err) {
      console.error("Errore eliminazione documento:", err);
    }
  };

  // Attach Image (Multimodal)
  const handleAttachImage = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Validate size and type
    if (!file.type.startsWith('image/')) {
      alert("Seleziona un file immagine valido.");
      return;
    }

    const reader = new FileReader();
    reader.onloadend = () => {
      setAttachedImage(reader.result as string);
    };
    reader.readAsDataURL(file);
  };

  // Audio - Text-to-Speech (Sintesi Vocale)
  const handleSpeakMessage = (msgId: string, text: string) => {
    if (!('speechSynthesis' in window)) {
      alert("Sintesi vocale non supportata in questo browser.");
      return;
    }

    if (speakingMessageId === msgId) {
      window.speechSynthesis.cancel();
      setSpeakingMessageId(null);
      return;
    }

    window.speechSynthesis.cancel();
    setSpeakingMessageId(msgId);

    // Clean markdown characters from text for a clean dictation
    const cleanText = text
      .replace(/```[\s\S]*?```/g, '[Codice omesso]')
      .replace(/`([^`]+)`/g, '$1')
      .replace(/[*#_\-]/g, '')
      .trim();

    const utterance = new SpeechSynthesisUtterance(cleanText);
    utterance.lang = 'it-IT';
    
    // Attempt to load standard Italian voice
    const voices = window.speechSynthesis.getVoices();
    const itVoice = voices.find(v => v.lang.startsWith('it'));
    if (itVoice) {
      utterance.voice = itVoice;
    }

    utterance.onend = () => {
      setSpeakingMessageId(null);
    };

    utterance.onerror = () => {
      setSpeakingMessageId(null);
    };

    window.speechSynthesis.speak(utterance);
  };

  // Audio - Speech-to-Text (Dettatura Vocale)
  const handleToggleListen = () => {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert("Il riconoscimento vocale non è supportato in questo browser.");
      return;
    }

    if (isListening) {
      recognitionRef.current?.stop();
      setIsListening(false);
      return;
    }

    const recognition = new SpeechRecognition();
    recognitionRef.current = recognition;
    recognition.lang = 'it-IT';
    recognition.continuous = false;
    recognition.interimResults = false;

    recognition.onstart = () => {
      setIsListening(true);
    };

    recognition.onerror = (event: any) => {
      console.error("Errore riconoscimento vocale:", event.error);
      setIsListening(false);
    };

    recognition.onend = () => {
      setIsListening(false);
    };

    recognition.onresult = (event: any) => {
      const transcript = event.results[0][0].transcript;
      setInput(prev => prev + (prev ? " " : "") + transcript);
    };

    recognition.start();
  };

  // Send Message
  const handleSendMessage = async (textToSend?: string) => {
    const messageText = textToSend || input;
    if (!messageText.trim() && !attachedImage) return;
    if (isStreaming) return;

    let convId = activeConversationId;
    setInput("");
    const imgToSend = attachedImage;
    setAttachedImage(null);

    if (!convId) {
      const newId = await handleCreateConversation();
      if (!newId) return;
      convId = newId;
    }

    // Add user message locally
    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: messageText,
      images: imgToSend ? [imgToSend] : null
    };
    setMessages(prev => [...prev, userMessage]);
    setIsStreaming(true);
    setStreamedContent("");
    setToolExecutions([]);

    try {
      // Prepare image base64 without prefix data:image/...;base64,
      let imagesPayload: string[] | null = null;
      if (imgToSend) {
        imagesPayload = [imgToSend.split(',')[1]];
      }

      const response = await fetch(`${BACKEND_URL}/api/conversations/${convId}/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: messageText,
          model: selectedModel,
          images: imagesPayload
        })
      });

      if (!response.ok) throw new Error(`Errore server: ${response.status}`);
      if (!response.body) throw new Error("Il server non ha inviato alcuno stream.");

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let done = false;
      let accumulatedText = "";
      let buffer = "";

      while (!done) {
        const { value, done: doneReading } = await reader.read();
        done = doneReading;
        buffer += decoder.decode(value, { stream: !done });

        let boundary = buffer.indexOf("\n\n");
        while (boundary !== -1) {
          const chunk = buffer.slice(0, boundary).trim();
          buffer = buffer.slice(boundary + 2);

          if (chunk.startsWith("data: ")) {
            const jsonStr = chunk.slice(6);
            try {
              const parsed = JSON.parse(jsonStr);
              
              if (parsed.tool) {
                // Agent started running a tool
                setToolExecutions(prev => [
                  ...prev,
                  { name: parsed.tool, args: parsed.args, collapsed: false }
                ]);
              } else if (parsed.tool_result) {
                // Tool output returned
                setToolExecutions(prev => {
                  const updated = [...prev];
                  if (updated.length > 0) {
                    updated[updated.length - 1].result = parsed.tool_result;
                  }
                  return updated;
                });
              } else if (parsed.content) {
                // Regular response stream text
                accumulatedText += parsed.content;
                setStreamedContent(accumulatedText);
              } else if (parsed.error) {
                accumulatedText += `\n\n[Errore: ${parsed.error}]`;
                setStreamedContent(accumulatedText);
              }
            } catch (e) {
              // Incomplete chunk
            }
          }
          boundary = buffer.indexOf("\n\n");
        }
      }

      // Finalize assistant message
      setMessages(prev => [
        ...prev, 
        { id: (Date.now() + 1).toString(), role: 'assistant', content: accumulatedText }
      ]);
      setStreamedContent("");
      setToolExecutions([]);
      fetchConversations();

    } catch (err: any) {
      console.error("Streaming error:", err);
      setMessages(prev => [
        ...prev,
        { 
          id: (Date.now() + 1).toString(), 
          role: 'assistant', 
          content: `Errore di connessione. Assicurati che il backend ed Ollama siano attivi. Dettagli: ${err.message}` 
        }
      ]);
    } finally {
      setIsStreaming(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const toggleToolCollapse = (index: number) => {
    setToolExecutions(prev => {
      const updated = [...prev];
      updated[index].collapsed = !updated[index].collapsed;
      return updated;
    });
  };

  return (
    <div className="app-container">
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="sidebar-header">
          <div className="logo-icon">
            <Brain size={20} />
          </div>
          <span className="logo-text">Athena AI</span>
        </div>

        <button 
          className="new-chat-btn" 
          onClick={() => {
            setActiveConversationId(null);
            setMessages([]);
            setStreamedContent("");
            setToolExecutions([]);
          }}
        >
          <Plus size={16} />
          Nuova Chat
        </button>

        <div className="sidebar-content">
          {/* Chat conversations */}
          <div className="conversations-group">
            <h3 className="section-title">Conversazioni</h3>
            {conversations.length === 0 ? (
              <div style={{ padding: '10px 12px', fontSize: '0.8rem', color: 'var(--text-dark)' }}>
                Nessuna conversazione
              </div>
            ) : (
              conversations.map((conv) => (
                <div 
                  key={conv.id}
                  className={`conv-item ${activeConversationId === conv.id ? 'active' : ''}`}
                  onClick={() => fetchMessages(conv.id)}
                >
                  <MessageSquare size={14} style={{ marginRight: '8px', flexShrink: 0 }} />
                  <span className="conv-title">{conv.title}</span>
                  <button 
                    className="conv-delete-btn"
                    onClick={(e) => handleDeleteConversation(e, conv.id)}
                  >
                    <Trash2 size={13} />
                  </button>
                </div>
              ))
            )}
          </div>

          {/* RAG Knowledge base documents list */}
          <div className="knowledge-group">
            <div className="section-title-container">
              <h3 className="section-title">Knowledge Base</h3>
              <input 
                type="file" 
                ref={fileInputRef} 
                style={{ display: 'none' }} 
                accept=".pdf,.txt,.md"
                onChange={handleUploadDocument}
              />
              <button 
                className="upload-icon-btn" 
                title="Carica PDF/Testo"
                disabled={uploadingDoc}
                onClick={() => fileInputRef.current?.click()}
              >
                {uploadingDoc ? (
                  <span style={{ fontSize: '0.7rem' }}>...</span>
                ) : (
                  <Upload size={14} />
                )}
              </button>
            </div>
            
            <div style={{ marginTop: '8px' }}>
              {documents.length === 0 ? (
                <div style={{ padding: '10px 12px', fontSize: '0.8rem', color: 'var(--text-dark)' }}>
                  Carica documenti (.pdf, .txt) per il RAG
                </div>
              ) : (
                documents.map((doc, idx) => (
                  <div key={idx} className="doc-item">
                    <FileText size={13} style={{ marginRight: '6px', color: '#a78bfa', flexShrink: 0 }} />
                    <span className="doc-name" title={doc.name}>{doc.name}</span>
                    <span className="doc-chunks">{doc.chunks} chk</span>
                    <button 
                      className="doc-delete-btn"
                      onClick={() => handleDeleteDocument(doc.name)}
                    >
                      <Trash2 size={12} />
                    </button>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

        <div className="sidebar-footer">
          <span>Athena v2.0 & v4.0</span>
          <Bot size={14} />
        </div>
      </aside>

      {/* Main Chat Panel */}
      <main className="chat-area">
        {/* Top Navbar */}
        <div className="top-bar">
          <div className="top-bar-left">
            <h2 className="chat-title">
              {activeConversationId 
                ? (conversations.find(c => c.id === activeConversationId)?.title || "Chat Attiva") 
                : "Nuova Sessione"}
            </h2>
            {activeConversationId && (
              <span className="personality-badge">
                {personalities.find(p => p.id === (conversations.find(c => c.id === activeConversationId)?.personality))?.name || "Athena Standard"}
              </span>
            )}
          </div>

          <div className="top-bar-right">
            {/* Model Selector */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Settings size={14} style={{ color: 'var(--text-muted)' }} />
              <select 
                className="settings-select"
                value={selectedModel}
                onChange={(e) => setSelectedModel(e.target.value)}
              >
                {COMMON_MODELS.map(m => (
                  <option key={m.id} value={m.id}>{m.name}</option>
                ))}
              </select>
            </div>

            {/* Personality Selector */}
            {!activeConversationId && (
              <select 
                className="settings-select"
                value={selectedPersonality}
                onChange={(e) => setSelectedPersonality(e.target.value)}
              >
                {personalities.map(p => (
                  <option key={p.id} value={p.id}>{p.name}</option>
                ))}
              </select>
            )}
          </div>
        </div>

        {/* Message Container */}
        {messages.length === 0 && !streamedContent && toolExecutions.length === 0 ? (
          /* Welcome Screen */
          <div className="welcome-container">
            <div className="welcome-logo">
              <Bot size={36} />
            </div>
            <h1 className="welcome-title">Athena AI Agentic Suite</h1>
            <p className="welcome-subtitle">
              Sperimenta le fasi avanzate: RAG su PDF locali, Ricerca Web DuckDuckGo, 
              interprete Python sandboxed ed input/output multimediale di immagini e voce.
            </p>

            <div className="suggested-actions">
              <div 
                className="suggested-card" 
                onClick={() => handleSuggestedAction("law_tutor", "Secondo il diritto italiano, quali sono gli elementi costitutivi del negozio giuridico?")}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                  <Scale size={16} style={{ color: '#a78bfa' }} />
                  <h4>Tutor Legale + RAG</h4>
                </div>
                <p>Carica codici o dispense a sinistra per risposte mirate e citate.</p>
              </div>

              <div 
                className="suggested-card" 
                onClick={() => handleSuggestedAction("coder", "Calcola la sequenza di Fibonacci fino al 15° termine usando il codice Python.")}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                  <Terminal size={16} style={{ color: '#2dd4bf' }} />
                  <h4>Agenti + Strumenti</h4>
                </div>
                <p>Esegue script ed equazioni nel backend ritornando l'output.</p>
              </div>

              <div 
                className="suggested-card" 
                onClick={() => handleSuggestedAction("athena", "Cerca sul web chi ha vinto l'ultimo premio Nobel per la Fisica e spiega la motivazione.")}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                  <Brain size={16} style={{ color: '#fb7185' }} />
                  <h4>Ricerca Web Attiva</h4>
                </div>
                <p>Cerca informazioni aggiornate sul web tramite DuckDuckGo.</p>
              </div>

              <div 
                className="suggested-card" 
                onClick={() => {
                  alert("Attiva il modello LLaVA dal selettore in alto a destra, carica un'immagine e chiedi: 'Cosa c'è in questa immagine?'");
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                  <ImageIcon size={16} style={{ color: '#fbbf24' }} />
                  <h4>Multimodale (Visione)</h4>
                </div>
                <p>Allega un'immagine ad Athena per analizzarla e spiegarla.</p>
              </div>
            </div>
          </div>
        ) : (
          /* Chat logs */
          <div className="messages-container">
            {messages.map((msg) => (
              <div key={msg.id} className={`message-row ${msg.role}`}>
                <div className="message-avatar">
                  {msg.role === 'user' ? 'U' : 'A'}
                </div>
                
                <div className="message-bubble-wrapper">
                  {msg.images && msg.images.map((img, i) => (
                    <img 
                      key={i} 
                      src={img.startsWith('data:') ? img : `data:image/jpeg;base64,${img}`} 
                      alt="Allegato" 
                      className="chat-image-preview" 
                    />
                  ))}
                  
                  <div className="message-bubble">
                    <div className="message-content">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {msg.content}
                      </ReactMarkdown>
                    </div>
                  </div>
                  
                  {/* TTS Button */}
                  {msg.role === 'assistant' && (
                    <button 
                      className="audio-control-btn"
                      onClick={() => handleSpeakMessage(msg.id, msg.content)}
                    >
                      {speakingMessageId === msg.id ? (
                        <>
                          <VolumeX size={12} /> Spegni Voce
                        </>
                      ) : (
                        <>
                          <Volume2 size={12} /> Ascolta Risposta
                        </>
                      )}
                    </button>
                  )}
                </div>
              </div>
            ))}

            {/* Render active tool executions */}
           {toolExecutions.map((tool, idx) => (
  <div key={`tool-${idx}`} className="tool-exec-container">
    <div className="tool-header" onClick={() => toggleToolCollapse(idx)}>
      <span className="tool-name-badge">
        <Terminal size={13} />
        Esecuzione Strumento: <code>{tool.name}()</code>
      </span>
      {tool.collapsed ? <ChevronDown size={14} /> : <ChevronUp size={14} />}
    </div>
    {!tool.collapsed && (
      <div style={{ marginTop: '6px' }}>
        <div style={{ fontSize: '0.75rem', color: 'var(--text-dark)', marginBottom: '4px' }}>
          Argomenti: <code>{JSON.stringify(tool.args)}</code>
        </div>
        {tool.result ? (
          <div className="tool-output">
            {tool.result}
            {tool.name === 'write_to_file' && (() => {
              const match = tool.result.match(/URL:\s*(https?:\/\/\S+)/);
              return match ? (
                <div style={{ marginTop: '8px' }}>
                  <a 
                    href={match[1]} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    download
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '6px',
                      padding: '6px 12px',
                      background: '#a78bfa',
                      color: '#1a1a2e',
                      borderRadius: '6px',
                      fontSize: '0.8rem',
                      fontWeight: 600,
                      textDecoration: 'none'
                    }}
                  >
                    <FileCheck size={14} />
                    Scarica file
                  </a>
                </div>
              ) : null;
            })()}
          </div>
        ) : (
          <div style={{ color: 'var(--text-dark)', fontSize: '0.75rem', fontStyle: 'italic', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Play size={10} className="pulse-animation" /> Esecuzione in corso...
          </div>
        )}
      </div>
    )}
  </div>
))}

            {/* Streamed content */}
            {streamedContent && (
              <div className="message-row assistant">
                <div className="message-avatar">A</div>
                <div className="message-bubble-wrapper">
                  <div className="message-bubble">
                    <div className="message-content">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {streamedContent}
                      </ReactMarkdown>
                      <span className="streaming-cursor" />
                    </div>
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        )}

        {/* Input area */}
        <div className="input-area">
          {/* Base64 preview list */}
          {attachedImage && (
            <div className="input-image-preview-container">
              <div className="input-image-card">
                <img src={attachedImage} alt="Preview" />
                <button className="remove-img-btn" onClick={() => setAttachedImage(null)}>
                  <X size={10} />
                </button>
              </div>
            </div>
          )}

          <div className={`input-container ${attachedImage ? 'with-preview' : ''}`}>
            {/* Hidden Input for Images */}
            <input 
              type="file"
              ref={imageInputRef}
              style={{ display: 'none' }}
              accept="image/*"
              onChange={handleAttachImage}
            />
            
            {/* Attach Image Button */}
            <button 
              className="input-action-btn"
              title="Carica Immagine (Multimodale)"
              onClick={() => imageInputRef.current?.click()}
              disabled={isStreaming}
            >
              <ImageIcon size={18} />
            </button>

            {/* Speech Microphone Button */}
            <button 
              className={`input-action-btn ${isListening ? 'active-mic' : ''}`}
              title={isListening ? "Rilascia per interrompere" : "Detta Messaggio"}
              onClick={handleToggleListen}
              disabled={isStreaming}
            >
              {isListening ? <MicOff size={18} /> : <Mic size={18} />}
            </button>

            {/* Main Text Input */}
            <textarea
              ref={textareaRef}
              className="chat-input"
              placeholder={isListening ? "Sto ascoltando la tua voce..." : "Fai una domanda ad Athena..."}
              rows={1}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={isStreaming}
            />

            {/* Send Button */}
            <button 
              className="send-btn" 
              onClick={() => handleSendMessage()}
              disabled={(!input.trim() && !attachedImage) || isStreaming}
            >
              <Send size={18} />
            </button>
          </div>
        </div>
      </main>
    </div>
  );
}
