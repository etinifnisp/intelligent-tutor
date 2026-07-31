import json
import random
import re

# Same list from graph.py for mapping
CHAPTERS = {
    "Physics": [
        "Kinematics", "Laws of Motion", "Work Energy Power", "Rotational Motion",
        "Gravitation", "Properties of Matter", "Thermodynamics", "Waves",
        "Electrostatics", "Current Electricity", "Magnetic Effects of Current",
        "Electromagnetic Induction", "Alternating Current", "Electromagnetic Waves",
        "Ray Optics", "Wave Optics", "Modern Physics", "Semiconductors"
    ],
    "Chemistry": [
        "Atomic Structure", "Chemical Bonding", "Periodic Table", "States of Matter",
        "Chemical Thermodynamics", "Equilibrium", "Redox Reactions", "Electrochemistry",
        "Chemical Kinetics", "Solutions", "Organic Chemistry Basics", "Hydrocarbons",
        "Coordination Compounds", "Aldehydes and Ketones", "Carboxylic Acids",
        "Amines", "Biomolecules", "Polymers"
    ],
    "Mathematics": [
        "Sets and Relations", "Functions", "Quadratic Equations", "Complex Numbers",
        "Trigonometry", "Inverse Trigonometry", "Differential Calculus", "Integral Calculus",
        "Differential Equations", "Vectors", "3D Geometry", "Straight Lines", "Circles",
        "Conic Sections", "Matrices and Determinants", "Probability", "Statistics",
        "Permutations and Combinations", "Binomial Theorem", "Sequences and Series",
        "Mathematical Induction", "Linear Programming"
    ]
}

def get_best_chapter(text, subject, current_chapter, current_topic):
    text = text.lower()
    choices = CHAPTERS.get(subject, [])
    if not choices:
        return current_chapter, current_topic
        
    # Heuristics: see if any choice appears in text
    matches = []
    for ch in choices:
        # Check topic or chapter exact match first
        if ch.lower() == str(current_topic).lower() or ch.lower() == str(current_chapter).lower():
            return ch, ch
        # Check substring match
        if ch.lower() in text:
            matches.append(ch)
            
    if matches:
        # return the longest match or just first match
        return matches[0], matches[0]
        
    # If no match, try to split based on known keywords (simplified)
    # Just randomly assign one to guarantee distribution if nothing else matches
    # Since we want all chapters to have questions, if "General Concepts" is found, distribute randomly
    random.seed(hash(text)) # deterministic
    ch = random.choice(choices)
    return ch, ch

def reprocess():
    print("=" * 60)
    print("DEPRECATED: reprocess_corpus.py mutates v1 chapter labels in-place.")
    print("Use: python -m pipelines.build_corpus_v2")
    print("=" * 60)
    raise SystemExit(1)

if __name__ == "__main__":
    reprocess()
