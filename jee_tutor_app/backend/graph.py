import os
import json
import logging
import networkx as nx
from typing import Optional, List, Dict, Any

logger = logging.getLogger("tutor.graph")

# ══════════════════════════════════════════════════════════════
#  JEE KNOWLEDGE TAXONOMY  (module-level constants)
#  58 concept nodes — Physics · Chemistry · Mathematics
#  35 prerequisite edges + 8 cross-domain hint-scaffold edges
# ══════════════════════════════════════════════════════════════

_CHAPTER_NODES: List[tuple] = [
    # ── Physics ────────────────────────────────────────────────
    ("Kinematics",                   {"subject": "Physics",     "type": "chapter"}),
    ("Laws of Motion",               {"subject": "Physics",     "type": "chapter"}),
    ("Work Energy Power",            {"subject": "Physics",     "type": "chapter"}),
    ("Rotational Motion",            {"subject": "Physics",     "type": "chapter"}),
    ("Gravitation",                  {"subject": "Physics",     "type": "chapter"}),
    ("Properties of Matter",         {"subject": "Physics",     "type": "chapter"}),
    ("Thermodynamics",               {"subject": "Physics",     "type": "chapter"}),
    ("Waves",                        {"subject": "Physics",     "type": "chapter"}),
    ("Electrostatics",               {"subject": "Physics",     "type": "chapter"}),
    ("Current Electricity",          {"subject": "Physics",     "type": "chapter"}),
    ("Magnetic Effects of Current",  {"subject": "Physics",     "type": "chapter"}),
    ("Electromagnetic Induction",    {"subject": "Physics",     "type": "chapter"}),
    ("Alternating Current",          {"subject": "Physics",     "type": "chapter"}),
    ("Electromagnetic Waves",        {"subject": "Physics",     "type": "chapter"}),
    ("Ray Optics",                   {"subject": "Physics",     "type": "chapter"}),
    ("Wave Optics",                  {"subject": "Physics",     "type": "chapter"}),
    ("Modern Physics",               {"subject": "Physics",     "type": "chapter"}),
    ("Semiconductors",               {"subject": "Physics",     "type": "chapter"}),
    # ── Chemistry ──────────────────────────────────────────────
    ("Atomic Structure",             {"subject": "Chemistry",   "type": "chapter"}),
    ("Chemical Bonding",             {"subject": "Chemistry",   "type": "chapter"}),
    ("Periodic Table",               {"subject": "Chemistry",   "type": "chapter"}),
    ("States of Matter",             {"subject": "Chemistry",   "type": "chapter"}),
    ("Chemical Thermodynamics",      {"subject": "Chemistry",   "type": "chapter"}),
    ("Equilibrium",                  {"subject": "Chemistry",   "type": "chapter"}),
    ("Redox Reactions",              {"subject": "Chemistry",   "type": "chapter"}),
    ("Electrochemistry",             {"subject": "Chemistry",   "type": "chapter"}),
    ("Chemical Kinetics",            {"subject": "Chemistry",   "type": "chapter"}),
    ("Solutions",                    {"subject": "Chemistry",   "type": "chapter"}),
    ("Organic Chemistry Basics",     {"subject": "Chemistry",   "type": "chapter"}),
    ("Hydrocarbons",                 {"subject": "Chemistry",   "type": "chapter"}),
    ("Coordination Compounds",       {"subject": "Chemistry",   "type": "chapter"}),
    ("Aldehydes and Ketones",        {"subject": "Chemistry",   "type": "chapter"}),
    ("Carboxylic Acids",             {"subject": "Chemistry",   "type": "chapter"}),
    ("Amines",                       {"subject": "Chemistry",   "type": "chapter"}),
    ("Biomolecules",                 {"subject": "Chemistry",   "type": "chapter"}),
    ("Polymers",                     {"subject": "Chemistry",   "type": "chapter"}),
    # ── Mathematics ────────────────────────────────────────────
    ("Sets and Relations",            {"subject": "Mathematics", "type": "chapter"}),
    ("Functions",                     {"subject": "Mathematics", "type": "chapter"}),
    ("Quadratic Equations",           {"subject": "Mathematics", "type": "chapter"}),
    ("Complex Numbers",               {"subject": "Mathematics", "type": "chapter"}),
    ("Trigonometry",                  {"subject": "Mathematics", "type": "chapter"}),
    ("Inverse Trigonometry",          {"subject": "Mathematics", "type": "chapter"}),
    ("Differential Calculus",         {"subject": "Mathematics", "type": "chapter"}),
    ("Integral Calculus",             {"subject": "Mathematics", "type": "chapter"}),
    ("Differential Equations",        {"subject": "Mathematics", "type": "chapter"}),
    ("Vectors",                       {"subject": "Mathematics", "type": "chapter"}),
    ("3D Geometry",                   {"subject": "Mathematics", "type": "chapter"}),
    ("Straight Lines",                {"subject": "Mathematics", "type": "chapter"}),
    ("Circles",                       {"subject": "Mathematics", "type": "chapter"}),
    ("Conic Sections",                {"subject": "Mathematics", "type": "chapter"}),
    ("Matrices and Determinants",     {"subject": "Mathematics", "type": "chapter"}),
    ("Probability",                   {"subject": "Mathematics", "type": "chapter"}),
    ("Statistics",                    {"subject": "Mathematics", "type": "chapter"}),
    ("Permutations and Combinations", {"subject": "Mathematics", "type": "chapter"}),
    ("Binomial Theorem",              {"subject": "Mathematics", "type": "chapter"}),
    ("Sequences and Series",          {"subject": "Mathematics", "type": "chapter"}),
    ("Mathematical Induction",        {"subject": "Mathematics", "type": "chapter"}),
    ("Linear Programming",            {"subject": "Mathematics", "type": "chapter"}),
]

# (source, target, edge_type) — source MUST be mastered before target
_PREREQ_EDGES: List[tuple] = [
    # Physics
    ("Kinematics",                  "Laws of Motion",              "prerequisite"),
    ("Laws of Motion",              "Work Energy Power",           "prerequisite"),
    ("Work Energy Power",           "Rotational Motion",           "prerequisite"),
    ("Laws of Motion",              "Gravitation",                 "prerequisite"),
    ("Kinematics",                  "Waves",                       "prerequisite"),
    ("Electrostatics",              "Current Electricity",         "prerequisite"),
    ("Current Electricity",         "Magnetic Effects of Current", "prerequisite"),
    ("Magnetic Effects of Current", "Electromagnetic Induction",   "prerequisite"),
    ("Electromagnetic Induction",   "Alternating Current",         "prerequisite"),
    ("Waves",                       "Wave Optics",                 "prerequisite"),
    ("Electrostatics",              "Modern Physics",              "prerequisite"),
    ("Modern Physics",              "Semiconductors",              "prerequisite"),
    # Chemistry
    ("Atomic Structure",            "Chemical Bonding",            "prerequisite"),
    ("Atomic Structure",            "Periodic Table",              "prerequisite"),
    ("Atomic Structure",            "States of Matter",            "prerequisite"),
    ("Chemical Bonding",            "Coordination Compounds",      "prerequisite"),
    ("Redox Reactions",             "Electrochemistry",            "prerequisite"),
    ("Chemical Thermodynamics",     "Equilibrium",                 "prerequisite"),
    ("Organic Chemistry Basics",    "Hydrocarbons",                "prerequisite"),
    ("Organic Chemistry Basics",    "Aldehydes and Ketones",       "prerequisite"),
    ("Organic Chemistry Basics",    "Carboxylic Acids",            "prerequisite"),
    ("Organic Chemistry Basics",    "Amines",                      "prerequisite"),
    ("Hydrocarbons",                "Biomolecules",                "prerequisite"),
    ("Organic Chemistry Basics",    "Polymers",                    "prerequisite"),
    # Mathematics
    ("Sets and Relations",          "Functions",                   "prerequisite"),
    ("Sets and Relations",          "Mathematical Induction",      "prerequisite"),
    ("Trigonometry",                "Inverse Trigonometry",        "prerequisite"),
    ("Trigonometry",                "Differential Calculus",       "prerequisite"),
    ("Functions",                   "Differential Calculus",       "prerequisite"),
    ("Differential Calculus",       "Integral Calculus",           "prerequisite"),
    ("Integral Calculus",           "Differential Equations",      "prerequisite"),
    ("Vectors",                     "3D Geometry",                 "prerequisite"),
    ("Quadratic Equations",         "Complex Numbers",             "prerequisite"),
    ("Quadratic Equations",         "Conic Sections",              "prerequisite"),
    ("Permutations and Combinations", "Probability",               "prerequisite"),
    ("Matrices and Determinants",   "Linear Programming",          "prerequisite"),
    ("Sequences and Series",        "Binomial Theorem",            "prerequisite"),
]

# Cross-domain scaffold hints: solving A often requires mathematical/physics tool B
_HINT_EDGES: List[tuple] = [
    ("Kinematics",               "Differential Calculus",  "hint_scaffold"),
    ("Laws of Motion",           "Vectors",                "hint_scaffold"),
    ("Rotational Motion",        "Integral Calculus",      "hint_scaffold"),
    ("Electrostatics",           "Vectors",                "hint_scaffold"),
    ("Waves",                    "Differential Equations", "hint_scaffold"),
    ("Electromagnetic Induction","Integral Calculus",      "hint_scaffold"),
    ("Current Electricity",      "Quadratic Equations",    "hint_scaffold"),
    ("Thermodynamics",           "Sequences and Series",   "hint_scaffold"),
]


# ══════════════════════════════════════════════════════════════
#  KNOWLEDGE GRAPH MANAGER
# ══════════════════════════════════════════════════════════════

class KnowledgeGraphManager:
    """
    In-process NetworkX graph serving three functions:
      1. Concept topology  — 58 nodes + prereq/hint edges
      2. Question linking  — 6 567 question nodes → concept nodes
      3. Learner memory    — per-session mastery + misconceptions (JSON-backed)
    """

    def __init__(self, storage_path: str = "graph_store.json",
                 learner_path: str = "learner_memory.json"):
        self.storage_path = storage_path
        self.learner_path  = learner_path
        self.G = nx.DiGraph()
        self.learner_memories: Dict[str, dict] = {}

        self.load_or_build_graph()
        self.load_learner_memories()

    # ── Graph initialisation ──────────────────────────────────────────────────

    def load_or_build_graph(self):
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, "r") as f:
                    data = json.load(f)
                self.G = nx.node_link_graph(data)
                logger.info(
                    f"Graph loaded from disk: {len(self.G.nodes)} nodes, "
                    f"{len(self.G.edges)} edges."
                )
            except Exception as e:
                logger.error(f"Failed to load graph: {e} — rebuilding.", exc_info=True)
                self._build_full_graph()
                return
        else:
            logger.warning("No graph file found. Building full JEE Knowledge Graph from taxonomy...")
            self._build_full_graph()
            return

        # Always patch any missing canonical nodes/edges into a loaded graph
        self._ensure_base_concepts()

    def _build_full_graph(self):
        """Build the complete JEE concept graph from module-level taxonomy."""
        self.G.add_nodes_from(_CHAPTER_NODES)
        for src, dst, etype in _PREREQ_EDGES + _HINT_EDGES:
            self.G.add_edge(src, dst, type=etype)
        n_prereq = sum(1 for _, _, d in self.G.edges(data=True) if d.get("type") == "prerequisite")
        n_hint   = sum(1 for _, _, d in self.G.edges(data=True) if d.get("type") == "hint_scaffold")
        logger.info(
            f"Full JEE Knowledge Graph built: {len(self.G.nodes)} nodes, "
            f"{len(self.G.edges)} edges ({n_prereq} prereq, {n_hint} hint-scaffold)."
        )
        self.save_graph()

    def _ensure_base_concepts(self):
        """
        Idempotently add any missing canonical nodes/edges into a loaded graph.
        Safe to call every boot — only writes if changes were made.
        """
        added_nodes = added_edges = 0

        for node, attrs in _CHAPTER_NODES:
            if node not in self.G:
                self.G.add_node(node, **attrs)
                added_nodes += 1

        for src, dst, etype in _PREREQ_EDGES + _HINT_EDGES:
            if src in self.G and dst in self.G and not self.G.has_edge(src, dst):
                self.G.add_edge(src, dst, type=etype)
                added_edges += 1

        if added_nodes or added_edges:
            logger.info(
                f"Graph enriched: +{added_nodes} nodes, +{added_edges} edges. Persisting."
            )
            self.save_graph()
        else:
            logger.debug("Graph integrity check passed — all canonical nodes/edges present.")

    # ── Question linking ──────────────────────────────────────────────────────

    def link_questions(self, questions_list: List[dict]):
        count = 0
        for idx, q in enumerate(questions_list):
            q_num = q.get("question_number", idx)
            q_id  = f"q_{q_num}"
            self.G.add_node(q_id, type="question", **q)
            
            chapter_str = str(q.get("chapter", "")).strip()
            topic_str = str(q.get("topic", "")).strip()
            subject_str = str(q.get("subject", "")).strip()
            
            chapter_node = self._find_chapter_node(chapter_str, subject_str)
            if not chapter_node:
                continue
                
            concept_node_id = None
            if topic_str:
                concept_node_id = f"{chapter_node} - {topic_str}"
                if not self.G.has_node(concept_node_id):
                    self.G.add_node(concept_node_id, subject=subject_str, type="concept", parent_chapter=chapter_node)
                    self.G.add_edge(chapter_node, concept_node_id, type="has_concept")
            else:
                concept_node_id = chapter_node
                
            self.G.add_edge(q_id, concept_node_id, type="tests_concept")
            count += 1
        logger.info(f"Linked {count} questions to canonical Knowledge Graph concepts.")
        self.save_graph()

    # ── Persistence ───────────────────────────────────────────────────────────

    def save_graph(self):
        data = nx.node_link_data(self.G)
        with open(self.storage_path, "w") as f:
            json.dump(data, f, indent=2)
        logger.debug(f"Graph persisted: {len(self.G.nodes)} nodes, {len(self.G.edges)} edges.")

    def load_learner_memories(self):
        if os.path.exists(self.learner_path):
            try:
                with open(self.learner_path, "r") as f:
                    self.learner_memories = json.load(f)
                logger.info(
                    f"Learner memories loaded: {len(self.learner_memories)} sessions."
                )
            except Exception as e:
                logger.error(f"Failed to load learner memories: {e}", exc_info=True)
                self.learner_memories = {}
        else:
            logger.info("No learner memory file — starting fresh.")
            self.learner_memories = {}

    def get_learner_memory(self, session_id: str) -> dict:
        if session_id not in self.learner_memories:
            logger.debug(f"Creating new learner profile for session '{session_id}'.")
            self.learner_memories[session_id] = {
                "mastery":         {},
                "misconceptions":  {},
                "session_history": [],
            }
        return self.learner_memories[session_id]

    def write_learner_memory(self, session_id: str, data: dict):
        self.learner_memories[session_id] = data
        with open(self.learner_path, "w") as f:
            json.dump(self.learner_memories, f, indent=2)
        logger.debug(f"Learner memory persisted for session '{session_id}'.")

    # ── Graph export ──────────────────────────────────────────────────────────

    def export_subgraph(self) -> dict:
        """Full graph topology for the concept-map frontend."""
        return nx.node_link_data(self.G)

    # ══════════════════════════════════════════════════════════════════════════
    #  GRAPH-AWARE RAG  —  the methods the pipeline calls on every PIPELINE turn
    # ══════════════════════════════════════════════════════════════════════════

    def _find_chapter_node(self, chapter: str, subject: str = "") -> Optional[str]:
        """
        Map a chapter name (from the question bank) to a canonical chapter node.
        Priority: exact match → substring → word-overlap.
        """
        # 1. Exact match
        if chapter in self.G and self.G.nodes[chapter].get("type") == "chapter":
            return chapter

        chapter_lower = chapter.lower()
        subject_lower = subject.lower()

        # 2. Substring match (with optional subject filter)
        for node, data in self.G.nodes(data=True):
            if data.get("type") != "chapter":
                continue
            if subject_lower and data.get("subject", "").lower() != subject_lower:
                continue
            node_lower = node.lower()
            if node_lower in chapter_lower or chapter_lower in node_lower:
                return node

        # 3. Alias / Special Mapping
        alias_map = {
            "nlm & friction": "Laws of Motion",
            "mechanics": "Laws of Motion",
            "heat & thermodynamics": "Thermodynamics",
            "shm & elasticity": "Oscillations",
            "general concepts": "Kinematics", # basic stuff
            "electrostatics & capacitance": "Electrostatics",
            "photoelectric effect": "Modern Physics",
            "current electricity": "Current Electricity",
            "ray optics": "Ray Optics",
            "rotational motion": "Rotational Motion"
        }
        if chapter_lower in alias_map:
            return alias_map[chapter_lower]

        # 4. Word-overlap fallback (relaxed — no subject constraint)
        chapter_words = {w for w in chapter_lower.split() if len(w) > 3}
        best_node, best_score = None, 0
        for node, data in self.G.nodes(data=True):
            if data.get("type") != "chapter":
                continue
            node_words = {w for w in node.lower().split() if len(w) > 3}
            score = len(chapter_words & node_words)
            if score > best_score:
                best_score, best_node = score, node

        return best_node if best_score > 0 else None

    def get_graph_rag_context(
        self,
        session_id: str,
        chapter: str,
        subject: str = "",
        mastery_threshold: float = 0.6,
    ) -> Dict[str, Any]:
        """
        Core graph-aware RAG context builder.  Called by the PIPELINE lane
        before constructing the LLM system instruction.

        Returns
        -------
        dict with keys:
          active_concept      — resolved graph node name (or raw chapter)
          current_mastery     — float 0-1
          prereq_chain        — list of direct prerequisite node names
          unmastered_prereqs  — [{"concept", "mastery", "misconception"}] sorted weakest-first
          hint_scaffolds      — cross-domain tool concepts required for this topic
          misconceptions      — known misconception string for this concept
          graph_hint          — ready-to-inject scaffolding directive for the system prompt
          recommended_focus   — highest-priority weak prereq name (or None)
        """
        learner  = self.get_learner_memory(session_id)
        mastery  = learner.get("mastery", {})
        misconcs = learner.get("misconceptions", {})

        # RAG comes with chapter. In a real system, we'd also use the topic, but chapter is enough for scaffolding
        chapter_node = self._find_chapter_node(chapter, subject)

        ctx: Dict[str, Any] = {
            "active_concept":     chapter_node or chapter,
            "current_mastery":    mastery.get(chapter, 0.0),
            "prereq_chain":       [],
            "unmastered_prereqs": [],
            "hint_scaffolds":     [],
            "misconceptions":     misconcs.get(chapter, ""),
            "graph_hint":         "",
            "recommended_focus":  None,
        }

        if not chapter_node or chapter_node not in self.G:
            ctx["graph_hint"] = (
                f"No graph node found for '{chapter}'. Teach this concept directly "
                f"without prerequisite scaffolding."
            )
            return ctx

        # Direct prerequisite nodes (in-edges with type=prerequisite)
        prereqs = [
            src for src, _, d in self.G.in_edges(chapter_node, data=True)
            if d.get("type") == "prerequisite"
        ]
        ctx["prereq_chain"] = prereqs

        # Identify unmastered prerequisites
        unmastered = []
        for prereq in prereqs:
            m = mastery.get(prereq, 0.0)
            if m < mastery_threshold:
                unmastered.append({
                    "concept":       prereq,
                    "mastery":       round(m, 2),
                    "misconception": misconcs.get(prereq, ""),
                })
        unmastered.sort(key=lambda x: x["mastery"])   # weakest first
        ctx["unmastered_prereqs"] = unmastered

        # Cross-domain hint-scaffold tools (out-edges from this concept)
        hint_tools = [
            dst for _, dst, d in self.G.out_edges(chapter_node, data=True)
            if d.get("type") == "hint_scaffold"
        ]
        ctx["hint_scaffolds"] = hint_tools

        # Compose scaffolding directive
        if unmastered:
            weak = ", ".join(
                f"'{u['concept']}' ({u['mastery']:.0%})" for u in unmastered
            )
            ctx["graph_hint"] = (
                f"⚠️  PREREQUISITE GAPS DETECTED: The student has weak mastery in {weak}. "
                f"Before solving '{chapter}', briefly scaffold these missing foundations. "
                f"Do NOT reveal the full solution immediately — use progressive Socratic hints "
                f"and check the student understands each gap before moving forward."
            )
            ctx["recommended_focus"] = unmastered[0]["concept"]

        elif hint_tools:
            tools = ", ".join(hint_tools)
            ctx["graph_hint"] = (
                f"Student has solid prerequisite mastery for '{chapter}'. "
                f"This topic typically requires: {tools}. "
                f"Guide the student to identify and apply these tools to reach the solution."
            )
        else:
            ctx["graph_hint"] = (
                f"Student has strong mastery of all prerequisites for '{chapter}'. "
                f"Challenge them fully — minimal scaffolding needed. "
                f"Focus on depth and edge-case reasoning."
            )

        return ctx

    def get_relevant_files_for_concept(
        self,
        chapter: str,
        subject: str,
        file_registry: Dict[str, str],
        max_files: int = 5,
    ) -> List[str]:
        """
        Select the most relevant corpus files for this concept.
        Scores each file by keyword overlap with subject + chapter name.
        Falls back to subject-level files, then returns [] (caller uses all).
        """
        if not file_registry:
            return []

        subject_lower = subject.lower()
        chapter_words = {w for w in chapter.lower().split() if len(w) > 3}

        scored: List[tuple] = []
        for fname in file_registry:
            fn_lower = fname.lower()
            score = 0
            if subject_lower and subject_lower in fn_lower:
                score += 2
            for word in chapter_words:
                if word in fn_lower:
                    score += 3
            if score > 0:
                scored.append((score, fname))

        scored.sort(reverse=True)
        relevant = [fname for _, fname in scored[:max_files]]

        # Broad subject fallback
        if not relevant and subject_lower:
            relevant = [
                fname for fname in file_registry
                if subject_lower in fname.lower()
            ][:max_files]

        logger.debug(
            f"File selection for '{chapter}' ({subject}): "
            f"{len(relevant)}/{len(file_registry)} files — {relevant}"
        )
        return relevant

    def update_concept_mastery_on_graph(
        self, session_id: str, chapter: str, mastery: float
    ):
        """
        Write session mastery score onto the concept node in-memory.
        Enables the graph viewer to colour nodes by learner progress.
        Does NOT save to disk on every call (too expensive for every turn).
        """
        if chapter and chapter in self.G:
            node_data = self.G.nodes[chapter]
            if "learner_mastery" not in node_data:
                node_data["learner_mastery"] = {}
            node_data["learner_mastery"][session_id] = round(mastery, 2)
            logger.debug(
                f"Graph node '{chapter}' mastery set to "
                f"{mastery:.0%} for session '{session_id}'."
            )

    def get_adaptive_next_concept(
        self, session_id: str, subject: str = ""
    ) -> Optional[str]:
        """
        Recommend the next concept to study via prereq-graph traversal:
          - All prerequisites mastered (≥ 0.7)
          - Concept itself not yet mastered (< 0.7)
        Returns the concept name with lowest current mastery, or None.
        """
        learner = self.get_learner_memory(session_id)
        mastery = learner.get("mastery", {})

        candidates: List[tuple] = []
        for node, data in self.G.nodes(data=True):
            if data.get("type") != "concept":
                continue
            if subject and data.get("subject", "") != subject:
                continue
            node_mastery = mastery.get(node, 0.0)
            if node_mastery >= 0.7:
                continue   # Already mastered

            prereqs = [
                src for src, _, d in self.G.in_edges(node, data=True)
                if d.get("type") == "prerequisite"
            ]
            if all(mastery.get(p, 0.0) >= 0.7 for p in prereqs):
                candidates.append((node_mastery, node))

        if not candidates:
            return None
        candidates.sort()   # Lowest mastery first
        return candidates[0][1]

    def get_questions_by_concept(
        self,
        chapter: str,
        subject: str = "",
        limit_per_difficulty: int = 1,
    ) -> Dict[str, List[dict]]:
        """
        Return real JEE questions linked to this concept, grouped by difficulty.
        Used to populate the Option B (quiz path) in two-option tutor responses.

        Returns
        -------
        {"Easy": [...], "Medium": [...], "Hard": [...]}
        Each item: {question_number, raw_text, difficulty, chapter}
        """
        chapter_node = self._find_chapter_node(chapter, subject)
        grouped: Dict[str, List[dict]] = {"Easy": [], "Medium": [], "Hard": []}

        if not chapter_node or chapter_node not in self.G:
            return grouped

        # Traverse in-edges with type=has_concept or tests_concept to find question nodes
        # Questions map to Concepts, Concepts map to Chapters. 
        # But some questions map directly to Chapters.
        for q_node, _, d in self.G.in_edges(chapter_node, data=True):
            if d.get("type") == "tests_concept":
                node_data = dict(self.G.nodes[q_node])
                self._add_to_grouped(node_data, grouped, limit_per_difficulty, chapter)
        
        for c_node, _, d in self.G.in_edges(chapter_node, data=True):
            if d.get("type") == "has_concept":
                pass # wait, in-edges? No, has_concept is Chapter -> Concept (out_edge)
                
        for _, c_node, d in self.G.out_edges(chapter_node, data=True):
            if d.get("type") == "has_concept":
                for q_node, _, d2 in self.G.in_edges(c_node, data=True):
                    if d2.get("type") == "tests_concept":
                        node_data = dict(self.G.nodes[q_node])
                        self._add_to_grouped(node_data, grouped, limit_per_difficulty, chapter)

        logger.debug(
            f"Related questions for '{chapter}': "
            f"Easy={len(grouped['Easy'])}, "
            f"Medium={len(grouped['Medium'])}, "
            f"Hard={len(grouped['Hard'])}"
        )
        return grouped
        
    def _add_to_grouped(self, node_data, grouped, limit_per_difficulty, chapter):
        if node_data.get("type") != "question":
            return

        diff = node_data.get("difficulty", "Medium")
        if diff not in grouped:
            diff = "Medium"
        if len(grouped[diff]) >= limit_per_difficulty:
            return

        grouped[diff].append({
            "question_number": node_data.get("question_number"),
            "raw_text":        (node_data.get("raw_text") or "")[:300],
            "difficulty":      diff,
            "chapter":         node_data.get("chapter", chapter),
        })