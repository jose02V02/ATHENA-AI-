from pypdf import PdfReader
from docx import Document
from pathlib import Path
import aiofiles

async def extract_text(file_path: str) -> str:
    ext = Path(file_path).suffix.lower()
    
    if ext == ".pdf":
        reader = PdfReader(file_path)
        return "\n".join([page.extract_text() for page in reader.pages])
    
    elif ext == ".docx":
        doc = Document(file_path)
        return "\n".join([p.text for p in doc.paragraphs])
    
    elif ext in [".txt", ".md", ".py", ".js", ".ts", ".json"]:
        async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
            return await f.read()
    
    elif ext == ".csv":
        async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
            return await f.read()
    
    else:
        raise ValueError(f"Formato non supportato: {ext}")
