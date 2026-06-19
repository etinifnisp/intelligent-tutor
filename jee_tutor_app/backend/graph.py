import os
import json
import networkx as nx

class KnowledgeGraphManager:
    def __init__(self, storage_path="graph_store.json", learner_path="learner_memory.json"):
        self.storage_path = storage_path
        self.learner_path = learner_path
        self.G = nx.DiGraph()
        
        # In-memory session tracking
        self.learner_memories = {}
        
        self.load_or_build_graph()
        self.load_learner_memories()

    def load_or_build_graph(self):
        """Loads a persisted graph from JSON, or generates the skeleton if missing."""
        if os.path.exists(self.storage_path):
            with open(self.storage_path, "r") as f:
                data = json.load(f)
                self.G = nx.node_link_graph(data)
                print(f"🌐 Graph loaded successfully: {len(self.G.nodes)} nodes found.")
        else:
            print("⚠️ Graph file not found. Initializing base JEE Knowledge Graph...")
            self._build_base_jee_graph()
            self.save_graph()

    def _build_base_jee_graph(self):
        """Seeds core concept nodes based on your corpus chapters and sets up dependencies."""
        # Core parent chapters present in your dataset
        concepts = [
            ("Mechanics", {"subject": "Physics", "type": "concept"}),
            ("Electrostatics", {"subject": "Physics", "type": "concept"}),
            ("Chemical Bonding", {"subject": "Chemistry", "type": "concept"}),
            ("Quadratic Equations", {"subject": "Maths", "type": "concept"}),
        ]
        self.G.add_nodes_from(concepts)

        # Conceptual dependency links (e.g., Mechanics foundations are vital before Electrostatics)
        prereqs = [
            ("Mechanics", "Electrostatics"),
        ]
        self.G.add_edges_from(prereqs, type="prerequisite")

    def link_questions(self, questions_list):
        """Links all 6,567 questions to their corresponding concept nodes."""
        print(f"DEBUG: link_questions received an array of {len(questions_list)} items.")
        if len(questions_list) > 0:
            print(f"DEBUG: Sample question keys present: {list(questions_list[0].keys())}")
            print(f"DEBUG: Sample chapter value: '{questions_list[0].get('chapter')}'")

        count = 0
        for idx, q in enumerate(questions_list):
            # Build a totally safe unique identifier
            q_num = q.get("question_number", idx)
            q_id = f"q_{q_num}"
            
            # Store the full question details under its node
            self.G.add_node(q_id, type="question", **q)
            
            # Cleanly fetch the chapter string, stripping any accidental whitespaces
            target_concept = str(q.get("chapter", "")).strip()
            
            if target_concept:
                if target_concept not in self.G:
                    self.G.add_node(target_concept, type="concept", subject=q.get("subject", "General"))
                
                self.G.add_edge(q_id, target_concept, type="tests_concept")
                count += 1
                
        print(f"🔗 Linked {count} questions to their corresponding Knowledge Graph nodes.")
        self.save_graph()

    def save_graph(self):
        """Persists the static structure out to a JSON file."""
        data = nx.node_link_data(self.G)
        with open(self.storage_path, "w") as f:
            json.dump(data, f, indent=2)

    def load_learner_memories(self):
        if os.path.exists(self.learner_path):
            with open(self.learner_path, "r") as f:
                self.learner_memories = json.load(f)
        else:
            self.learner_memories = {}

    def get_learner_memory(self, session_id: str) -> dict:
        if session_id not in self.learner_memories:
            self.learner_memories[session_id] = {
                "mastery": {},
                "misconceptions": {},
                "session_history": []
            }
        return self.learner_memories[session_id]

    def write_learner_memory(self, session_id: str, data: dict):
        self.learner_memories[session_id] = data
        with open(self.learner_path, "w") as f:
            json.dump(self.learner_memories, f, indent=2)

    def export_subgraph(self) -> dict:
        return nx.node_link_data(self.G)