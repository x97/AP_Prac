# 393 个 core 概念复核

> 复核基线是 393 条 core。执行三批合并后为 402 条：`In-group bias`、`General intelligence (g)`、`Emotional intelligence`、`Antipsychotic drugs`、`Neuroplasticity`、`Double-blind procedure`、`Percentile rank`、`Phoneme`、`Random sampling` 这 9 个概念原本被拆成 Barron/Myers 两条，合并后恢复跨书身份，因此由 supporting 变为 core。本报告记录复核基线与建议；最终状态（1,105 条概念、209 条关系）见 `concept_audit_postcheck.md`。

## 结论摘要

- 复核基线 core 概念：**393**；权重 ≥70：**119**；权重 <60：**68**。
- **63 个 core 概念没有 core 题**（63 个）。core tier 是“两本教材都覆盖”的课程核心标记，不等于考试高频；不按零 core 题直接降级，避免丢掉跨书覆盖信号。
- 命名问题（基线）：93 个首字母小写；11 组跨章复现/拼写重复（三批执行后共合并 20 组）；8 组真正的同名异义；1 个复合概念 `Amygdala and hippocampus`。
- 复核基线整理 **193** 条关系；三批执行后为 **209** 条：上下位 132，整体-部分 55，相关 14，同名异义 8。
- 高权重概念整体可靠；需要人工注意的是 `Correlation`、`Validity`、`Behavioral perspective` 这类上位 umbrella，应保留为父概念，而不是降级。

## 复核口径

- `weight_tier=core`：Barron 与 Myers 两本书都有对应 KP；这是课程覆盖标记。
- `weight`：由 core/supporting/confusable 题量、跨书、Myers 词表、单元和定义共同决定，反映考试需求。
- 零 core 题但权重 55–60 的 core 概念，多数仍是有教材覆盖的课程概念；报告标为 `curriculum_only`，不自动降级。

## 高权重 core 概念（权重 ≥70）

| 概念 | Unit | 权重 | core题 | confusable | 标记 | 建议 |
|---|---:|---:|---:|---:|---|---|
| Correlation | 0 | 92.2 | 40 | 12 | generic_umbrella,high_weight,has_narrower | keep_umbrella |
| Independent variable | 0 | 90.3 | 38 | 23 | high_weight | keep |
| Mean | 0 | 87.8 | 27 | 18 | high_weight,has_broader | keep |
| Standard deviation | 0 | 87.8 | 34 | 13 | high_weight,has_broader | keep |
| Dependent variable | 0 | 86.7 | 26 | 26 | high_weight | keep |
| Operant conditioning | 3 | 86.6 | 27 | 13 | high_weight,has_broader,has_part | keep |
| Random assignment | 0 | 85.7 | 31 | 20 | high_weight | keep |
| Informed consent | 0 | 84.3 | 24 | 25 | high_weight | keep |
| Operational definitions | 0 | 81.6 | 26 | 4 | curated_rename,high_weight | rename_special |
| Classical conditioning | 3 | 80.0 | 13 | 17 | high_weight,has_broader,has_narrower,has_part | keep |
| Systematic desensitization | 5 | 79.8 | 20 | 12 | high_weight,has_broader,has_whole | keep |
| Positive reinforcement | 3 | 79.7 | 15 | 19 | high_weight,has_broader,has_whole | keep |
| Social facilitation | 4 | 79.5 | 17 | 29 | high_weight | keep |
| Validity | 0 | 79.5 | 14 | 20 | high_weight,has_narrower | keep |
| Longitudinal research | 3 | 78.9 | 17 | 20 | high_weight | keep |
| Median | 0 | 78.7 | 16 | 12 | high_weight,has_broader | keep |
| Fundamental attribution error | 4 | 78.2 | 17 | 23 | high_weight | keep |
| Sympathetic nervous system | 1 | 78.1 | 16 | 11 | high_weight,has_whole | keep |
| reliability | 2 | 78.0 | 16 | 8 | lowercase,high_weight | rename_case |
| Cognitive therapy | 5 | 77.8 | 14 | 9 | high_weight,has_broader | keep |
| Major depressive disorder | 5 | 77.5 | 15 | 14 | high_weight,has_broader | keep |
| Big Five personality traits | 4 | 77.5 | 21 | 1 | high_weight,has_broader | keep |
| Cross-sectional research | 3 | 77.1 | 13 | 24 | high_weight | keep |
| Object permanence | 3 | 77.0 | 15 | 23 | high_weight | keep |
| Observational learning | 3 | 76.9 | 12 | 18 | high_weight,has_broader | keep |
| Mode | 0 | 76.6 | 14 | 9 | high_weight,has_broader | keep |
| Generalization | 3 | 76.4 | 14 | 24 | high_weight,has_whole | keep |
| Obsessive-compulsive disorder (OCD) | 5 | 76.3 | 14 | 22 | high_weight | keep |
| Behavioral Perspective | 0 | 76.2 | 20 | 0 | curated_rename,high_weight | rename_special |
| Case study method | 0 | 76.2 | 20 | 0 | high_weight,has_broader | keep |
| Range | 0 | 76.2 | 14 | 11 | high_weight,has_broader | keep |
| Amygdala and hippocampus | 1 | 76.2 | 17 | 0 | curated_rename,compound,high_weight,has_whole | rename_special,review_split |
| Drive reduction theory | 4 | 76.0 | 15 | 3 | high_weight | keep |
| confirmation bias | 2 | 75.8 | 12 | 11 | lowercase,high_weight | rename_case |
| Naturalistic observation | 0 | 75.7 | 11 | 44 | high_weight,has_broader | keep |
| Self-serving bias | 4 | 75.5 | 12 | 17 | high_weight | keep |
| Cerebellum | 1 | 75.4 | 12 | 28 | high_weight,has_whole | keep |
| Extinction | 3 | 75.1 | 12 | 13 | high_weight,has_whole | keep |
| Negative reinforcement | 3 | 75.1 | 11 | 33 | high_weight,has_broader,has_whole | keep |
| specific phobia | 5 | 75.1 | 11 | 13 | lowercase,high_weight,has_broader | rename_case |
| algorithm | 2 | 75.0 | 14 | 9 | lowercase,high_weight | rename_case |
| Conditioned stimulus (CS) | 3 | 74.7 | 10 | 4 | high_weight | keep |
| Confounding variable | 0 | 74.7 | 13 | 5 | high_weight | keep |
| Statistical significance | 0 | 74.7 | 13 | 5 | high_weight | keep |
| availability heuristic | 2 | 74.6 | 13 | 11 | lowercase,high_weight,has_broader | rename_case |
| Normal curve | 0 | 74.5 | 12 | 4 | high_weight | keep |
| Cognitive dissonance theory | 4 | 74.4 | 15 | 2 | high_weight | keep |
| Mere exposure effect | 4 | 74.4 | 15 | 2 | high_weight,duplicate_target | keep_after_merge:Mere exposure effect (Unit 1) |
| Debriefing | 0 | 74.3 | 11 | 22 | high_weight | keep |
| Cones | 1 | 74.3 | 12 | 1 | high_weight,has_whole | keep |
| Conservation | 3 | 74.1 | 11 | 20 | high_weight | keep |
| Latent learning | 3 | 74.0 | 10 | 17 | high_weight,has_broader | keep |
| Correlation coefficient | 0 | 73.9 | 11 | 6 | high_weight,has_broader | keep |
| Occipital lobes | 1 | 73.9 | 12 | 4 | high_weight,has_whole | keep |
| Modeling | 3 | 73.8 | 9 | 5 | high_weight,duplicate_target | keep_after_merge:Modeling (Unit 5) |
| Self-fulfilling prophecy | 4 | 73.8 | 10 | 14 | high_weight | keep |
| Opponent-process theory | 1 | 73.7 | 12 | 3 | curated_rename,high_weight,homonym_family | rename_special |
| Sensory adaptation | 1 | 73.5 | 11 | 4 | high_weight | keep |
| Group polarization | 4 | 73.5 | 9 | 32 | high_weight | keep |
| Anxiety disorders | 5 | 73.4 | 8 | 1 | high_weight,has_broader,has_narrower | keep |
| serial position effect | 2 | 73.3 | 9 | 6 | lowercase,high_weight | rename_case |
| Parasympathetic nervous system | 1 | 73.0 | 8 | 16 | high_weight,has_whole | keep |
| Deindividuation | 4 | 73.0 | 9 | 25 | high_weight | keep |
| Scatterplot | 0 | 72.7 | 9 | 0 | high_weight | keep |
| Traits | 4 | 72.7 | 7 | 2 | high_weight,has_narrower | keep |
| heuristic | 2 | 72.6 | 6 | 10 | lowercase,high_weight,has_narrower | rename_case |
| generalized anxiety disorder (GAD) | 5 | 72.5 | 9 | 19 | lowercase,high_weight,has_broader | rename_case |
| Critical period | 3 | 72.4 | 10 | 4 | high_weight | keep |
| Projective tests | 4 | 72.4 | 11 | 1 | high_weight | keep |
| Intrinsic motivations | 4 | 72.4 | 10 | 1 | curated_rename,high_weight,has_broader | rename_special |
| Secure attachment | 3 | 72.3 | 9 | 4 | high_weight,has_broader | keep |
| Self-efficacy | 4 | 72.3 | 10 | 9 | high_weight | keep |
| Social loafing | 4 | 72.2 | 9 | 16 | high_weight | keep |
| Circadian rhythm | 1 | 72.2 | 12 | 1 | high_weight | keep |
| Person-centered therapy | 5 | 72.2 | 7 | 7 | high_weight,has_broader | keep |
| encoding | 2 | 72.2 | 8 | 8 | lowercase,high_weight | rename_case |
| predictive validity | 2 | 72.1 | 10 | 8 | lowercase,high_weight,has_broader | rename_case |
| Yerkes-Dodson law | 4 | 72.1 | 10 | 0 | high_weight | keep |
| Egocentric | 3 | 72.0 | 9 | 14 | high_weight | keep |
| Conformity | 4 | 72.0 | 7 | 10 | high_weight | keep |
| Assimilation | 3 | 72.0 | 10 | 7 | high_weight | keep |
| antisocial personality disorder | 5 | 72.0 | 9 | 13 | lowercase,high_weight,has_broader | rename_case |
| Survey method | 0 | 71.9 | 10 | 0 | high_weight | keep |
| Hindsight bias | 0 | 71.8 | 10 | 6 | high_weight | keep |
| misinformation effect | 2 | 71.7 | 9 | 4 | lowercase,high_weight | rename_case |
| Shaping | 3 | 71.6 | 8 | 18 | high_weight,has_whole | keep |
| general adaptation syndrome (GAS) | 5 | 71.6 | 8 | 2 | lowercase,high_weight | rename_case |
| Rational emotive behavior therapy (REBT) | 5 | 71.5 | 10 | 4 | high_weight,has_broader | keep |
| Hypothalamus | 1 | 71.5 | 6 | 16 | high_weight,duplicate_target,has_whole | keep_after_merge:Hypothalamus (Unit 4) |
| difference threshold | 2 | 71.5 | 7 | 6 | lowercase,high_weight,has_broader | rename_case |
| semantic memory | 2 | 71.5 | 9 | 3 | lowercase,high_weight,has_broader | rename_case |
| Flynn effect | 2 | 71.4 | 12 | 0 | high_weight | keep |
| Post-traumatic stress disorder (PTSD) | 5 | 71.4 | 8 | 5 | high_weight,has_broader | keep |
| Frontal lobes | 1 | 71.3 | 8 | 3 | high_weight,has_whole,has_part | keep |
| Norms | 4 | 71.3 | 8 | 3 | high_weight | keep |
| hallucinations | 5 | 71.3 | 7 | 5 | lowercase,high_weight | rename_case |
| Unconditioned stimulus (US or UCS) | 3 | 71.3 | 6 | 10 | high_weight | keep |
| Stress | 5 | 71.3 | 7 | 0 | high_weight | keep |
| Groupthink | 4 | 71.1 | 6 | 36 | high_weight | keep |
| bipolar disorder | 5 | 71.1 | 7 | 9 | lowercase,high_weight,has_narrower | rename_case |
| Extrinsic motivations | 4 | 71.1 | 8 | 2 | curated_rename,high_weight,has_broader | rename_special |
| top-down processing | 2 | 71.1 | 9 | 0 | lowercase,high_weight | rename_case |
| Continuous reinforcement | 3 | 71.0 | 8 | 5 | high_weight,has_whole | keep |
| Homeostasis | 4 | 71.0 | 8 | 5 | high_weight | keep |
| Negatively skewed distribution | 0 | 71.0 | 8 | 5 | high_weight | keep |
| absolute threshold | 2 | 71.0 | 8 | 12 | lowercase,high_weight,has_broader | rename_case |
| Self-actualization | 4 | 70.9 | 8 | 11 | high_weight,duplicate_target | keep_after_merge:Self-actualization (Unit 5) |
| Bystander effect | 4 | 70.8 | 7 | 5 | high_weight | keep |
| hippocampus | 2 | 70.8 | 8 | 1 | lowercase,high_weight,has_whole | rename_case |
| selective attention | 2 | 70.8 | 8 | 1 | lowercase,high_weight | rename_case |
| learned helplessness | 5 | 70.5 | 9 | 3 | lowercase,high_weight | rename_case |
| Somatosensory cortex | 1 | 70.4 | 6 | 8 | high_weight,has_whole | keep |
| Insight learning | 3 | 70.3 | 8 | 6 | high_weight,has_broader | keep |
| Dissociative disorders | 5 | 70.2 | 7 | 2 | high_weight,has_broader,has_narrower | keep |
| depth perception | 2 | 70.2 | 7 | 2 | lowercase,high_weight,has_broader | rename_case |
| short-term memory | 2 | 70.2 | 6 | 9 | lowercase,high_weight,has_broader,has_narrower | rename_case |
| Wernicke’s area | 1 | 70.2 | 6 | 5 | high_weight,has_whole | keep |
| crystallized intelligence | 2 | 70.2 | 7 | 5 | lowercase,high_weight,has_broader | rename_case |
| fluid intelligence | 2 | 70.1 | 6 | 6 | lowercase,high_weight,has_broader | rename_case |

## 零 core 题的 core 概念

这些概念两本书都覆盖，但没有被任何题目标成 core；其中不少在 supporting/confusable 中出现。建议保留 core tier，在排序和复习优先级上按权重处理。

| 概念 | Unit | 权重 | supporting | confusable | 建议 |
|---|---:|---:|---:|---:|---|
| Defense mechanisms | 4 | 60.2 | 20 | 2 | curriculum_only |
| Psychoanalysis (therapy) | 5 | 58.5 | 2 | 8 | curriculum_only,review_qualifier |
| Motor cortex | 1 | 58.1 | 1 | 8 | curriculum_only |
| Frequency theory | 1 | 57.7 | 3 | 2 | curriculum_only |
| Threshold | 1 | 57.6 | 2 | 3 | curriculum_only |
| Motor neurons (efferent neurons) | 1 | 57.4 | 1 | 4 | curriculum_only |
| Rorschach inkblot test | 4 | 57.3 | 6 | 0 | curriculum_only |
| Place theory | 1 | 57.2 | 1 | 3 | curriculum_only |
| Hindbrain | 1 | 57.1 | 5 | 0 | curriculum_only |
| Axon | 1 | 57.1 | 2 | 1 | curriculum_only |
| Personality | 4 | 56.9 | 4 | 0 | downgrade_review |
| Somatic therapies | 5 | 56.9 | 4 | 0 | curriculum_only |
| Insomnia | 1 | 56.9 | 0 | 6 | curriculum_only |
| echoic memory | 2 | 56.9 | 0 | 6 | rename_case,curriculum_only |
| Neurons | 1 | 56.6 | 3 | 0 | curriculum_only |
| Psychoactive drugs | 1 | 56.6 | 3 | 0 | curriculum_only |
| Reflexes | 3 | 56.6 | 3 | 0 | curriculum_only |
| Pupil | 1 | 56.5 | 0 | 4 | curriculum_only |
| Repression | 4 | 56.5 | 0 | 4 | curriculum_only |
| Structured interview | 0 | 56.5 | 0 | 4 | curriculum_only |
| Transcranial magnetic stimulation (TMS) | 5 | 56.5 | 0 | 4 | curriculum_only |
| Discriminative stimulus | 3 | 56.3 | 0 | 3 | curriculum_only |
| Primary reinforcers | 3 | 56.3 | 2 | 0 | curriculum_only |
| convergent thinking | 2 | 56.3 | 0 | 3 | rename_case,curriculum_only |
| All-or-none principle | 1 | 56.1 | 0 | 2 | curriculum_only |
| Cell body (soma) | 1 | 56.1 | 0 | 2 | curriculum_only |
| Computerized axial tomography (CAT or CT) scan | 1 | 56.1 | 0 | 2 | curriculum_only |
| Cornea | 1 | 56.1 | 0 | 2 | curriculum_only |
| Ego | 4 | 56.1 | 0 | 2 | curriculum_only |
| Family therapy | 5 | 56.1 | 0 | 2 | curriculum_only |
| Insight therapies | 5 | 56.1 | 0 | 2 | curriculum_only |
| Forebrain | 1 | 55.9 | 1 | 0 | curriculum_only |
| Id | 4 | 55.9 | 1 | 0 | curriculum_only |
| Theory | 0 | 55.9 | 1 | 0 | downgrade_review |
| Alpha waves | 1 | 55.8 | 0 | 1 | curriculum_only |
| Dendrites | 1 | 55.8 | 0 | 1 | curriculum_only |
| Fetal alcohol syndrome (FAS) | 3 | 55.8 | 0 | 1 | curriculum_only |
| Frustration-aggression hypothesis | 4 | 55.8 | 0 | 1 | curriculum_only |
| Midbrain | 1 | 55.8 | 0 | 1 | curriculum_only |
| Peer review | 0 | 55.8 | 0 | 1 | curriculum_only |
| Self-determination theory | 4 | 55.8 | 0 | 1 | curriculum_only |
| autokinetic effect | 2 | 55.8 | 0 | 1 | rename_case,curriculum_only |
| central executive | 2 | 55.8 | 0 | 1 | rename_case,curriculum_only |
| change blindness | 2 | 55.8 | 0 | 1 | rename_case,curriculum_only |
| phi phenomenon | 2 | 55.8 | 0 | 1 | rename_case,curriculum_only |
| subliminal | 2 | 55.8 | 0 | 1 | rename_case,curriculum_only |
| Association area | 1 | 55.0 | 0 | 0 | curriculum_only |
| Blind sight | 1 | 55.0 | 0 | 0 | rename_special,curriculum_only |
| Collective unconscious | 4 | 55.0 | 0 | 0 | curriculum_only |
| Consciousness | 1 | 55.0 | 0 | 0 | curriculum_only |
| Feature detectors | 1 | 55.0 | 0 | 0 | curriculum_only |
| Genes | 1 | 55.0 | 0 | 0 | curriculum_only |
| Prefrontal lobotomy | 5 | 55.0 | 0 | 0 | curriculum_only |
| Psychosurgery | 5 | 55.0 | 0 | 0 | curriculum_only |
| Relative deprivation theory | 4 | 55.0 | 0 | 0 | curriculum_only |
| Social responsibility norm | 4 | 55.0 | 0 | 0 | curriculum_only |
| Type A | 4 | 55.0 | 0 | 0 | curriculum_only |
| Type B | 4 | 55.0 | 0 | 0 | curriculum_only |
| Wechsler Adult Intelligence Scale (WAIS) | 2 | 55.0 | 0 | 0 | curriculum_only |
| character strengths | 5 | 55.0 | 0 | 0 | rename_case,curriculum_only |
| figure-ground relationship | 2 | 55.0 | 0 | 0 | rename_case,curriculum_only |
| flashbulb memories | 2 | 55.0 | 0 | 0 | rename_special,curriculum_only |
| resilience | 5 | 55.0 | 0 | 0 | rename_case,curriculum_only |

## 命名规范与重复概念

### 首字母小写（建议统一为句首大写）

共 93 个：

- `absolute threshold` → `Absolute threshold`
- `achievement tests` → `Achievement tests`
- `agoraphobia` → `Agoraphobia`
- `algorithm` → `Algorithm`
- `anorexia nervosa` → `Anorexia nervosa`
- `anterograde amnesia` → `Anterograde amnesia`
- `antisocial personality disorder` → `Antisocial personality disorder`
- `aptitude tests` → `Aptitude tests`
- `autism spectrum disorder` → `Autism spectrum disorder`
- `autokinetic effect` → `Autokinetic effect`
- `availability heuristic` → `Availability heuristic`
- `belief perseverance` → `Belief perseverance`
- `binocular depth cues` → `Binocular depth cues`
- `bipolar disorder` → `Bipolar disorder`
- `bottom-up processing` → `Bottom-up processing`
- `bulimia` → `Bulimia`
- `central executive` → `Central executive`
- `change blindness` → `Change blindness`
- `character strengths` → `Character strengths`
- `chunking` → `Chunking`
- `concepts` → `Concepts`
- `confirmation bias` → `Confirmation bias`
- `content validity` → `Content validity`
- `convergence` → `Convergence`
- `convergent thinking` → `Convergent thinking`
- `crystallized intelligence` → `Crystallized intelligence`
- `delusions` → `Delusions`
- `depth perception` → `Depth perception`
- `diathesis-stress model` → `Diathesis-stress model`
- `difference threshold` → `Difference threshold`
- `divergent thinking` → `Divergent thinking`
- `echoic memory` → `Echoic memory`
- `emotion-focused coping` → `Emotion-focused coping`
- `encoding` → `Encoding`
- `episodic memory` → `Episodic memory`
- `explicit memories` → `Explicit memory`
- `factor analysis` → `Factor analysis`
- `figure-ground relationship` → `Figure-ground relationship`
- `flashbulb memories` → `Flashbulb memory`
- `fluid intelligence` → `Fluid intelligence`
- `framing` → `Framing`
- `general adaptation syndrome (GAS)` → `General adaptation syndrome (GAS)`
- `generalized anxiety disorder (GAD)` → `Generalized anxiety disorder (GAD)`
- `gratitude` → `Gratitude`
- `hallucinations` → `Hallucinations`
- `heuristic` → `Heuristic`
- `hippocampus` → `Hippocampus`
- `iconic memory` → `Iconic memory`
- `implicit memories` → `Implicit memory`
- `inattentional blindness` → `Inattentional blindness`
- `intelligence` → `Intelligence`
- `learned helplessness` → `Learned helplessness`
- `long-term memory` → `Long-term memory`
- `long-term potentiation` → `Long-term potentiation`
- `mental age` → `Mental age`
- `mental set` → `Mental set`
- `misinformation effect` → `Misinformation effect`
- `monocular depth cues` → `Monocular depth cues`
- `mood-congruent memory` → `Mood-congruent memory`
- `overconfidence` → `Overconfidence`
- `panic disorder` → `Panic disorder`
- `perceptual set` → `Perceptual set`
- `phi phenomenon` → `Phi phenomenon`
- `post-traumatic growth` → `Post-traumatic growth`
- `predictive validity` → `Predictive validity`
- `proactive interference` → `Proactive interference`
- `recall` → `Recall`
- `recognition` → `Recognition`
- `relearning effect` → `Relearning effect`
- `reliability` → `Reliability`
- `representativeness heuristic` → `Representativeness heuristic`
- `resilience` → `Resilience`
- `retinal disparity` → `Retinal disparity`
- `retrieval` → `Retrieval`
- `retroactive interference` → `Retroactive interference`
- `retrograde amnesia` → `Retrograde amnesia`
- `selective attention` → `Selective attention`
- `semantic memory` → `Semantic memory`
- `sensory memory` → `Sensory memory`
- `serial position effect` → `Serial position effect`
- `short-term memory` → `Short-term memory`
- `signal detection theory` → `Signal detection theory`
- `social anxiety disorder` → `Social anxiety disorder`
- `spacing effect` → `Spacing effect`
- `specific phobia` → `Specific phobia`
- `subjective well-being` → `Subjective well-being`
- `subliminal` → `Subliminal`
- `tend-and-befriend theory` → `Tend-and-befriend theory`
- `therapeutic alliance` → `Therapeutic alliance`
- `top-down processing` → `Top-down processing`
- `visual cliff` → `Visual cliff`
- `visuospatial sketchpad` → `Visuospatial sketchpad`
- `working memory` → `Working memory`

### 需要合并的跨章复现/拼写重复

- `Garcia effect (Unit 4)` → `Garcia effect`：同一概念；Unit 4 是饥饿动机章节的复现
- `Hypothalamus (Unit 4)` → `Hypothalamus`：同一解剖结构；Unit 4 讲饥饿动机时的复现
- `Mere exposure effect (Unit 1)` → `Mere exposure effect`：同一概念；Unit 1 意识章节的复现
- `Modeling (Unit 5)` → `Modeling`：同一概念；Unit 5 治疗章节的复现
- `Perception (Unit 2)` → `Perception`：同一概念；Unit 2 知觉章节的复现
- `Self-actualization (Unit 5)` → `Self-actualization`：同一概念；Unit 5 人本治疗章节的复现
- `Token economy (Unit 3)` → `Token economy`：同一概念；Unit 3 操作性条件作用章节的复现
- `Unconditional positive regard (Unit 4)` → `Unconditional positive regard`：同一概念；Unit 4 人本人格理论章节的复现
- `Determinism (Unit 5)` → `Determinism`：同一哲学概念；Unit 5 治疗章节的复现
- `eclectic (Unit 0)` → `eclectic`：同一概念；Unit 0 总结章节的复现
- `ingroup bias` → `In-group bias`：同一概念，仅连字符/空格写法不同

### 需要限定词的同名异义

- `Accommodation (developmental)` / `Accommodation (sensory)`
- `Autonomy` / `Autonomy (Unit 4)`
- `Discrimination (conditioning)` / `Discrimination (social)`
- `GRIT` / `grit`
- `Opponent-process theory` / `Opponent-process theory (Unit 4)`
- `Proximity` / `Proximity (Unit 2)`
- `Psychoanalysis (therapy)` / `Psychoanalysis (theory)`
- `Similarity (Unit 4)` / `Similarity`

### 特殊改名

- `Operational definitions` → `Operational definition`
- `Behavioral Perspective` → `Behavioral perspective`
- `Amygdala and hippocampus` → `Amygdala`
- `Opponent-process theory` → `Opponent-process theory (color vision)`
- `Intrinsic motivations` → `Intrinsic motivation`
- `Extrinsic motivations` → `Extrinsic motivation`
- `implicit memories` → `Implicit memory`
- `Smell (or Olfaction)` → `Smell (Olfaction)`
- `explicit memories` → `Explicit memory`
- `Social-Cognitive Theory` → `Social-cognitive theory`
- `Blind sight` → `Blindsight`
- `flashbulb memories` → `Flashbulb memory`
- `GRIT` → `GRIT (conflict resolution)`
- `grit` → `Grit (perseverance)`
- `Similarity (Unit 4)` → `Similarity (attraction)`
- `Similarity` → `Similarity (visual)`
- `Proximity` → `Proximity (attraction)`
- `Proximity (Unit 2)` → `Proximity (visual)`
- `Autonomy` → `Autonomy (Erikson)`
- `eclectic` → `Eclecticism`
- `Autonomy (Unit 4)` → `Autonomy (self-determination)`
- `Opponent-process theory (Unit 4)` → `Opponent-process theory (motivation)`

## 上下位 / 整体-部分 / 相关关系

关系按领域分布：

- Unit 0 统计与研究：13 条
- Unit 1 生物基础：35 条
- Unit 2 感觉与知觉：8 条
- Unit 2 智力与思维：4 条
- Unit 2 记忆：18 条
- Unit 3 发展：3 条
- Unit 3 学习：33 条
- Unit 4 人格：2 条
- Unit 4 动机：3 条
- Unit 4 社会心理学：5 条
- Unit 5 治疗：37 条
- Unit 5 障碍：24 条
- 同名异义：8 条

### 高置信度关系（节选）

| 领域 | 关系 | A | B | 说明 |
|---|---|---|---|---|
| Unit 0 统计与研究 | 上下位 | Descriptive statistics | Mean | 平均数是一种描述统计量 |
| Unit 0 统计与研究 | 上下位 | Descriptive statistics | Median | 中位数是一种描述统计量 |
| Unit 0 统计与研究 | 上下位 | Descriptive statistics | Mode | 众数是一种描述统计量 |
| Unit 0 统计与研究 | 上下位 | Descriptive statistics | Range | 全距是一种描述统计量 |
| Unit 0 统计与研究 | 上下位 | Descriptive statistics | Standard deviation | 标准差是一种描述统计量 |
| Unit 0 统计与研究 | 相关 | Descriptive statistics | Normal curve | 正态曲线是描述统计中常用的分布模型 |
| Unit 0 统计与研究 | 相关 | Descriptive statistics | Negatively skewed distribution | 负偏态分布是描述统计中常用的分布形态 |
| Unit 0 统计与研究 | 相关 | Inferential statistics | Statistical significance | 统计显著性用于推断统计的结论判断 |
| Unit 0 统计与研究 | 上下位 | Correlation | Correlation coefficient | 相关系数是相关关系的量化指标 |
| Unit 0 统计与研究 | 上下位 | Validity | Predictive validity | 预测效度是效度的一种 |
| Unit 0 统计与研究 | 上下位 | Validity | Content validity | 内容效度是效度的一种 |
| Unit 0 统计与研究 | 上下位 | Qualitative research | Case study method | 个案研究是质性研究方法 |
| Unit 0 统计与研究 | 上下位 | Qualitative research | Naturalistic observation | 自然观察常用于质性研究 |
| Unit 2 感觉与知觉 | 上下位 | Threshold | Absolute threshold | 绝对阈限是阈限的一种 |
| Unit 2 感觉与知觉 | 上下位 | Threshold | Difference threshold | 差别阈限是阈限的一种 |
| Unit 1 生物基础 | 整体-部分 | Peripheral nervous system (PNS) | Somatic nervous system | 躯体神经系统是外周神经系统的一部分 |
| Unit 1 生物基础 | 整体-部分 | Peripheral nervous system (PNS) | Autonomic nervous system | 自主神经系统是外周神经系统的一部分 |
| Unit 1 生物基础 | 整体-部分 | Autonomic nervous system | Sympathetic nervous system | 交感神经系统是自主神经系统的一部分 |
| Unit 1 生物基础 | 整体-部分 | Autonomic nervous system | Parasympathetic nervous system | 副交感神经系统是自主神经系统的一部分 |
| Unit 1 生物基础 | 整体-部分 | Central nervous system (CNS) | Spinal cord | 脊髓是中枢神经系统的一部分 |
| Unit 1 生物基础 | 整体-部分 | Hindbrain | Cerebellum | 小脑位于后脑 |
| Unit 1 生物基础 | 整体-部分 | Hindbrain | Medulla | 延髓位于后脑 |
| Unit 1 生物基础 | 整体-部分 | Hindbrain | Reticular formation | 网状结构位于后脑/脑干 |
| Unit 1 生物基础 | 整体-部分 | Hindbrain | Pons | 脑桥位于后脑 |
| Unit 1 生物基础 | 整体-部分 | Forebrain | Thalamus | 丘脑位于前脑 |
| Unit 1 生物基础 | 整体-部分 | Forebrain | Hypothalamus | 下丘脑位于前脑 |
| Unit 1 生物基础 | 整体-部分 | Forebrain | Limbic system | 边缘系统位于前脑 |
| Unit 1 生物基础 | 整体-部分 | Forebrain | Cerebral cortex | 大脑皮层位于前脑 |
| Unit 1 生物基础 | 整体-部分 | Limbic system | Amygdala | 杏仁核是边缘系统的一部分 |
| Unit 1 生物基础 | 整体-部分 | Limbic system | Hippocampus | 海马是边缘系统的一部分 |
| Unit 1 生物基础 | 整体-部分 | Limbic system | Hypothalamus | 下丘脑是边缘系统的一部分 |
| Unit 1 生物基础 | 整体-部分 | Cerebral cortex | Frontal lobes | 额叶是大脑皮层的一部分 |
| Unit 1 生物基础 | 整体-部分 | Cerebral cortex | Parietal lobes | 顶叶是大脑皮层的一部分 |
| Unit 1 生物基础 | 整体-部分 | Cerebral cortex | Occipital lobes | 枕叶是大脑皮层的一部分 |
| Unit 1 生物基础 | 整体-部分 | Cerebral cortex | Temporal lobes | 颞叶是大脑皮层的一部分 |
| Unit 1 生物基础 | 整体-部分 | Frontal lobes | Motor cortex | 运动皮层位于额叶 |
| Unit 1 生物基础 | 整体-部分 | Frontal lobes | Broca’s area | 布洛卡区通常位于额叶 |
| Unit 1 生物基础 | 整体-部分 | Parietal lobes | Somatosensory cortex | 躯体感觉皮层位于顶叶 |
| Unit 1 生物基础 | 整体-部分 | Temporal lobes | Wernicke’s area | 韦尼克区通常位于颞叶 |
| Unit 1 生物基础 | 上下位 | Neurons | Sensory neurons (afferent neurons) | 感觉神经元是神经元的一种 |
| Unit 1 生物基础 | 上下位 | Neurons | Motor neurons (efferent neurons) | 运动神经元是神经元的一种 |
| Unit 1 生物基础 | 上下位 | Neurons | Interneurons (association neurons) | 中间神经元是神经元的一种 |
| Unit 1 生物基础 | 上下位 | Psychoactive drugs | Depressants | 抑制剂是精神活性药物的一类 |
| Unit 1 生物基础 | 上下位 | Psychoactive drugs | Stimulants | 兴奋剂是精神活性药物的一类 |
| Unit 1 生物基础 | 上下位 | Psychoactive drugs | Hallucinogens | 致幻剂是精神活性药物的一类 |
| Unit 1 生物基础 | 上下位 | Consciousness | Sleep | 睡眠是一种意识状态 |
| Unit 1 生物基础 | 上下位 | Sleep | REM sleep | REM 睡眠是睡眠的一个阶段 |
| Unit 1 生物基础 | 整体-部分 | Retina | Rods | 视杆细胞位于视网膜 |
| Unit 1 生物基础 | 整体-部分 | Retina | Cones | 视锥细胞位于视网膜 |
| Unit 1 生物基础 | 整体-部分 | Retina | Fovea | 中央凹是视网膜的一部分 |
| Unit 2 感觉与知觉 | 上下位 | Perception | Depth perception | 深度知觉是知觉的一种 |
| Unit 2 感觉与知觉 | 上下位 | Binocular depth cues | Convergence | 辐合是一种双眼深度线索 |
| Unit 2 感觉与知觉 | 上下位 | Binocular depth cues | Retinal disparity | 视网膜像差是一种双眼深度线索 |
| Unit 2 感觉与知觉 | 整体-部分 | Gestalt psychology | Figure-ground relationship | 图形-背景关系是格式塔组织原则之一 |
| Unit 2 感觉与知觉 | 整体-部分 | Gestalt psychology | Proximity (visual) | 接近性是格式塔组织原则之一 |
| Unit 2 感觉与知觉 | 整体-部分 | Gestalt psychology | Similarity (visual) | 相似性是格式塔组织原则之一 |
| Unit 2 记忆 | 上下位 | Memory | Sensory memory | 感觉记忆是记忆的一种 |
| Unit 2 记忆 | 上下位 | Memory | Short-term memory | 短时记忆是记忆的一种 |
| Unit 2 记忆 | 上下位 | Memory | Long-term memory | 长时记忆是记忆的一种 |
| Unit 2 记忆 | 上下位 | Memory | Explicit memory | 外显记忆是记忆的一种 |
| Unit 2 记忆 | 上下位 | Memory | Implicit memory | 内隐记忆是记忆的一种 |
| Unit 2 记忆 | 上下位 | Sensory memory | Iconic memory | 图像记忆是感觉记忆的一种 |
| Unit 2 记忆 | 上下位 | Sensory memory | Echoic memory | 声像记忆是感觉记忆的一种 |
| Unit 2 记忆 | 上下位 | Short-term memory | Working memory | 工作记忆是短时记忆的主动加工模型 |
| Unit 2 记忆 | 上下位 | Long-term memory | Episodic memory | 情景记忆是长时记忆的一种 |
| Unit 2 记忆 | 上下位 | Long-term memory | Semantic memory | 语义记忆是长时记忆的一种 |
| Unit 2 记忆 | 上下位 | Long-term memory | Procedural memory | 程序记忆是长时记忆的一种 |
| Unit 2 记忆 | 上下位 | Explicit memory | Episodic memory | 情景记忆属于外显记忆 |
| Unit 2 记忆 | 上下位 | Explicit memory | Semantic memory | 语义记忆属于外显记忆 |
| Unit 2 记忆 | 上下位 | Implicit memory | Procedural memory | 程序记忆属于内隐记忆 |
| Unit 2 记忆 | 上下位 | Retrieval | Recall | 回忆是提取的一种形式 |
| Unit 2 记忆 | 上下位 | Retrieval | Recognition | 再认是提取的一种形式 |
| Unit 2 记忆 | 上下位 | Interference | Proactive interference | 前摄干扰是干扰的一种 |
| Unit 2 记忆 | 上下位 | Interference | Retroactive interference | 倒摄干扰是干扰的一种 |
| Unit 2 智力与思维 | 上下位 | Intelligence | Crystallized intelligence | 晶体智力是智力的一种 |
| Unit 2 智力与思维 | 上下位 | Intelligence | Fluid intelligence | 流体智力是智力的一种 |
| Unit 2 智力与思维 | 上下位 | Heuristic | Availability heuristic | 可得性启发是启发式的一种 |
| Unit 2 智力与思维 | 上下位 | Heuristic | Representativeness heuristic | 代表性启发是启发式的一种 |
| Unit 3 学习 | 上下位 | Learning | Classical conditioning | 经典条件作用是学习的一种 |
| Unit 3 学习 | 上下位 | Learning | Operant conditioning | 操作性条件作用是学习的一种 |
| Unit 3 学习 | 上下位 | Learning | Observational learning | 观察学习是学习的一种 |
| Unit 3 学习 | 上下位 | Learning | Latent learning | 潜伏学习是学习的一种 |
| Unit 3 学习 | 上下位 | Learning | Insight learning | 顿悟学习是学习的一种 |
| Unit 3 学习 | 上下位 | Classical conditioning | Aversive conditioning | 厌恶条件作用是经典条件作用的一种 |
| Unit 3 学习 | 整体-部分 | Classical conditioning | Acquisition | 习得是经典条件作用的阶段 |
| Unit 3 学习 | 整体-部分 | Classical conditioning | Extinction | 消退是经典条件作用的现象 |
| Unit 3 学习 | 整体-部分 | Classical conditioning | Spontaneous recovery | 自发恢复是经典条件作用的现象 |
| Unit 3 学习 | 整体-部分 | Classical conditioning | Generalization | 泛化是经典条件作用的现象 |
| Unit 3 学习 | 整体-部分 | Classical conditioning | Discrimination (conditioning) | 辨别是经典条件作用的现象 |
| Unit 3 学习 | 整体-部分 | Classical conditioning | Higher-order conditioning | 高级条件作用是经典条件作用的一种程序 |
| Unit 3 学习 | 整体-部分 | Operant conditioning | Positive reinforcement | 正强化是操作性条件作用的程序 |
| Unit 3 学习 | 整体-部分 | Operant conditioning | Negative reinforcement | 负强化是操作性条件作用的程序 |
| Unit 3 学习 | 整体-部分 | Operant conditioning | Punishment | 惩罚是操作性条件作用的程序 |
| Unit 3 学习 | 整体-部分 | Operant conditioning | Shaping | 塑造是操作性条件作用的程序 |
| Unit 3 学习 | 整体-部分 | Operant conditioning | Extinction | 消退是操作性条件作用的现象 |
| Unit 3 学习 | 整体-部分 | Operant conditioning | Generalization | 泛化是操作性条件作用的现象 |
| Unit 3 学习 | 整体-部分 | Operant conditioning | Discrimination (conditioning) | 辨别是操作性条件作用的现象 |
| Unit 3 学习 | 整体-部分 | Operant conditioning | Continuous reinforcement | 连续强化是操作性条件作用的强化程序 |
| Unit 3 学习 | 整体-部分 | Operant conditioning | Fixed-ratio (FR) schedule | 定比强化程序属于操作性条件作用 |
| Unit 3 学习 | 整体-部分 | Operant conditioning | Variable-ratio (VR) schedule | 变比强化程序属于操作性条件作用 |
| Unit 3 学习 | 整体-部分 | Operant conditioning | Fixed-interval (FI) schedule | 定时强化程序属于操作性条件作用 |
| Unit 3 学习 | 整体-部分 | Operant conditioning | Variable-interval (VI) schedule | 变时强化程序属于操作性条件作用 |
| Unit 3 学习 | 上下位 | Reinforcement | Positive reinforcement | 正强化是强化的一种 |
| Unit 3 学习 | 上下位 | Reinforcement | Negative reinforcement | 负强化是强化的一种 |
| Unit 3 学习 | 上下位 | Reinforcement schedule | Fixed-ratio (FR) schedule | 定比程序是强化程序的一种 |
| Unit 3 学习 | 上下位 | Reinforcement schedule | Variable-ratio (VR) schedule | 变比程序是强化程序的一种 |
| Unit 3 学习 | 上下位 | Reinforcement schedule | Fixed-interval (FI) schedule | 定时程序是强化程序的一种 |
| Unit 3 学习 | 上下位 | Reinforcement schedule | Variable-interval (VI) schedule | 变时程序是强化程序的一种 |
| Unit 3 学习 | 上下位 | Reinforcer | Primary reinforcers | 原发性强化物是强化物的一种 |
| Unit 3 学习 | 上下位 | Reinforcer | Secondary reinforcers | 次级强化物是强化物的一种 |
| Unit 3 学习 | 上下位 | Reinforcer | Generalized reinforcer | 概括化强化物是强化物的一种 |
| Unit 4 人格 | 上下位 | Defense mechanisms | Repression | 压抑是防御机制的一种 |
| Unit 3 发展 | 上下位 | Attachment | Secure attachment | 安全型依恋是依恋的一种 |
| Unit 3 发展 | 整体-部分 | Language | Babbling stage | 咿呀语阶段是语言发展的阶段 |
| Unit 3 发展 | 整体-部分 | Language | Telegraphic speech | 电报式言语是语言发展的阶段 |
| Unit 4 社会心理学 | 相关 | Attribution theory | Fundamental attribution error | 基本归因错误是归因理论研究的偏差 |
| Unit 4 社会心理学 | 相关 | Attribution theory | Self-serving bias | 自我服务偏差是归因理论研究的偏差 |
| Unit 4 社会心理学 | 相关 | Attribution theory | Actor-observer bias | 行动者-观察者偏差是归因理论研究的偏差 |
| Unit 4 社会心理学 | 相关 | Conformity | Normative social influence | 规范性社会影响是导致从众的影响之一 |
| Unit 4 社会心理学 | 相关 | Conformity | Informational social influence | 信息性社会影响是导致从众的影响之一 |

其余 73 条见 `concept_relation_candidates.csv`。

## 自动候选中的误报（已剔除）

- `Behavioral Perspective → CBT`：行为主义视角与 CBT 不是上下位。
- `Stress → PTSD`、`Stress → diathesis-stress model`：应激与障碍/模型不是上下位。
- `Hypothesis → Facial feedback hypothesis`、`Hypothesis → Frustration-aggression hypothesis`：假设与具体理论不是上下位。
- `achievement tests → Achievement motivation`、`intelligence → WAIS`、`Personality → Personality inventories`：构念与测量工具不是上下位。
- `Personality disorders → Personality inventories`：障碍与评估工具不是上下位。
- `Discrimination (conditioning) → Discrimination (social)`：这是同名异义，不是上下位。
- `Cognitive therapy → CBT`：方向反了；正确关系是 `CBT → Cognitive therapy`。
- 复数启发式误报：`bias`、`consciousness`、`Cones`、`Big Five personality traits` 等不应因词尾 `s` 自动改名。

## 建议动作

1. **P0 合并重复概念**：`Unit X` 后缀的跨章复现概念并入主概念，避免同一概念被拆成多条、权重被稀释。
2. **P1 修正同名/复合概念**：`Amygdala and hippocampus` → `Amygdala`；`Blind sight` → `Blindsight`；`Smell (or Olfaction)` → `Smell (Olfaction)`；Autonomy/Proximity/Similarity/Opponent-process/GRIT 加限定词。
3. **P2 统一首字母大小写**：所有概念名统一为句首大写，不改动专有名词和缩写。
4. **保留 umbrella**：`Correlation`、`Validity`、`Learning`、`Motivation` 等作为父概念保留；其下位关系写入 `concept_relations`。
5. **不按零 core 题降级**：core tier 继续表示跨书覆盖；考试优先级用 weight 和关系表表达。
