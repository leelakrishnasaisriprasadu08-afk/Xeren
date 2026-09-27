import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from xeren.core.runtime import XerenCore

print("Starting test_ingest.py...")
core = XerenCore()
print("XerenCore instantiated.")
try:
    res = core.ingest_knowledge(texts=["Test knowledge ingestion."], source="scratch_test")
    print("Ingestion result:", res.operation.value, "chunks:", len(res.inserted_chunk_ids))
except Exception as e:
    import traceback
    print("Ingestion error:", e)
    traceback.print_exc()
