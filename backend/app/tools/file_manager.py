import os
from supabase import create_client
from dotenv import load_dotenv

# Carica le variabili dal file .env
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        # Modifica il file backend/app/tools/file_manager.py
def write_to_file(file_path: str, content: str) -> str:
    try:
        # Usa file_path invece di filename
        supabase.storage.from_("athena-files").upload(
            path=file_path, 
            file=content.encode("utf-8"),
            file_options={"content-type": "text/plain"}
        )
        return f"File '{file_path}' salvato correttamente su Supabase."
    except Exception as e:
        return f"Errore: {str(e)}"
        def write_to_file(file_path: str, content: str) -> str:
    try:
        supabase.storage.from_("athena-files").upload(
            path=file_path,
            file=content.encode("utf-8"),
            file_options={"content-type": "text/plain", "upsert": "true"}
        )
        # Genera un URL firmato valido 1 ora (3600 secondi)
        signed = supabase.storage.from_("athena-files").create_signed_url(file_path, 3600)
        url = signed.get("signedURL") or signed.get("signed_url") or ""
        return f"File '{file_path}' salvato correttamente su Supabase. URL: {url}"
    except Exception as e:
        return f"Errore: {str(e)}"