import os
from supabase import create_client
from dotenv import load_dotenv

# Carica le variabili dal file .env
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def write_to_file(file_path: str, content: str) -> str:
    """Carica il file nel bucket 'athena-files' su Supabase e restituisce un link di download."""
    try:
        # Caricamento del file nel bucket (upsert=true permette di sovrascrivere se già esiste)
        supabase.storage.from_("athena-files").upload(
            path=file_path,
            file=content.encode("utf-8"),
            file_options={"content-type": "text/plain", "upsert": "true"}
        )

        # Genera un URL firmato valido per 1 ora (3600 secondi)
        signed = supabase.storage.from_("athena-files").create_signed_url(file_path, 3600)
        url = signed.get("signedURL") or signed.get("signed_url") or ""

        return f"File '{file_path}' salvato correttamente su Supabase. URL: {url}"
    except Exception as e:
        return f"Errore durante il salvataggio su Supabase: {str(e)}"


def read_file(file_path: str) -> str:
    """Legge il contenuto di un file dal bucket 'athena-files' su Supabase."""
    try:
        response = supabase.storage.from_("athena-files").download(file_path)
        return response.decode("utf-8")
    except Exception as e:
        return f"Errore durante la lettura da Supabase: {str(e)}"