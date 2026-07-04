,import os
from supabase import create_client
from dotenv import load_dotenv

# Carica le variabili dal file .env
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def write_to_file(filename: str, content: str) -> str:
    """Carica il file nel bucket 'athena-files' su Supabase."""
    try:
        # Caricamento del file nel bucket
        supabase.storage.from_("athena-files").upload(
            path=filename,
            file=content.encode("utf-8"),
            file_options={"content-type": "text/plain"}
        )
        return f"File '{filename}' salvato correttamente su Supabase!"
    except Exception as e:
        return f"Errore durante il salvataggio su Supabase: {str(e)}"