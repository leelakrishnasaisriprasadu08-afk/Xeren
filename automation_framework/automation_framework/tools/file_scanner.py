"""
Reads local notes/materials the user has granted access to, so a plugin
grounds its output in the user's own documents instead of guessing.

Supports .txt/.md natively. .pdf/.docx support switches on automatically
if PyPDF2 / python-docx are installed -- otherwise those files are skipped
with a warning instead of crashing the pipeline.
"""
import os
from typing import Iterable, List

try:
    import PyPDF2  # type: ignore
except ImportError:
    PyPDF2 = None

try:
    import docx  # type: ignore  (python-docx)
except ImportError:
    docx = None

TEXT_EXTENSIONS = {".txt", ".md"}
SUPPORTED_EXTENSIONS = TEXT_EXTENSIONS | {".pdf", ".docx"}


class LocalFileScanner:
    def __init__(self, root_dir: str):
        self.root_dir = root_dir

    def find_by_keywords(self, keywords: Iterable[str]) -> List[str]:
        """Walk root_dir and return paths whose filename loosely matches
        one of the given keywords (subjects). Empty keywords -> everything
        supported under root_dir."""
        keywords_lower = [k.lower() for k in keywords if k]
        matches: List[str] = []
        if not os.path.isdir(self.root_dir):
            return matches

        for dirpath, _, filenames in os.walk(self.root_dir):
            for fname in filenames:
                ext = os.path.splitext(fname)[1].lower()
                if ext not in SUPPORTED_EXTENSIONS:
                    continue
                if not keywords_lower or any(k in fname.lower() for k in keywords_lower):
                    matches.append(os.path.join(dirpath, fname))
        return matches

    def extract_text(self, paths: Iterable[str], max_chars_per_file: int = 6000) -> str:
        chunks = []
        for path in paths:
            text = self._read_one(path)
            if text:
                chunks.append(f"--- {os.path.basename(path)} ---\n{text[:max_chars_per_file]}")
        return "\n\n".join(chunks)

    def _read_one(self, path: str) -> str:
        ext = os.path.splitext(path)[1].lower()
        try:
            if ext in TEXT_EXTENSIONS:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    return f.read()
            if ext == ".pdf" and PyPDF2:
                text = []
                with open(path, "rb") as f:
                    reader = PyPDF2.PdfReader(f)
                    for page in reader.pages:
                        text.append(page.extract_text() or "")
                return "\n".join(text)
            if ext == ".docx" and docx:
                document = docx.Document(path)
                return "\n".join(p.text for p in document.paragraphs)
        except Exception as exc:  # noqa: BLE001 - one bad file shouldn't kill the run
            print(f"[file_scanner] Skipped {path}: {exc}")
        return ""
