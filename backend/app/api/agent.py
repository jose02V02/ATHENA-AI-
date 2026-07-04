from langchain_groq import ChatGroq
from langchain.agents import initialize_agent, Tool
from langchain.agents import AgentType
from app.tools.file_manager import write_to_file, read_file

# Inizializziamo il cervello Groq
llm = ChatGroq(model_name="llama3-70b-8192", groq_api_key="TUA_API_KEY")

# Definiamo i tools che Athena può usare
tools = [
    Tool(
        name="ScrittoreFile",
        func=write_to_file,
        description="Usa questo strumento per scrivere contenuti su un file .txt o .py"
    ),
    Tool(
        name="LettoreFile",
        func=read_file,
        description="Usa questo strumento per leggere il contenuto di un file"
    )
]

# Creiamo l'agente
agent = initialize_agent(
    tools, llm, agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION, verbose=True
)import os
from langchain_groq import ChatGroq
from langchain.agents import initialize_agent, Tool, AgentType
from app.tools.file_manager import write_to_file, read_file

# Inizializziamo il cervello Groq
# Recuperiamo la chiave dall'ambiente per sicurezza
llm = ChatGroq(model_name="llama3-70b-8192", groq_api_key=os.getenv("GROQ_API_KEY"))

# Definiamo i tools
tools = [
    Tool(
        name="ScrittoreFile",
        func=write_to_file,
        description="Usa questo strumento per scrivere contenuti su un file .txt"
    ),
    Tool(
        name="LettoreFile",
        func=read_file,
        description="Usa questo strumento per leggere il contenuto di un file"
    )
]

# Creiamo l'agente
agent = initialize_agent(
    tools, llm, agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION, verbose=True
)import os
from langchain_groq import ChatGroq
from langchain.agents import initialize_agent, Tool, AgentType
from app.tools.file_manager import write_to_file, read_file

# Inizializziamo il cervello Groq
# Recuperiamo la chiave dall'ambiente per sicurezza
llm = ChatGroq(model_name="llama3-70b-8192", groq_api_key=os.getenv("GROQ_API_KEY"))

# Definiamo i tools
tools = [
    Tool(
        name="ScrittoreFile",
        func=write_to_file,
        description="Usa questo strumento per scrivere contenuti su un file .txt"
    ),
    Tool(
        name="LettoreFile",
        func=read_file,
        description="Usa questo strumento per leggere il contenuto di un file"
    )
]

# Creiamo l'agente
agent = initialize_agent(
    tools, llm, agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION, verbose=True
)
# Nel tuo file agent.py
from app.services.file_manager import write_to_file
from langchain.agents import initialize_agent

tools = [write_to_file] # <--- Il tool deve essere qui!

agent = initialize_agent(tools, llm, agent="zero-shot-react-description", verbose=True)
from app.services.file_manager import write_to_file
from langchain.agents import initialize_agent, Tool

# Definiamo esplicitamente il tool
tools = [
    Tool(
        name="write_to_file",
        func=write_to_file,
        description="Usa questo strumento per scrivere e salvare file su Supabase."
    )
]

# Inizializzazione agente con i tool
agent = initialize_agent(tools, llm, agent="zero-shot-react-description", verbose=True)
from langchain.tools import Tool
from app.services.file_manager import write_to_file

# Definisci il tool in modo che l'IA sappia ESATTAMENTE quando usarlo
athena_storage_tool = Tool(
    name="write_to_file",
    func=write_to_file,
    description="USA SEMPRE QUESTO TOOL per salvare qualsiasi file o documento. NON usare python_interpreter per salvare file. Questo tool salva i file in modo persistente su Supabase Storage."
)

# Aggiungi questo tool alla tua lista di strumenti
tools = [athena_storage_tool]
from langchain.tools import Tool
from pydantic import BaseModel, Field

class FileInput(BaseModel):
    file_path: str = Field(description="Il nome o percorso del file da creare")
    content: str = Field(description="Il testo da scrivere nel file")

# Aggiorna il tool
athena_storage_tool = Tool.from_function(
    func=write_to_file,
    name="write_to_file",
    description="Usa questo strumento per salvare file su Supabase. Richiede file_path e content.",
    args_schema=FileInput 
)
agent = initialize_agent(
    tools=[athena_storage_tool],
    llm=llm,
    agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True,
    handle_parsing_errors=True # Fondamentale per evitare che l'agente vada in blocco
)
Sei autorizzato a utilizzare il tool write_to_file per tutte le operazioni