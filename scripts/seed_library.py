"""Upload docs/knowledge/*.md to the Evolus knowledge library through the API.

    python -m scripts.seed_library            # uses EVOLUS_LIBRARY_ID from .env
    python -m scripts.seed_library --list     # show documents and indexing status
"""
import asyncio
import json
import pathlib
import sys

from src.config import settings
from src.evolus import client as evolus

DOCS = pathlib.Path(__file__).resolve().parent.parent / "docs" / "knowledge"


async def main() -> int:
    lib = settings.evolus_library_id
    if not (evolus.configured() and lib):
        print("Set EVOLUS_API_KEY, EVOLUS_APPLICATION_ID and EVOLUS_LIBRARY_ID in .env first.")
        return 1
    if "--list" in sys.argv:
        print(json.dumps(await evolus.list_library_documents(lib), indent=2))
        return 0
    for path in sorted(DOCS.glob("*.md")):
        res = await evolus.upload_library_document(lib, path.name, path.read_bytes(), "en")
        print(f"uploaded {path.name}: {json.dumps(res)[:200]}")
    print("Indexing runs in the background. Check with: python -m scripts.seed_library --list")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
