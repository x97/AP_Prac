# PDF mind map audit

- Source: `心理学思维导图.pdf`
- Knowledge DB: `/Users/aa/Documents/AP_psych/data/releases/current/knowledge.db`
- Parser: vector connector endpoints -> label boxes; bold root; BFS tree.
- Unit 1 trees are curated from the PDF hierarchy + Unit 1 knowledge DB + the standard AP scope. Unit 2–5 use parsed trees with description cleanup.
- Unmatched labels stay in the JSON as English-only, non-clickable labels. They are not fabricated concepts.
- This script writes only the JSON and this report; it does not write a Release or the content DB.

## Unit 1 — Biological Bases of Behavior

| Topic | Source | Nodes | Matched |
|---|---|---:|---:|
| 1.1 Interaction of Heredity and Environment | p15 | 25 | 21 |

| 1.2 Overview of the Nervous System | p14, p14 | 25 | 24 |

| 1.3 The Neuron and Neural Firing | p17 | 31 | 27 |

| 1.4 The Brain | p18 | 44 | 40 |

| 1.5 Sleep | p14 | 24 | 21 |

| 1.6 Sensation | p20 | 56 | 45 |

## Unit 2 — Cognition

| Topic | Source | Nodes | Matched |
|---|---|---:|---:|
| 2.1 Perception | p24 | 28 | 21 |

| 2.2 Thinking, Problem-Solving, Judgments, and Decision-Making | p25 | 24 | 20 |

| 2.3 Introduction to Memory | p26 | 22 | 15 |

| 2.4 Encoding Memories | p26 | 9 | 8 |

| 2.5 Storing Memories | p26 | 14 | 12 |

| 2.6 Retrieving Memories | p26 | 16 | 13 |

| 2.7 Forgetting and Other Memory Challenges | p26 | 19 | 16 |

| 2.8 Intelligence and Achievement | p27 | 28 | 23 |

## Unit 3 — Development and Learning

| Topic | Source | Nodes | Matched |
|---|---|---:|---:|
| 3.1 Themes and Methods in Developmental Psychology | p32 | 13 | 11 |

| 3.2 Physical Development Across the Lifespan | p32 | 26 | 22 |

| 3.3 Gender and Sexual Orientation | p32 | 13 | 11 |

| 3.4 Cognitive Development Across the Lifespan | p32 | 19 | 16 |

| 3.5 Communication and Language Development | p32 | 14 | 12 |

| 3.6 Social-Emotional Development Across the Lifespan | p32 | 28 | 25 |
- curated concepts not found in Unit 1 DB: Adolescent egocentrism

| 3.7 Classical Conditioning | p33 | 18 | 15 |

| 3.8 Operant Conditioning | p34 | 28 | 21 |

| 3.9 Social, Cognitive, and Neurological Factors in Learning | p35 | 9 | 9 |

## Unit 4 — Social Psychology and Personality

| Topic | Source | Nodes | Matched |
|---|---|---:|---:|
| 4.1 Attribution Theory and Person Perception | p40 | 25 | 19 |

| 4.2 Attitude Formation and Attitude Change | p41 | 16 | 13 |
- curated concepts not found in Unit 1 DB: Belief perseverance, Confirmation bias

| 4.3 Psychology of Social Situations | p42 | 30 | 28 |

| 4.4 Psychodynamic and Humanistic Theories of Personality | p43, p43 | 27 | 24 |
- curated concepts not found in Unit 1 DB: Person-centered therapy, Unconditional positive regard

| 4.5 Social-Cognitive and Trait Theories of Personality | p43, p43 | 18 | 16 |
- curated concepts not found in Unit 1 DB: Factor analysis, Observational learning, Social-cognitive theory

| 4.6 Motivation | p44 | 22 | 19 |

| 4.7 Emotion | p45 | 14 | 11 |

## Unit 5 — Mental and Physical Health

| Topic | Source | Nodes | Matched |
|---|---|---:|---:|
| 5.1 Introduction to Health Psychology | p51 | 12 | 11 |

| 5.2 Positive Psychology | p51 | 7 | 7 |

| 5.3 Explaining and Classifying Psychological Disorders | p49 | 16 | 13 |
- curated concepts not found in Unit 1 DB: Categories of Disorders, Evolutionary (or Darwinian) Perspective

| 5.4 Selection of Categories of Psychological Disorders | p52 | 55 | 49 |

| 5.5 Treatment of Psychological Disorders | p53 | 27 | 26 |
