---
name: jee-classifier
description: >
  Classifies JEE question paper content by subject, chapter, topic, 
  question type, and difficulty. Load when parsing or categorising 
  any JEE Main or JEE Advanced question.
---

# JEE Question Classification Skill

## Subject → Chapter mapping (Physics)
Mechanics: kinematics, NLM, WEP, rotational motion, gravitation, SHM, waves
Thermal: thermodynamics, KTG, heat transfer
Electricity: electrostatics, current electricity, magnetism, EMI, AC circuits
Optics: ray optics, wave optics
Modern: photoelectric, nuclear, semiconductors, communication

## Subject → Chapter mapping (Chemistry)
Physical: mole concept, stoichiometry, states of matter, thermodynamics,
          equilibrium, electrochemistry, kinetics, solutions
Inorganic: periodic table, chemical bonding, p-block, d-block, coordination
Organic: GOC, hydrocarbons, functional groups, named reactions, biomolecules

## Subject → Chapter mapping (Mathematics)
Algebra: complex numbers, quadratic, progressions, binomial, matrices, determinants
Calculus: limits, continuity, differentiation, integration, differential equations
Coordinate: straight lines, circles, conics, 3D geometry, vectors
Others: permutations, probability, trigonometry, mathematical reasoning

## Difficulty calibration
Easy: single-concept, direct formula application, seen frequently in NCERT
Medium: two-concept combination, moderate calculation, standard JEE level
Hard: multi-concept, lengthy calculation, unfamiliar application or twist

## Question type detection
MCQ-single: exactly one correct option, +4/-1
MCQ-multiple: one or more correct, +4/−2 partial (JEE Advanced)
Integer: answer is non-negative integer 0–9, no negative marking
Numerical: decimal answer, no negative marking (JEE Main)
Matrix-match: column matching, JEE Advanced specific
Paragraph: comprehension-based, shared stem for 2–3 questions
