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