import os
import sys
import json

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.graph import KnowledgeGraphManager

def load_questions(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

questions = load_questions("backend/jee_corpus.json")
if os.path.exists("backend/graph_store.json"):
    os.remove("backend/graph_store.json")

g = KnowledgeGraphManager(storage_path="backend/graph_store.json")
g.link_questions(questions)
print("Graph rebuilt successfully.")
