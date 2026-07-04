import sys
import io
import math
import json
from duckduckgo_search import DDGS
from app.core.file_manager import write_to_file

def web_search(query: str) -> str:
    """Ricerca sul web tramite DuckDuckGo e restituisce i risultati più pertinenti."""
    try:
        with DDGS() as ddgs:
            results = [r for r in ddgs.text(query, max_results=4)]
            if not results:
                return "Nessun risultato trovato sul web per questa ricerca."
            output = []
            for r in results:
                output.append(f"Titolo: {r.get('title')}\nLink: {r.get('href')}\nDescrizione: {r.get('body')}\n")
            return "\n".join(output)
    except Exception as e:
        return f"Errore durante la ricerca web: {str(e)}"

def python_interpreter(code: str) -> str:
    """Esegue codice Python locale in sicurezza e restituisce l'output standard (stdout/stderr)."""
    for bad in ["os", "subprocess", "shutil", "socket", "requests", "urllib"]:
        if f"import {bad}" in code or f"from {bad}" in code:
            return f"Errore: L'importazione del modulo '{bad}' è bloccata per ragioni di sicurezza."

    old_stdout = sys.stdout
    old_stderr = sys.stderr
    redirected_output = io.StringIO()
    redirected_error = io.StringIO()
    sys.stdout = redirected_output
    sys.stderr = redirected_error

    glob = {
        "__builtins__": __builtins__,
        "math": math,
        "json": json,
    }
    loc = {}

    try:
        exec(code, glob, loc)
        sys.stdout = old_stdout
        sys.stderr = old_stderr

        stdout_val = redirected_output.getvalue()
        stderr_val = redirected_error.getvalue()

        res = ""
        if stdout_val:
            res += stdout_val
        if stderr_val:
            res += f"\nErrori:\n{stderr_val}"

        if not res.strip():
            res = "Codice eseguito con successo (nessun output stampato)."
        return res
    except Exception as e:
        sys.stdout = old_stdout
        sys.stderr = old_stderr
        return f"Errore di esecuzione: {str(e)}"

# Register of available tools
TOOLS_DEFINITION = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Cerca informazioni aggiornate su internet relative a notizie, eventi recenti o quesiti generali.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "La query di ricerca testuale da inviare al motore."
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "python_interpreter",
            "description": "Esegue codice Python per fare calcoli matematici complessi, manipolare dati o risolvere compiti computazionali.",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "Il codice Python da eseguire. Usa print() per visualizzare i risultati."
                    }
                },
                "required": ["code"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_to_file",
            "description": "Salva un file di testo nel bucket Supabase 'athena-files'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Nome/percorso del file da salvare"
                    },
                    "content": {
                        "type": "string",
                        "description": "Contenuto testuale del file"
                    }
                },
                "required": ["file_path", "content"]
            }
        }
    }
]

def execute_tool(name: str, arguments: dict) -> str:
    if name == "web_search":
        return web_search(arguments.get("query", ""))
    elif name == "python_interpreter":
        return python_interpreter(arguments.get("code", ""))
    elif name == "write_to_file":
        return write_to_file(arguments.get("file_path", ""), arguments.get("content", ""))
    else:
        return f"Errore: Strumento '{name}' non supportato."