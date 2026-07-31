import json
import os
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_ROOT.parent
sys.path.insert(0, str(BACKEND_ROOT))

from app.services.knowledge_graph import KnowledgeGraphManager

CORPUS_PATH = PROJECT_ROOT / "data" / "corpus" / "jee_corpus.json"
GRAPH_STORE_PATH = PROJECT_ROOT / "data" / "graph_store.json"


def load_questions(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


if __name__ == "__main__":
    questions = load_questions(CORPUS_PATH)
    if GRAPH_STORE_PATH.exists():
        os.remove(GRAPH_STORE_PATH)

    graph = KnowledgeGraphManager(storage_path=str(GRAPH_STORE_PATH))
    graph.link_questions(questions)
    print("Graph rebuilt successfully.")
