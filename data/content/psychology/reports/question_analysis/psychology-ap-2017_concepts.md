# 题目概念关联报告（概念层）

- 生成时间：2026-11-02T14:00:58+08:00
- 试卷：`psychology-ap-2017`
- 模型：`deepseek-flash[1m]`
- Prompt：`question-concept-link-v2`
- 题目：97；失败：0

> 核心概念按“正确选项倒推”生成；干扰项只进入 confusable。
> 写库目标：`question_concept_links`；`question_kp_links` 仅作 legacy 兼容。

| 题号 | 状态 | 核心概念 | 辅助 | 易混淆 | 关键字 | 备注 |
|---:|---|---|---|---|---|---|
| 4 | linked | Random assignment（85.7） | — | Random sampling（B） | control for preexisting differences（未收录）、groups of participants（未收录）、experiment、Random assignment、Random sampling、double-blind design（未收录） | Core is random assignment as the procedure that equates groups on preexisting differences. Random sampling and double-blind are the narrow-domain near-misses; confederate and one-at-a-time are unrelated controls and omitted. |
| 5 | linked | Depressants（65.6） | — | — | reduces the activity of the central nervous system（未收录）、neurotransmitters、gamma-aminobutyric acid (GABA)（未收录）、hippocampus、cerebellum、Alcohol（未收录） | The item tests recognizing alcohol as a depressant that slows CNS activity; GABA is mentioned but the core classification is depressant. |
| 6 | linked | Assimilation（72.0） | — | Accommodation (developmental)（B）、Habituation（D）、Object permanence（E） | Jean Piaget（未收录）、cognitive process（未收录）、assimilation、accommodation、habituation、object permanence | Core is assimilation: Andrea fits a sparrow into her existing bird schema. Accommodation (C04) is the key near-miss; C03 is the sensory lens meaning and is not the relevant distractor here. |
| 7 | linked | Pitch（65.8） | Frequency | Amplitude（B） | pitch、frequency、amplitude、timbre（未收录） | Pitch is the core perceptual concept; frequency is the physical correlate in the correct option. Amplitude/loudness are the closest same-domain confusions. Timbre and complexity are related sound qualities but not close enough to list as confusables. |
| 8 | linked | Hemispheres（28.3） | Hemispheric specialization (brain lateralization) | Medulla（B）、Cerebellum（C）、Endocrine system（D） | damage（未收录）、Right hemisphere（未收录）、Left occipital lobe（未收录）、Medulla、Cerebellum、Endocrine system | The item tests right-hemisphere specialization for visuospatial construction; the correct option names the right hemisphere, mapped to the hemispheres concept (C16), with hemispheric specialization (C54) as supporting context. |
| 9 | linked | Group polarization（73.5） | — | Social loafing（A）、Groupthink（C）、Social facilitation（D）、In-group bias（B） | psychological concepts（未收录）、Group polarization、Social loafing、In-group bias、Groupthink、Social facilitation | The chart itself is not included in the text, but the correct answer identifies group polarization as the tested concept. All distractors are group/social psychology concepts in the same narrow domain, so they are listed as confusables. |
| 10 | linked | Reflexes（56.6） | — | Cerebellum（B）、Hypothalamus（A）、Hippocampus（D） | spinal reflex（未收录）、sensory information（未收录）、brain（未收录） | The item tests the concept of a spinal reflex: an automatic withdrawal that occurs before sensory information reaches the brain. Reflex arcs (C03) support the explanation. Distractors are brain structures that are tempting but not the mechanism. |
| 11 | linked | Mode（76.6） | Descriptive statistics | — | mode、data（未收录） | The item tests identifying the most frequently occurring score (mode). The context mentions self-worth ratings, but that is incidental to the statistical task; no distractor is a near-miss statistical concept, so confusables are empty. |
| 12 | linked | Mean（87.8） | Descriptive statistics | — | mean、data（未收录） | Item asks for the arithmetic average of the ten scores; no distractor is a near-miss statistical concept, so confusables are empty. |
| 13 | linked | Behaviorism（30.0） | — | — | unconscious、hidden motives（未收录）、study behavior directly（未收录）、John Watson（未收录） | Behaviorism (C17) is the core concept; the item tests the behaviorist rejection of unconscious/mentalistic explanation in favor of observable behavior. |
| 14 | linked | Companionate love（30.0） | — | Passionate love（B） | Companionate love、Passionate love、Mere-exposure effect、Cognitive dissonance（未收录）、social psychology | Companionate love is the correct concept: long-term deep affectionate attachment. Passionate love is the only same-domain confusable. Mere-exposure and cognitive dissonance are unrelated distractors, so they are keywords only, not confusables. |
| 15 | linked | Schemata（33.1） | — | Change blindness（A）、Depth perception（B）、Binocular depth cues（E） | Müller-Lyer illusion（未收录）、perceptual hypotheses（未收录）、experiences in their lives（未收录）、change blindness、depth perception、binocular depth cues | The core is that perception is shaped by learned experience (perceptual hypotheses/schemata). The Müller-Lyer and noncarpentered-culture terms support the scenario but are not the tested principle. |
| 16 | linked | Display rules（34.5） | Facial expressions | James-Lange theory（E）、Two-factor theory（E） | display rules、facial expressions、cultures（未收录）、James-Lange theory、Schachter two-factor theory（未收录） | Core is display rules; facial expressions is supporting. James-Lange and two-factor are confusable emotion theories from option E. |
| 17 | linked | Positive psychology（63.0）、Well-being（27.6） | — | External locus of control（A）、Internal locus of control（B） | positive psychology、Perception of control（未收录）、well-being、locus of control、external locus of control、internal locus of control | Core is positive psychology (field named in stem) plus well-being (outcome in correct answer). Locus of control appears only in distractors and is treated as supporting/confusable, not core. |
| 18 | linked | Limbic system（69.4） | Amygdala | — | limbic system、emotions（未收录） | Distractors (logic/reasoning, decision making, auditory comprehension, sensory sensitivity) are loosely related brain functions, not narrow-domain near-misses, so no confusables are listed. |
| 19 | linked | Reliability（78.0） | Test-retest reliability | Validity（B）、Standardization（C） | assessment instrument（未收录）、same sample again（未收录）、Reliability、Validity、Standardization | Repeated administration of the same instrument to the same sample is the classic test-retest reliability procedure; the core concept is reliability, with test-retest reliability as supporting detail. |
| 20 | linked | Delusions（69.9） | Positive symptoms、Schizophrenia | Flat affect（A） | positive symptom（未收录）、schizophrenia、Delusions、Flat affect | Delusions are the positive symptom; flat affect is a negative symptom distractor. Difficulty reading emotions and attention problems are not positive symptoms. |
| 21 | linked | Obedience（67.3） | — | Conformity（A）、Deindividuation（C） | Stanley Milgram's experiment（未收录）、Obedience、Conformity、Deindividuation | Milgram's shock study is the classic demonstration of obedience to authority; conformity and deindividuation are the closest social-psychology distractors. |
| 22 | linked | Cognitive map（69.8） | Latent learning | Higher-order conditioning（A）、Observational learning（D）、Assimilation（E） | experiment、rats learned to navigate a maze（未收录）、food reward（未收录）、cognitive mapping（未收录） | The item tests cognitive map (C04) as the mental representation of the maze layout revealed once reward was given; latent learning (C08) is a plausible supporting concept but is not named in the question. |
| 23 | linked | Behavioral perspective（76.2） | — | — | systematic desensitization、phobia（未收录）、Behavioral（未收录） | The item asks which treatment approach explains systematic desensitization; the correct answer is the behavioral perspective, with systematic desensitization as the technique being explained. |
| 24 | linked | Representative sample（37.6） | Random sampling | Convenience sampling（B） | generalizable（未收录）、representative sample、small convenience sample（未收录）、self-report surveys（未收录）、double-blind procedure、experiment | Generalizability depends on a representative sample; random sampling (C37) is a related supporting mechanism. Double-blind and experiment distractors address bias/causation, not generalizability. |
| 25 | linked | Hypothalamus（76.9） | — | Hippocampus（A）、Medulla（B）、Amygdala（C） | pituitary gland（未收录）、hypothalamus | The item tests knowledge that the hypothalamus controls the pituitary gland and thus the endocrine system. The pituitary gland itself is not in the candidate list, so it is marked null. |
| 26 | linked | Down syndrome（20.0） | Chromosomal abnormality | — | extra copy of chromosome 21（未收录）、Down syndrome、Tourette's disorder（未收录）、Autism spectrum disorder、Parkinson's disease（未收录）、Phenylketonuria (PKU)（未收录） | Core is Down syndrome, defined by the extra copy of chromosome 21. Distractors are other disorders; only chromosomal conditions are near-miss confusables. |
| 27 | linked | Person-centered therapy（72.2） | Unconditional positive regard | Family therapy（D）、Flooding（A） | therapeutic technique（未收录）、patient should determine the course of therapy（未收录）、person-centered therapy、flooding、rational-emotive behavior therapy、family therapy | Logotherapy (option C) is not in the candidate list, so it is omitted from confusables. Core is person-centered therapy, which emphasizes client-directed course of therapy. |
| 28 | linked | Temperament（66.6） | — | Object permanence（E） | infant's individual style of interacting with the world（未收录）、Temperament、Object permanence | Temperament is the term for an infant's characteristic emotional reactivity and style of interacting with the world. Object permanence is a related infant cognitive milestone but does not describe interaction style. |
| 29 | linked | Id（55.9） | — | Superego（C） | Sigmund Freud's theory of personality（未收录）、id、More, more, more!（未收录） | The id's demand for immediate gratification is captured by the correct option; superego and ego options serve as same-domain confusables. |
| 30 | linked | Central route to persuasion（69.2） | Persuasion | Groupthink（B）、Door-in-the-face technique（C）、Self-serving bias（D）、Algorithm（E） | central route to persuasion、explain（未收录）、groupthink、door-in-the-face technique、self-serving bias、algorithm | Katie presents detailed factual arguments, indicating deep processing of message content characteristic of the central route to persuasion. |
| 31 | linked | Positive reinforcement（79.7） | Reinforcement | Negative reinforcement（C）、Punishment（A） | positive reinforcement、negative reinforcement、punishment、primary reinforcement（未收录）、attention（未收录） | Attention from the teacher is added after misbehavior and the behavior increases, so it functions as positive reinforcement. Differential reinforcement (D) is a loosely related distractor and was omitted as a confusable. |
| 32 | linked | Habituation（30.0） | — | Sensory adaptation（A）、Generalization（D）、Transference（E） | repeatedly shown an object（未收录）、spend less time looking at the object（未收录）、heart rates and respirations decrease（未收录）、habituation、sensory adaptation、dishabituation（未收录）、generalization、transference | Dishabituation (option C) is a valid near-miss but has no candidate key, so it is recorded as a keyword with concept=null. Supporting C09 is a weak fit; the core is clearly C01. |
| 33 | linked | Linguistic determinism（30.0） | — | Critical period（D） | linguistic determinism、Benjamin Whorf（未收录）、language | Core is Whorf's linguistic determinism; linguistic relativity (C06) is a near-synonym supporting concept. Distractors C and D reflect nativist/critical-period accounts, not the tested concept. |
| 34 | linked | Algorithm（75.0） | — | Heuristic（B）、Insight（E） | systematically tries every possible solution（未收录）、algorithm、heuristic、insight | The core concept is algorithm, defined as a step-by-step method that guarantees a solution. Heuristic and insight are included as confusables because they are alternative problem-solving strategies in the same domain. |
| 35 | linked | Social facilitation（79.5） | Social impairment | Social loafing（E）、Conformity（A）、Obedience（B） | social psychology principles（未收录）、performance（未收录）、large crowd of attendees（未收录）、Social facilitation、Social impairment、Social loafing、Conformity、Obedience | The stem describes improved performance in front of a large audience, matching social facilitation. Social impairment is the closest near-miss (audience effect in the opposite direction) and is included as supporting because the stem contrasts average practice performance with exceptional competition performance. |
| 36 | linked | Continuous reinforcement（71.0） | — | — | loves to read（未收录）、do nothing additional（未收录）、gold star（未收录） | The item tests intrinsic motivation and overjustification: because Shaniqua already reads for enjoyment, adding external rewards could undermine intrinsic interest, so no additional reinforcement is best. Continuous reinforcement (C01) is the closest candidate but is imperfect; the concept base lacks an intrinsic motivation/overjustification key. |
| 37 | linked | Imprinting（61.6） | — | Secure attachment（E）、Object permanence（B）、Observational learning（C）、Accommodation (developmental)（D） | Konrad Lorenz（未收录）、gosling（未收录）、follow the first large moving object it sees（未收录）、imprinting、object permanence、observational learning、accommodation、secure attachment | Imprinting is the clear core concept; attachment is a supporting related bond concept. Accommodation in option D is treated as the developmental sense (C06), not the sensory lens sense. |
| 38 | linked | Intrinsic motivation（72.4） | Motivation | Extrinsic motivation（A）、Achievement motivation（C）、Belongingness（E） | enjoys running（未收录）、intrinsic motivation、extrinsic motivation、achievement motivation、a need for affiliation（未收录）、a need for belongingness（未收录） | The stem's 'because she enjoys running' signals an internal reward, making intrinsic motivation the core. Extrinsic motivation is the strongest confusable; achievement, affiliation, and belongingness are plausible social-motive near-misses. |
| 39 | linked | Amygdala（76.2） | — | Cerebellum（C）、Medulla（D）、Reticular formation（E）、Cerebral cortex（A） | brain structures（未收录）、emotion、fear（未收录）、Amygdala | Core concept is amygdala as the emotion/fear center; emotion is a supporting concept. Distractors are other brain structures in the same domain. |
| 40 | linked | Antipsychotic drugs（70.2） | — | Psychoanalysis (therapy)（A）、Rational emotive behavior therapy (REBT)（E） | most effective treatment（未收录）、schizophrenia、Antipsychotic medications、Psychoanalysis、Insight therapy（未收录）、Rational emotive behavior therapy | Antidepressant medications (C20) is a distractor but not a near-miss in the same narrow domain as antipsychotics; omitted from confusables. |
| 41 | linked | Attribution theory（68.8）、Situation attribution（34.5） | — | Fundamental attribution error（C） | Stanford prison simulation（未收录）、situational factors（未收录）、personality factors（未收录） | The item tests situational vs. dispositional attribution (attribution theory) applied to Zimbardo's prison study; the correct option is a situation attribution. |
| 42 | linked | Hypothalamus（76.9） | — | Hippocampus（A）、Medulla（B）、Corpus callosum（D） | hunger（未收录）、satiety（未收录）、brain structures（未收录）、Hypothalamus、Hippocampus、Medulla、Occipital cortex（未收录）、Corpus callosum | Core is hypothalamus (C01). Supporting concepts C06 (ventromedial/satiety center) and C21 (lateral/hunger center) are hypothalamic subregions that explain the hunger/satiety link but are not named in the question. Confusables are the other named brain structures in the options. |
| 43 | linked | Scatterplot（72.7） | Correlation coefficient | — | scatterplots（未收录）、strongest relation（未收录） | Item tests reading scatterplots to judge correlation strength; correlation coefficient is the underlying statistic but not named in the stem. |
| 44 | linked | Organizational psychology（25.0）、Intrinsic motivation（72.4） | — | — | motivation、job satisfaction（未收录）、redesign jobs（未收录）、responsibility and flexibility（未收录） | Item tests organizational psychology's job enrichment/redesign as a route to satisfaction and performance, with intrinsic motivation as a supporting mechanism. Distractors A and E reflect operant reward/punishment strategies. |
| 45 | linked | Occipital lobes（73.9） | Accidents | Hippocampus（C） | head trauma（未收录）、unable to see（未收录）、occipital lobe（未收录）、parietal lobe（未收录）、hippocampus、Wernicke's area、Broca's area | The item tests localization of visual processing to the occipital lobe; the stem's 'eyes functioning normally' rules out peripheral causes and points to cortical damage. |
| 46 | linked | Drive reduction theory（76.0） | Homeostasis | Instincts（A）、Incentive（B）、Hierarchy of needs（C）、Arousal theory（D） | Homeostasis、motivation theory（未收录）、Drive-reduction theory、Instinct theory（未收录）、Incentive theory（未收录）、Hierarchy of needs、Arousal theory | Homeostasis is the key term linking to drive-reduction theory; the other options are rival motivation theories. |
| 47 | linked | Procedural memory（38.6） | Implicit memory | — | play the violin（未收录）、from memory（未收录）、does not remember learning（未收录）、Procedural（未收录） | Procedural memory is the tested concept; implicit memory supports why Matthew cannot consciously recall learning the skill. |
| 48 | linked | External locus of control（68.3） | Locus of control | Internal locus of control（C）、Self-serving bias（E） | lucky（未收录）、External locus of control、Internal locus of control、Self-serving bias | The stem's 'because he was lucky' directly signals external locus of control. Positive psychology and humanistic psychology are unrelated distractors and omitted from confusables. |
| 49 | linked | Similarity (visual)（26.6） | Gestalt psychology | Proximity (visual)（A）、Closure（C） | Gestalt principles（未收录）、Similarity、Proximity、Closure、Good continuation（未收录） | Core is the Gestalt similarity grouping principle; Gestalt psychology is supporting context. Common fate (E) is a motion-based grouping principle but not in the candidate list, so omitted from confusables. |
| 50 | linked | Critical period（72.4） | — | Linguistic determinism（C）、Temperament（A） | critical periods（未收录）、deprived of language exposure（未收录）、linguistic determinism、temperament | The case study is the vehicle, but the tested concept is the critical period for language acquisition. Case study method (C01) is mentioned only implicitly and is not the answer. |
| 51 | linked | Attribution（26.1） | — | — | explanation（未收录）、attribution、nice person（未收录）、belief in a just world（未收录）、stereotype、social facilitation | The item tests the general definition of an attribution as an explanation of cause; the dispositional flavor of Julie's explanation supports but is not required. |
| 52 | linked | Personality disorders（68.1） | Cluster C | — | personality disorders、Dependent（未收录）、defers to the wishes of others（未收录） | Dependent personality disorder is not a separate candidate concept; it is represented under the broader personality disorders concept (C01) and Cluster C (C05). |
| 53 | linked | Psychodynamic Perspective（37.9） | — | — | unconscious thoughts and desires（未收录）、psychological approaches（未收录）、Psychodynamic（未收录） | Core concept is the psychodynamic perspective (C09), supported by the unconscious concept (C01). Confusables are the other major psychological perspectives listed as options. |
| 54 | linked | Sympathetic nervous system（78.1） | Autonomic nervous system | — | pupils become dilated（未收录）、digestion is reduced（未收录）、skin becomes cold（未收录）、Sympathetic（未收录）、Parasympathetic（未收录）、Central（未收录）、Somatic（未收录）、Endocrine（未收录） | The arousal signs (dilated pupils, reduced digestion, cold skin) are sympathetic nervous system activation. Autonomic nervous system is a valid supporting concept because the sympathetic division is part of it. |
| 55 | linked | Bystander effect（70.8） | Diffusion of responsibility、Bystander intervention | — | prosocial behavior、crowded farmers market（未收录）、empathy（未收录）、distress（未收录） | The correct answer (crowded market) illustrates the bystander effect: more witnesses reduce helping. Diffusion of responsibility is a supporting explanation. Options A and C are tempting because they reference helping-related norms but would increase helping. |
| 56 | linked | Positively skewed distribution（33.5）、Mean（87.8） | Median | Normal curve（C）、Range（A）、Standard deviation（B） | mean、median、positively skewed（未收录）、normal（未收录）、standard deviation、range | Core is positively skewed distribution; the mean-median comparison is the reasoning that identifies it. Negative skew (C08) is not literally named in option D but is the direct opposite concept and a common confusion. |
| 57 | linked | Projection（35.5） | Defense mechanisms | Displacement（A）、Regression（B）、Rationalization（D）、Sublimation（E） | defense mechanism（未收录）、criticize other people for being dependent and lazy（未收录）、Projection | Projection is the core: Colleen attributes her own dependency to others. Defense mechanisms is supporting context. Distractors are other defense mechanisms, so they are confusables. |
| 58 | linked | Scapegoat theory（30.0） | Prejudice | — | scapegoat theory、prejudice、blame others（未收录） | Scapegoat theory is the tested concept; prejudice is a supporting concept embedded in the correct option. Distractors A, B, D, and E map to other social-psychology concepts and are treated as confusables. |
| 59 | linked | Learned helplessness（70.5） | — | Stress（B）、Self-esteem（D）、REM sleep（A） | positive correlation、Perceived lack of control（未收录）、learned helplessness、Stress、Self-esteem、REM sleep | The item tests recognizing a positive correlation; the correct pairing is perceived lack of control with learned helplessness. Other options are negative correlations. |
| 60 | linked | Somatic therapies（56.9） | — | — | major depressive disorder、medication（未收录）、serotonin（未收录）、norepinephrine（未收录）、Biological（未收录） | Core is the biological/somatic approach to depression, evidenced by the medication altering serotonin or norepinephrine. Antidepressant drugs (C07) and major depressive disorder (C01) are supporting context. Serotonin and norepinephrine are key stem terms without a dedicated candidate concept. |
| 61 | linked | Classical conditioning（80.0） | Aversive conditioning | Biological preparedness（B）、Punishment（D） | Little Albert（未收录） | Little Albert is the classic demonstration of classical conditioning of fear; aversive conditioning is a related supporting concept. |
| 62 | linked | Intimacy（30.0） | Erikson's psychosocial stage theory | Identity（D） | Erik Erikson（未收录）、early adulthood（未收录）、life partner（未收录）、psychosocial stage of development（未收录）、intimacy versus isolation（未收录）、identity versus role confusion（未收录）、generativity versus stagnation（未收录） | Core is the intimacy versus isolation stage; Erikson's psychosocial stage theory is supporting context. Generativity (option A) has no exact candidate key, so it is left null in keywords. |
| 63 | linked | Conservation（74.1） | — | Egocentric（A）、Object permanence（C） | conservation、tall, thin container（未收录）、egocentrism、object permanence、Jean Piaget（未收录） | The item tests Piaget's conservation concept: understanding that liquid quantity stays the same despite a change in container shape. Egocentrism and object permanence are same-domain Piaget distractors. |
| 64 | linked | Optic nerve（30.0） | — | Feature detectors（A）、Rods（E）、Cones（E） | visual information processing（未收录）、Feature detectors、retina、rods and cones（未收录）、ganglion cells（未收录）、optic nerve、Rods、cones | Core is the optic nerve pathway from bipolar to ganglion cells. Feature detectors, rods, and cones are distractors in the same visual-sensation domain. |
| 65 | linked | Dopamine hypothesis（33.3） | Schizophrenia | — | dopamine hypothesis、schizophrenia、spinal cord、peripheral nervous system | Core is the dopamine hypothesis (excess dopamine linked to schizophrenia). Spinal cord and PNS appear only in distractors and are treated as confusables, not core. |
| 66 | linked | Activation-synthesis theory of dreaming（26.7） | Dreams | — | dream、random stimulation from the brain stem（未收录）、Activation-synthesis（未收录） | The stem paraphrases activation-synthesis theory: dreams are the brain's attempt to interpret random brain-stem stimulation. Wish fulfillment is the only distractor in the same narrow domain (dream theories); the others are unrelated. |
| 67 | linked | Normal curve（74.5）、Standard deviation（87.8） | z-scores | — | normal（未收录）、standard deviation、percentage（未收录） | Item requires applying the normal curve's known area (about 68% within one SD, about 95% within two SDs) to find the percentage between 50 and 80; standard deviation and normal curve are the tested concepts. |
| 68 | linked | Emotional intelligence（55.8） | — | — | multiple intelligences、Howard Gardner（未收录）、emotional intelligence、Intrapersonal（未收录）、Kinesthetic（未收录）、Naturalist（未收录）、Spatial（未收录）、Linguistic（未收录） | Core is emotional intelligence (C02); intrapersonal intelligence (C06) is the correct-answer concept that operationalizes it. Interpersonal intelligence (C57) is the strongest confusable but is not an option here, so it is listed only as a conceptual near-miss. |
| 69 | linked | Standardization（30.0） | — | — | standardized tests（未收录）、administered and scored in a consistent manner（未收录）、administered individually（未收录）、projective（未收录） | Standardization is the tested concept; reliability/validity are related but not the answer here. |
| 70 | linked | Fixed-ratio (FR) schedule（64.3） | — | — | reinforcement schedules（未收录）、Fixed ratio（未收录）、Fixed interval（未收录）、Variable ratio（未收录）、Variable interval（未收录）、Continuous（未收录） | The stem describes reinforcement after a set number of responses (twenty phones), which is a fixed-ratio schedule. Time-based and variable schedules are the near-miss distractors. |
| 71 | linked | Validity（79.5） | — | — | validity、hypnosis、psychiatric disorders（未收录）、empirical support（未收录）、efficacy（未收录）、negative bias（未收录） | Validity is the tested concept: the item asks what undermines the validity of hypnosis as a treatment, and the correct answer (lack of empirical support) is the validity threat. Hypnosis is the treatment context; evidence-based practice is a supporting link. |
| 72 | linked | Wernicke’s area（70.2） | — | Motor cortex（A）、Somatosensory cortex（D） | comprehending the meaning of words（未收录）、Wernicke's area、traumatic injury（未收录）、motor cortex、Suprachiasmatic nucleus、somatosensory cortex、reticular formation | Wernicke's area is the core because the stem describes impaired language comprehension. Broca's area is not an option but is the most likely confusable concept; among listed options, motor cortex and somatosensory cortex are the nearest same-domain distractors. |
| 73 | linked | Secondary reinforcers（69.0） | Reinforcer | Primary reinforcers（D）、Unconditioned stimulus (US or UCS)（A）、Unconditioned response (UR or UCR)（B）、Conditioned response (CR)（C） | star（未收录）、behaves well（未收录）、prize（未收录）、secondary reinforcer（未收录）、primary reinforcer、unconditioned stimulus、unconditioned response、conditioned response | The star functions as a learned reinforcer exchanged for a prize, so the core is secondary reinforcer. Token economy is a plausible supporting link because stars act like tokens, but it is not required to answer. |
| 74 | linked | Conversion disorder（28.3） | — | Panic disorder（A）、Bipolar disorder（B）、Tardive dyskinesia（D）、Schizophrenia（E） | Conversion disorder、lost his ability to see（未收录）、unable to find a biological reason（未收录）、witnessed a burglary（未收录）、Panic disorder、Bipolar disorder、Tardive dyskinesia、Schizophrenia | Core is conversion disorder: loss of a physical function (blindness) with no biological explanation following psychological stress. Supporting trauma-and-stressor-related disorders reflects the upsetting burglary witness context. Confusables are the other disorder options in the same DSM-category domain. |
| 75 | linked | Naturalistic observation（75.7） | — | — | naturalistic observation、artificiality（未收录）、laboratory studies（未收录） | The strength tested is that naturalistic observation reduces artificiality compared with lab settings; wrong options describe strengths of experiments or quantitative methods. |
| 76 | linked | Generalization（76.4） | Taste aversion | Extinction（B）、Spontaneous recovery（C）、Shaping（A）、Latent learning（E） | stimulus generalization（未收录）、nauseous（未收录）、extinction、spontaneous recovery、shaping、latent learning | The item tests stimulus generalization: Tyler's nausea conditioned to one fast-food meal now generalizes to all fast food. Taste aversion (C04) is a supporting concept explaining the initial conditioning, but the correct answer is generalization. |
| 77 | linked | Flynn effect（71.4） | IQ | Head Start（C） | Flynn effect、Intelligence quotient (IQ) scores（未收录）、Head Start、statistically significant（未收录） | The Flynn effect is the generational rise in IQ scores; option A captures higher scores across a decade, while C describes a program effect and D a null relationship. |
| 78 | linked | Cocktail party effect（29.8） | Selective attention | Sensory adaptation（C）、Bottom-up processing（D） | attention（未收录）、cocktail party effect、sensory adaptation、bottom-up processing、just-noticeable difference（未收录） | The item tests the cocktail party effect: important or personally relevant auditory stimuli capture attention. Selective attention is a related supporting concept. |
| 79 | linked | Deep processing（30.0） | — | Shallow processing（A）、Shallow processing（C）、Shallow processing（E） | levels of processing（未收录）、recall、Counting the number of syllables（未收录）、Mentally spelling（未收录）、rhymes（未收录） | Core is deep processing (semantic encoding by meaning), which the correct option exemplifies; levels of processing model is the supporting framework. Shallow processing is the confusable near-miss for the structural/phonological distractors. |
| 80 | linked | Conformity（72.0） | Obedience | Social facilitation（C）、Social loafing（E） | Compliance（未收录）、asked Shelby to step aside（未收录）、moved out of the way（未收录）、Social facilitation、Social loafing | The correct answer 'Compliance' is not present as a candidate concept; the closest candidate is Conformity (C21), which is a near-miss rather than an exact match. Core is therefore marked with reduced confidence and the correct-option keyword is left unlinked (concept=null). |
| 81 | linked | Big Five personality traits（77.5） | Traits | — | Big Five personality factors（未收录）、psychological perspective（未收录）、Trait psychology（未收录） | Core is the Big Five trait model; trait psychology is the perspective that grounds it. |
| 82 | linked | Encoding（72.2） | — | Retroactive interference（A）、Proactive interference（B）、Source amnesia（C）、Retrieval（E） | attention is focused（未收录）、unable to recall（未收录）、encoding failure（未收录）、retroactive interference、proactive interference、source amnesia、retrieval failure（未收录） | Caleb never encoded the short story because attention was on the history project, so the recall problem is encoding failure rather than interference or retrieval failure. |
| 83 | linked | Unconditioned stimulus (US or UCS)（71.3） | Classical conditioning | Conditioned stimulus (CS)（A）、Conditioned response (CR)（B）、Unconditioned response (UR or UCR)（D） | Ivan Pavlov's classical conditioning paradigm（未收录）、salivated in response to the food（未收录）、unconditioned stimulus | The item tests identifying the food as the unconditioned stimulus that naturally elicits salivation before any conditioning. |
| 84 | linked | Projective tests（72.4） | — | — | personalities（未收录）、draw pictures（未收录）、drawings will reveal underlying personality characteristics（未收录）、Psychoanalytic（未收录） | Projective tests are the core concept; psychoanalytic theory is the supporting framework. Distractors are other personality perspectives. |
| 85 | linked | Cognitive therapy（77.8） | Cognitive restructuring | — | therapy（未收录）、changing a behavior（未收录）、maladaptive thinking（未收录）、Cognitive（未收录） | The stem describes cognitive therapy's focus on changing maladaptive thinking to alter behavior; cognitive restructuring is the supporting mechanism. |
| 86 | linked | Mental set（67.0） | — | Accommodation (developmental)（A）、Object permanence（B）、Conservation（C）、Divergent thinking（E） | mental set、door opening（未收录）、pulling on the handle（未收录）、Accommodation、Object permanence、Conservation、Divergent thinking | The item tests mental set: Raj persists with a previously successful door-opening approach despite it failing. Accommodation (C07) is the developmental sense, not the sensory-lens sense (C06). |
| 87 | linked | Sensory adaptation（73.5） | — | Subliminal（D） | sensory adaptation、no longer notices the strong smell of garlic（未收录）、smell of garlic（未收录）、subliminal perception（未收录）、just-noticeable difference（未收录） | Core is sensory adaptation; smell is supporting context. Subliminal perception and just-noticeable difference are the nearest threshold-related distractors. |
| 88 | linked | Learning（68.3） | — | — | Quickly learning（未收录）、seventy-year-old（未收录）、cognitive tasks（未收录） | The item tests age-related decline in new learning (fluid ability) versus preserved crystallized memory. No candidate directly names crystallized/fluid intelligence, so only Learning is core. |
| 89 | linked | Latent learning（74.0）、Cognitive map（69.8） | — | — | latent learning、cognitive maps（未收录）、Edward Tolman（未收录） | Item tests identification of Tolman as pioneer of latent learning and cognitive maps; both core concepts are named in the stem. |
| 90 | linked | Aptitude tests（66.4） | — | Achievement tests（A）、Intelligence test（C）、Personality inventories（D） | potential ability（未收录）、aptitude test、achievement test、intelligence test、personality inventory | Core is aptitude tests (C01), directly matching 'potential ability.' Achievement tests (C03) is the primary near-miss distractor; intelligence test (C04) and personality inventory (C07) are secondary test-type confusables. Interest inventory (E) has no candidate concept and is omitted. |
| 91 | linked | Post-traumatic stress disorder (PTSD)（71.4）、Trauma-and-stressor-related disorders（30.0） | Personality disorders | Specific phobia（A）、Major depressive disorder（B） | psychological disorders、classification（未收录）、posttraumatic stress（未收录）、trauma- and stressor-related disorders、specific phobia、schizophrenia spectrum and other psychotic disorders（未收录）、major depressive（未收录）、personality disorders、obsessive-compulsive（未收录）、depressive disorders、conversion（未收录） | The item tests matching disorders to DSM-5 categories; the core is PTSD paired with trauma- and stressor-related disorders. Wrong options are confusable because each names a real disorder with a plausible but incorrect category. |
| 92 | linked | Decay（29.5） | — | — | Hermann Ebbinghaus（未收录）、memory、nonsense syllables（未收录）、graphs（未收录）、forgetting（未收录）、time（未收录） | The item tests Ebbinghaus's forgetting curve (decline of retention over time), best captured by decay among candidates; scatterplot and relearning are the closest near-miss distractors. |
| 93 | linked | Smell (Olfaction)（65.4）、Sensory interaction（30.0） | Gustation | Five different types of tastes（D）、Taste buds（E） | perception of taste（未收录）、sense of smell（未收录）、flavor of food（未收录）、taste differences（未收录）、basilar membrane（未收录）、five primary taste qualities（未收录）、Taste receptors（未收录） | Core is smell/olfaction (C02) with sensory interaction (C10) as the mechanism linking smell to flavor perception. C01 and C06 are confusable near-misses from wrong options D and E. |
| 94 | linked | Iconic memory（61.6） | Sensory memory | — | glances at a graph（未收录）、less than a second later（未收录）、immediately remember（未收录）、Iconic（未收录）、Echoic（未收录）、Procedural（未收录）、Declarative（未收录）、Implicit（未收录） | Core is iconic memory: brief visual sensory memory lasting less than a second. Supporting sensory memory frames the stage. Distractors are other memory types, so they are confusable only as near-miss memory categories. |
| 95 | linked | Confirmation bias（75.8） | — | Self-serving bias（D）、Functional fixedness（E） | confirmation bias、strongly opposed to video game use（未收录）、the dangers of video games（未收录）、self-serving bias、functional fixedness、insight | The item tests confirmation bias: Mikayla selectively searches for and accepts information that confirms her preexisting opposition to video games. Self-serving bias and functional fixedness are the closest same-domain distractors (other biases/thinking obstacles). |
| 96 | linked | Experiment（30.0） | — | Naturalistic observation（B）、Case study method（D） | randomly assigned（未收录）、Experimental（未收录）、Correlational（未收录）、Naturalistic observation、Case study | The scenario describes an experiment because the researcher manipulates cell phone use and randomly assigns participants. Random assignment is a supporting concept. Participant observation (A) is not in the candidate list and is only loosely related, so it is omitted from confusables. |
| 97 | linked | Independent variable（90.3） | — | Dependent variable（A）、Confounding variable（C） | cell phone use（未收录）、randomly assigned（未收录）、independent variable、dependent variable、confounding variable | Cell phone use is the factor the researcher manipulates, making it the independent variable; driving safety is the measured dependent variable. Random assignment is mentioned but not tested. |
| 98 | linked | Framing（67.7） | — | Representativeness heuristic（E）、Overconfidence（C）、Belief perseverance（D） | 95 percent success rate（未收录）、5 percent failure rate（未收录）、framing、intuition、overconfidence、belief perseverance、representativeness heuristic | Framing is the core concept: the same information presented as success vs. failure rate changes judgments. Supporting nudge is related but not directly tested. |
| 99 | linked | Observational learning（76.9） | — | Generalization（B）、Latent learning（C）、Negative reinforcement（D）、Partial-reinforcement effect（E） | observational learning、stimulus generalization（未收录）、latent learning、negative reinforcement、intermittent reinforcement（未收录） | The item tests observational learning as the best explanation for Suzie's behavior; the other options are operant/classical conditioning near-misses. |
| 100 | linked | Agoraphobia（64.8） | Panic disorder | — | persistent fear（未收录）、heart attack in public（未收录）、not wanting to leave his house（未收录）、Agoraphobia、Social anxiety（未收录）、Obsessive-compulsive（未收录）、Generalized anxiety（未收录） | Agoraphobia is the best match because the stem emphasizes fear of panic in public leading to avoidance of leaving home. Panic disorder is a supporting concept since the feared event is a heart attack (panic symptoms), but the avoidance pattern points to agoraphobia. |

## 覆盖

- linked：97
- needs_review：0
- no_match：0

## 校验记录

- Q4（psychology-ap-2017-mcq-004）：supporting 'Experiment' is not in the correct option or the core subheading; dropped
- Q4（psychology-ap-2017-mcq-004）：confusable 'Double-blind procedure' is not named in option 'A' and is not in the core subheading; dropped
- Q4（psychology-ap-2017-mcq-004）：keyword 'control for preexisting differences': not a known alias of 'Random assignment'; stored without a KP
- Q4（psychology-ap-2017-mcq-004）：keyword 'groups of participants': not a known alias of 'Experiment'; stored without a KP
- Q4（psychology-ap-2017-mcq-004）：keyword 'double-blind design': not a known alias of 'Double-blind procedure'; stored without a KP
- Q5（psychology-ap-2017-mcq-005）：supporting 'Neurotransmitters' is not in the correct option or the core subheading; dropped
- Q5（psychology-ap-2017-mcq-005）：confusable 'Stimulants' is not named in option 'A' and is not in the core subheading; dropped
- Q5（psychology-ap-2017-mcq-005）：confusable 'Stimulants' is not named in option 'B' and is not in the core subheading; dropped
- Q5（psychology-ap-2017-mcq-005）：confusable 'Stimulants' is not named in option 'C' and is not in the core subheading; dropped
- Q5（psychology-ap-2017-mcq-005）：confusable 'Hallucinogens' is not named in option 'E' and is not in the core subheading; dropped
- Q5（psychology-ap-2017-mcq-005）：keyword 'reduces the activity of the central nervous system': not a known alias of 'Depressants'; stored without a KP
- Q5（psychology-ap-2017-mcq-005）：keyword 'Alcohol': not a known alias of 'Depressants'; stored without a KP
- Q6（psychology-ap-2017-mcq-006）：supporting 'Schemata' is not in the correct option or the core subheading; dropped
- Q7（psychology-ap-2017-mcq-007）：confusable 'Loudness' is not named in option 'B' and is not in the core subheading; dropped
- Q8（psychology-ap-2017-mcq-008）：confusable 'Occipital lobes' is not named in option 'A' and is not in the core subheading; dropped
- Q8（psychology-ap-2017-mcq-008）：keyword 'Right hemisphere': not a known alias of 'Hemispheres'; stored without a KP
- Q8（psychology-ap-2017-mcq-008）：keyword 'Left occipital lobe': not a known alias of 'Occipital lobes'; stored without a KP
- Q10（psychology-ap-2017-mcq-010）：supporting 'Reflex arcs' is not in the correct option or the core subheading; dropped
- Q10（psychology-ap-2017-mcq-010）：confusable 'Somatosensory cortex' is not named in option 'E' and is not in the core subheading; dropped
- Q10（psychology-ap-2017-mcq-010）：keyword 'spinal reflex': not a known alias of 'Reflexes'; stored without a KP
- Q10（psychology-ap-2017-mcq-010）：keyword 'sensory information': not a known alias of 'Sensory neurons (afferent neurons)'; stored without a KP
- Q11（psychology-ap-2017-mcq-011）：keyword 'data': not a known alias of 'Descriptive statistics'; stored without a KP
- Q13（psychology-ap-2017-mcq-013）：supporting 'Unconscious' is not in the correct option or the core subheading; dropped
- Q13（psychology-ap-2017-mcq-013）：confusable 'Psychoanalysis (theory)' is not named in option 'B' and is not in the core subheading; dropped
- Q13（psychology-ap-2017-mcq-013）：confusable 'Humanist Perspective' is not named in option 'A' and is not in the core subheading; dropped
- Q13（psychology-ap-2017-mcq-013）：keyword 'study behavior directly': not a known alias of 'Behaviorism'; stored without a KP
- Q13（psychology-ap-2017-mcq-013）：keyword 'John Watson': not a known alias of 'Behaviorism'; stored without a KP
- Q14（psychology-ap-2017-mcq-014）：supporting 'Passionate love' duplicates a confusable; dropped
- Q14（psychology-ap-2017-mcq-014）：keyword 'Cognitive dissonance': not a known alias of 'Cognitive dissonance theory'; stored without a KP
- Q15（psychology-ap-2017-mcq-015）：supporting 'Muller-Lyer illusion' is not in the correct option or the core subheading; dropped
- Q15（psychology-ap-2017-mcq-015）：supporting 'Noncarpentered cultures' is not in the correct option or the core subheading; dropped
- Q15（psychology-ap-2017-mcq-015）：keyword 'Müller-Lyer illusion': not a known alias of 'Muller-Lyer illusion'; stored without a KP
- Q15（psychology-ap-2017-mcq-015）：keyword 'perceptual hypotheses': not a known alias of 'Schemata'; stored without a KP
- Q15（psychology-ap-2017-mcq-015）：keyword 'experiences in their lives': not a known alias of 'Schemata'; stored without a KP
- Q16（psychology-ap-2017-mcq-016）：keyword 'cultures': not a known alias of 'Display rules'; stored without a KP
- Q16（psychology-ap-2017-mcq-016）：keyword 'Schachter two-factor theory': not a known alias of 'Two-factor theory'; stored without a KP
- Q17（psychology-ap-2017-mcq-017）：supporting 'Locus of control' is not in the correct option or the core subheading; dropped
- Q17（psychology-ap-2017-mcq-017）：supporting 'Personal control' is not in the correct option or the core subheading; dropped
- Q17（psychology-ap-2017-mcq-017）：keyword 'Perception of control': not a known alias of 'Personal control'; stored without a KP
- Q18（psychology-ap-2017-mcq-018）：keyword 'emotions': not a known alias of 'Amygdala'; stored without a KP
- Q19（psychology-ap-2017-mcq-019）：keyword 'same sample again': not a known alias of 'Reliability'; stored without a KP
- Q20（psychology-ap-2017-mcq-020）：confusable 'Negative symptoms' is not named in option 'A' and is not in the core subheading; dropped
- Q20（psychology-ap-2017-mcq-020）：keyword 'positive symptom': not a known alias of 'Positive symptoms'; stored without a KP
- Q21（psychology-ap-2017-mcq-021）：keyword "Stanley Milgram's experiment": not a known alias of 'Obedience'; stored without a KP
- Q22（psychology-ap-2017-mcq-022）：confusable 'Secondary reinforcers' is not named in option 'C' and is not in the core subheading; dropped
- Q22（psychology-ap-2017-mcq-022）：keyword 'rats learned to navigate a maze': not a known alias of 'Cognitive map'; stored without a KP
- Q22（psychology-ap-2017-mcq-022）：keyword 'food reward': not a known alias of 'Reinforcement'; stored without a KP
- Q22（psychology-ap-2017-mcq-022）：keyword 'cognitive mapping': not a known alias of 'Cognitive map'; stored without a KP
- Q23（psychology-ap-2017-mcq-023）：supporting 'Systematic desensitization' is not in the correct option or the core subheading; dropped
- Q23（psychology-ap-2017-mcq-023）：supporting 'Counterconditioning' is not in the correct option or the core subheading; dropped
- Q23（psychology-ap-2017-mcq-023）：confusable 'Cognitive therapy' is not named in option 'C' and is not in the core subheading; dropped
- Q23（psychology-ap-2017-mcq-023）：confusable 'Humanistic therapies' is not named in option 'B' and is not in the core subheading; dropped
- Q23（psychology-ap-2017-mcq-023）：confusable 'Psychoanalysis (therapy)' is not named in option 'E' and is not in the core subheading; dropped
- Q23（psychology-ap-2017-mcq-023）：keyword 'phobia': not a known alias of 'Specific phobia'; stored without a KP
- Q23（psychology-ap-2017-mcq-023）：keyword 'Behavioral': not a known alias of 'Behavioral perspective'; stored without a KP
- Q24（psychology-ap-2017-mcq-024）：confusable 'Experiment' is in option 'E' but not in the core's narrow domain; dropped
- Q24（psychology-ap-2017-mcq-024）：keyword 'generalizable': not a known alias of 'Representative sample'; stored without a KP
- Q24（psychology-ap-2017-mcq-024）：keyword 'small convenience sample': not a known alias of 'Convenience sampling'; stored without a KP
- Q24（psychology-ap-2017-mcq-024）：keyword 'self-report surveys': not a known alias of 'Survey method'; stored without a KP
- Q25（psychology-ap-2017-mcq-025）：supporting 'Endocrine system' is not in the correct option or the core subheading; dropped
- Q25（psychology-ap-2017-mcq-025）：confusable 'Occipital lobes' is not named in option 'D' and is not in the core subheading; dropped
- Q26（psychology-ap-2017-mcq-026）：confusable 'Klinefelter’s syndrome' is not named in option 'A' and is not in the core subheading; dropped
- Q26（psychology-ap-2017-mcq-026）：confusable 'Turner’s syndrome' is not named in option 'A' and is not in the core subheading; dropped
- Q26（psychology-ap-2017-mcq-026）：keyword 'extra copy of chromosome 21': not a known alias of 'Down syndrome'; stored without a KP
- Q27（psychology-ap-2017-mcq-027）：confusable 'Rational emotive behavior therapy (REBT)' is not named in option 'B' and is not in the core subheading; dropped
- Q27（psychology-ap-2017-mcq-027）：keyword 'therapeutic technique': not a known alias of 'Person-centered therapy'; stored without a KP
- Q27（psychology-ap-2017-mcq-027）：keyword 'patient should determine the course of therapy': not a known alias of 'Person-centered therapy'; stored without a KP
- Q28（psychology-ap-2017-mcq-028）：keyword "infant's individual style of interacting with the world": not a known alias of 'Temperament'; stored without a KP
- Q29（psychology-ap-2017-mcq-029）：supporting 'Psychoanalysis (theory)' is not in the correct option or the core subheading; dropped
- Q29（psychology-ap-2017-mcq-029）：confusable 'Ego' is not named in option 'E' and is not in the core subheading; dropped
- Q29（psychology-ap-2017-mcq-029）：keyword "Sigmund Freud's theory of personality": not a known alias of 'Psychoanalysis (theory)'; stored without a KP
- Q29（psychology-ap-2017-mcq-029）：keyword 'More, more, more!': not a known alias of 'Id'; stored without a KP
- Q30（psychology-ap-2017-mcq-030）：keyword 'information on tuition, graduation and retention rates, financial aid, and enrollment': whole/long option text; dropped
- Q30（psychology-ap-2017-mcq-030）：keyword 'explain': not a known alias of 'Persuasion'; stored without a KP
- Q31（psychology-ap-2017-mcq-031）：confusable 'Primary reinforcers' is not named in option 'E' and is not in the core subheading; dropped
- Q31（psychology-ap-2017-mcq-031）：keyword 'primary reinforcement': not a known alias of 'Primary reinforcers'; stored without a KP
- Q32（psychology-ap-2017-mcq-032）：supporting 'Sensory habituation' is not in the correct option or the core subheading; dropped
- Q32（psychology-ap-2017-mcq-032）：keyword 'repeatedly shown an object': not a known alias of 'Habituation'; stored without a KP
- Q32（psychology-ap-2017-mcq-032）：keyword 'spend less time looking at the object': not a known alias of 'Habituation'; stored without a KP
- Q32（psychology-ap-2017-mcq-032）：keyword 'heart rates and respirations decrease': not a known alias of 'Habituation'; stored without a KP
- Q33（psychology-ap-2017-mcq-033）：supporting 'Linguistic relativity hypothesis' is not in the correct option or the core subheading; dropped
- Q33（psychology-ap-2017-mcq-033）：confusable 'Language acquisition device' is not named in option 'C' and is not in the core subheading; dropped
- Q33（psychology-ap-2017-mcq-033）：keyword 'Benjamin Whorf': not a known alias of 'Linguistic determinism'; stored without a KP
- Q33（psychology-ap-2017-mcq-033）：keyword 'Language shapes the way an individual thinks and interprets experiences.': whole/long option text; dropped
- Q34（psychology-ap-2017-mcq-034）：supporting 'Heuristic' duplicates a confusable; dropped
- Q34（psychology-ap-2017-mcq-034）：keyword 'systematically tries every possible solution': not a known alias of 'Algorithm'; stored without a KP
- Q35（psychology-ap-2017-mcq-035）：keyword 'performance': not a known alias of 'Social facilitation'; stored without a KP
- Q35（psychology-ap-2017-mcq-035）：keyword 'large crowd of attendees': not a known alias of 'Social facilitation'; stored without a KP
- Q36（psychology-ap-2017-mcq-036）：confusable 'Token economy' is not named in option 'D' and is not in the core subheading; dropped
- Q36（psychology-ap-2017-mcq-036）：keyword 'loves to read': not a known alias of 'Continuous reinforcement'; stored without a KP
- Q36（psychology-ap-2017-mcq-036）：keyword 'do nothing additional': not a known alias of 'Continuous reinforcement'; stored without a KP
- Q36（psychology-ap-2017-mcq-036）：keyword 'gold star': not a known alias of 'Token economy'; stored without a KP
- Q37（psychology-ap-2017-mcq-037）：supporting 'Attachment' is not in the correct option or the core subheading; dropped
- Q37（psychology-ap-2017-mcq-037）：keyword 'Konrad Lorenz': not a known alias of 'Imprinting'; stored without a KP
- Q37（psychology-ap-2017-mcq-037）：keyword 'gosling': not a known alias of 'Imprinting'; stored without a KP
- Q37（psychology-ap-2017-mcq-037）：keyword 'follow the first large moving object it sees': not a known alias of 'Imprinting'; stored without a KP
- Q38（psychology-ap-2017-mcq-038）：confusable 'Affiliation need' is not named in option 'D' and is not in the core subheading; dropped
- Q38（psychology-ap-2017-mcq-038）：keyword 'enjoys running': not a known alias of 'Intrinsic motivation'; stored without a KP
- Q38（psychology-ap-2017-mcq-038）：keyword 'a need for affiliation': not a known alias of 'Affiliation need'; stored without a KP
- Q38（psychology-ap-2017-mcq-038）：keyword 'a need for belongingness': not a known alias of 'Belongingness'; stored without a KP
- Q39（psychology-ap-2017-mcq-039）：supporting 'Emotion' is not in the correct option or the core subheading; dropped
- Q40（psychology-ap-2017-mcq-040）：supporting 'Schizophrenia' is not in the correct option or the core subheading; dropped
- Q40（psychology-ap-2017-mcq-040）：confusable 'Insight therapies' is not named in option 'D' and is not in the core subheading; dropped
- Q40（psychology-ap-2017-mcq-040）：keyword 'Insight therapy': not a known alias of 'Insight therapies'; stored without a KP
- Q41（psychology-ap-2017-mcq-041）：supporting 'Zimbardo’s prison experiment' is not in the correct option or the core subheading; dropped
- Q41（psychology-ap-2017-mcq-041）：keyword 'Stanford prison simulation': not a known alias of 'Zimbardo’s prison experiment'; stored without a KP
- Q41（psychology-ap-2017-mcq-041）：keyword 'situational factors': not a known alias of 'Situation attribution'; stored without a KP
- Q41（psychology-ap-2017-mcq-041）：keyword 'personality factors': not a known alias of 'Personality'; stored without a KP
- Q42（psychology-ap-2017-mcq-042）：supporting 'Ventromedial hypothalamus' is not in the correct option or the core subheading; dropped
- Q42（psychology-ap-2017-mcq-042）：supporting 'Lateral hypothalamus' is not in the correct option or the core subheading; dropped
- Q42（psychology-ap-2017-mcq-042）：confusable 'Occipital lobes' is not named in option 'C' and is not in the core subheading; dropped
- Q42（psychology-ap-2017-mcq-042）：keyword 'hunger': not a known alias of 'Hypothalamus'; stored without a KP
- Q42（psychology-ap-2017-mcq-042）：keyword 'satiety': not a known alias of 'Hypothalamus'; stored without a KP
- Q42（psychology-ap-2017-mcq-042）：keyword 'Occipital cortex': not a known alias of 'Occipital lobes'; stored without a KP
- Q43（psychology-ap-2017-mcq-043）：keyword 'scatterplots': not a known alias of 'Scatterplot'; stored without a KP
- Q43（psychology-ap-2017-mcq-043）：keyword 'strongest relation': not a known alias of 'Correlation coefficient'; stored without a KP
- Q44（psychology-ap-2017-mcq-044）：supporting 'Motivation' is not in the correct option or the core subheading; dropped
- Q44（psychology-ap-2017-mcq-044）：confusable 'Law of effect' is not named in option 'A' and is not in the core subheading; dropped
- Q44（psychology-ap-2017-mcq-044）：confusable 'Law of effect' is not named in option 'E' and is not in the core subheading; dropped
- Q44（psychology-ap-2017-mcq-044）：keyword 'job satisfaction': not a known alias of 'Organizational psychology'; stored without a KP
- Q44（psychology-ap-2017-mcq-044）：keyword 'redesign jobs': not a known alias of 'Organizational psychology'; stored without a KP
- Q44（psychology-ap-2017-mcq-044）：keyword 'responsibility and flexibility': not a known alias of 'Intrinsic motivation'; stored without a KP
- Q45（psychology-ap-2017-mcq-045）：confusable 'Parietal lobes' is not named in option 'A' and is not in the core subheading; dropped
- Q45（psychology-ap-2017-mcq-045）：confusable 'Wernicke’s area' is not named in option 'D' and is not in the core subheading; dropped
- Q45（psychology-ap-2017-mcq-045）：confusable 'Broca’s area' is not named in option 'E' and is not in the core subheading; dropped
- Q45（psychology-ap-2017-mcq-045）：keyword 'occipital lobe': not a known alias of 'Occipital lobes'; stored without a KP
- Q45（psychology-ap-2017-mcq-045）：keyword 'parietal lobe': not a known alias of 'Parietal lobes'; stored without a KP
- Q46（psychology-ap-2017-mcq-046）：keyword 'motivation theory': not a known alias of 'Motivation'; stored without a KP
- Q46（psychology-ap-2017-mcq-046）：keyword 'Instinct theory': not a known alias of 'Instincts'; stored without a KP
- Q46（psychology-ap-2017-mcq-046）：keyword 'Incentive theory': not a known alias of 'Incentive'; stored without a KP
- Q47（psychology-ap-2017-mcq-047）：confusable 'Episodic memory' is not named in option 'A' and is not in the core subheading; dropped
- Q47（psychology-ap-2017-mcq-047）：confusable 'Semantic memory' is not named in option 'D' and is not in the core subheading; dropped
- Q47（psychology-ap-2017-mcq-047）：confusable 'Short-term memory' is not named in option 'B' and is not in the core subheading; dropped
- Q47（psychology-ap-2017-mcq-047）：confusable 'Sensory memory' is not named in option 'C' and is not in the core subheading; dropped
- Q47（psychology-ap-2017-mcq-047）：keyword 'play the violin': not a known alias of 'Procedural memory'; stored without a KP
- Q47（psychology-ap-2017-mcq-047）：keyword 'from memory': not a known alias of 'Memory'; stored without a KP
- Q47（psychology-ap-2017-mcq-047）：keyword 'does not remember learning': not a known alias of 'Implicit memory'; stored without a KP
- Q47（psychology-ap-2017-mcq-047）：keyword 'Procedural': not a known alias of 'Procedural memory'; stored without a KP
- Q48（psychology-ap-2017-mcq-048）：keyword 'lucky': not a known alias of 'External locus of control'; stored without a KP
- Q49（psychology-ap-2017-mcq-049）：confusable 'Continuity' is not named in option 'D' and is not in the core subheading; dropped
- Q49（psychology-ap-2017-mcq-049）：keyword 'Gestalt principles': not a known alias of 'Gestalt psychology'; stored without a KP
- Q49（psychology-ap-2017-mcq-049）：keyword 'Good continuation': not a known alias of 'Continuity'; stored without a KP
- Q50（psychology-ap-2017-mcq-050）：supporting 'Language' is not in the correct option or the core subheading; dropped
- Q50（psychology-ap-2017-mcq-050）：keyword 'critical periods': not a known alias of 'Critical period'; stored without a KP
- Q50（psychology-ap-2017-mcq-050）：keyword 'deprived of language exposure': not a known alias of 'Language'; stored without a KP
- Q51（psychology-ap-2017-mcq-051）：supporting 'Dispositional attribution' is not in the correct option or the core subheading; dropped
- Q51（psychology-ap-2017-mcq-051）：confusable 'Just-world phenomenon' is not named in option 'B' and is not in the core subheading; dropped
- Q51（psychology-ap-2017-mcq-051）：confusable 'Stereotype' is in option 'D' but not in the core's narrow domain; dropped
- Q51（psychology-ap-2017-mcq-051）：confusable 'Social facilitation' is in option 'E' but not in the core's narrow domain; dropped
- Q51（psychology-ap-2017-mcq-051）：keyword 'explanation': not a known alias of 'Attribution'; stored without a KP
- Q51（psychology-ap-2017-mcq-051）：keyword 'nice person': not a known alias of 'Dispositional attribution'; stored without a KP
- Q51（psychology-ap-2017-mcq-051）：keyword 'belief in a just world': not a known alias of 'Just-world phenomenon'; stored without a KP
- Q52（psychology-ap-2017-mcq-052）：confusable 'Obsessive-compulsive disorder (OCD)' is not named in option 'A' and is not in the core subheading; dropped
- Q52（psychology-ap-2017-mcq-052）：confusable 'Antisocial personality disorder' is not named in option 'C' and is not in the core subheading; dropped
- Q52（psychology-ap-2017-mcq-052）：confusable 'Narcissistic personality disorder' is not named in option 'E' and is not in the core subheading; dropped
- Q52（psychology-ap-2017-mcq-052）：keyword 'defers to the wishes of others': not a known alias of 'Cluster C'; stored without a KP
- Q53（psychology-ap-2017-mcq-053）：supporting 'Unconscious' is not in the correct option or the core subheading; dropped
- Q53（psychology-ap-2017-mcq-053）：confusable 'Cognitive Perspective' is not named in option 'A' and is not in the core subheading; dropped
- Q53（psychology-ap-2017-mcq-053）：confusable 'Biopsychology (or Neuroscience) Perspective' is not named in option 'B' and is not in the core subheading; dropped
- Q53（psychology-ap-2017-mcq-053）：confusable 'Behavioral perspective' is not named in option 'C' and is not in the core subheading; dropped
- Q53（psychology-ap-2017-mcq-053）：confusable 'Social-Cultural (or Sociocultural) Perspective' is not named in option 'D' and is not in the core subheading; dropped
- Q53（psychology-ap-2017-mcq-053）：keyword 'unconscious thoughts and desires': not a known alias of 'Unconscious'; stored without a KP
- Q53（psychology-ap-2017-mcq-053）：keyword 'Psychodynamic': not a known alias of 'Psychodynamic Perspective'; stored without a KP
- Q54（psychology-ap-2017-mcq-054）：confusable 'Parasympathetic nervous system' is not named in option 'A' and is not in the core subheading; dropped
- Q54（psychology-ap-2017-mcq-054）：confusable 'Somatic nervous system' is not named in option 'D' and is not in the core subheading; dropped
- Q54（psychology-ap-2017-mcq-054）：confusable 'Central nervous system (CNS)' is not named in option 'B' and is not in the core subheading; dropped
- Q54（psychology-ap-2017-mcq-054）：confusable 'Endocrine system' is not named in option 'E' and is not in the core subheading; dropped
- Q54（psychology-ap-2017-mcq-054）：keyword 'pupils become dilated': not a known alias of 'Sympathetic nervous system'; stored without a KP
- Q54（psychology-ap-2017-mcq-054）：keyword 'digestion is reduced': not a known alias of 'Sympathetic nervous system'; stored without a KP
- Q54（psychology-ap-2017-mcq-054）：keyword 'skin becomes cold': not a known alias of 'Sympathetic nervous system'; stored without a KP
- Q54（psychology-ap-2017-mcq-054）：keyword 'Sympathetic': not a known alias of 'Sympathetic nervous system'; stored without a KP
- Q54（psychology-ap-2017-mcq-054）：keyword 'Parasympathetic': not a known alias of 'Parasympathetic nervous system'; stored without a KP
- Q54（psychology-ap-2017-mcq-054）：keyword 'Central': not a known alias of 'Central nervous system (CNS)'; stored without a KP
- Q54（psychology-ap-2017-mcq-054）：keyword 'Somatic': not a known alias of 'Somatic nervous system'; stored without a KP
- Q54（psychology-ap-2017-mcq-054）：keyword 'Endocrine': not a known alias of 'Endocrine system'; stored without a KP
- Q55（psychology-ap-2017-mcq-055）：confusable 'Social responsibility norm' is not named in option 'A' and is not in the core subheading; dropped
- Q55（psychology-ap-2017-mcq-055）：confusable 'Reciprocity norm' is not named in option 'C' and is not in the core subheading; dropped
- Q55（psychology-ap-2017-mcq-055）：keyword 'crowded farmers market': not a known alias of 'Bystander effect'; stored without a KP
- Q56（psychology-ap-2017-mcq-056）：keyword 'positively skewed': not a known alias of 'Positively skewed distribution'; stored without a KP
- Q56（psychology-ap-2017-mcq-056）：keyword 'normal': not a known alias of 'Normal curve'; stored without a KP
- Q56（psychology-ap-2017-mcq-056）：校验错误：confusable: option 'D' is not a wrong option
- Q57（psychology-ap-2017-mcq-057）：keyword 'defense mechanism': not a known alias of 'Defense mechanisms'; stored without a KP
- Q57（psychology-ap-2017-mcq-057）：keyword 'criticize other people for being dependent and lazy': not a known alias of 'Projection'; stored without a KP
- Q58（psychology-ap-2017-mcq-058）：confusable 'Just-world phenomenon' is not named in option 'B' and is not in the core subheading; dropped
- Q58（psychology-ap-2017-mcq-058）：confusable 'Group polarization' is not named in option 'A' and is not in the core subheading; dropped
- Q58（psychology-ap-2017-mcq-058）：confusable 'Social facilitation' is not named in option 'D' and is not in the core subheading; dropped
- Q58（psychology-ap-2017-mcq-058）：confusable 'Deindividuation' is not named in option 'E' and is not in the core subheading; dropped
- Q58（psychology-ap-2017-mcq-058）：keyword 'blame others': not a known alias of 'Scapegoat theory'; stored without a KP
- Q59（psychology-ap-2017-mcq-059）：supporting 'Positive correlation' is not in the correct option or the core subheading; dropped
- Q59（psychology-ap-2017-mcq-059）：supporting 'Perceived control' is not in the correct option or the core subheading; dropped
- Q59（psychology-ap-2017-mcq-059）：keyword 'Perceived lack of control': not a known alias of 'Perceived control'; stored without a KP
- Q60（psychology-ap-2017-mcq-060）：supporting 'Antidepressant drugs' is not in the correct option or the core subheading; dropped
- Q60（psychology-ap-2017-mcq-060）：supporting 'Major depressive disorder' is not in the correct option or the core subheading; dropped
- Q60（psychology-ap-2017-mcq-060）：confusable 'Cognitive therapy' is not named in option 'A' and is not in the core subheading; dropped
- Q60（psychology-ap-2017-mcq-060）：confusable 'Psychodynamic therapy' is not named in option 'B' and is not in the core subheading; dropped
- Q60（psychology-ap-2017-mcq-060）：confusable 'Social-Cultural (or Sociocultural) Perspective' is not named in option 'C' and is not in the core subheading; dropped
- Q60（psychology-ap-2017-mcq-060）：confusable 'Behavioral perspective' is not named in option 'E' and is not in the core subheading; dropped
- Q60（psychology-ap-2017-mcq-060）：keyword 'medication': not a known alias of 'Antidepressant drugs'; stored without a KP
- Q60（psychology-ap-2017-mcq-060）：keyword 'Biological': not a known alias of 'Somatic therapies'; stored without a KP
- Q61（psychology-ap-2017-mcq-061）：confusable 'Modeling' is not named in option 'A' and is not in the core subheading; dropped
- Q61（psychology-ap-2017-mcq-061）：keyword 'Little Albert': not a known alias of 'Classical conditioning'; stored without a KP
- Q61（psychology-ap-2017-mcq-061）：keyword 'fear can be conditioned in humans': whole/long option text; dropped
- Q61（psychology-ap-2017-mcq-061）：keyword 'humans can learn through observation': whole/long option text; dropped
- Q61（psychology-ap-2017-mcq-061）：keyword 'biological constraints affect learning in humans': whole/long option text; dropped
- Q61（psychology-ap-2017-mcq-061）：keyword 'punishment can effectively decrease behavior in humans': whole/long option text; dropped
- Q62（psychology-ap-2017-mcq-062）：supporting 'Psychosocial stage theory' is not in the correct option or the core subheading; dropped
- Q62（psychology-ap-2017-mcq-062）：confusable 'Autonomy (Erikson)' is not named in option 'E' and is not in the core subheading; dropped
- Q62（psychology-ap-2017-mcq-062）：confusable 'Basic trust' is not named in option 'A' and is not in the core subheading; dropped
- Q62（psychology-ap-2017-mcq-062）：keyword 'Erik Erikson': not a known alias of "Erikson's psychosocial stage theory"; stored without a KP
- Q62（psychology-ap-2017-mcq-062）：keyword 'early adulthood': not a known alias of 'Intimacy'; stored without a KP
- Q62（psychology-ap-2017-mcq-062）：keyword 'life partner': not a known alias of 'Intimacy'; stored without a KP
- Q62（psychology-ap-2017-mcq-062）：keyword 'psychosocial stage of development': not a known alias of "Erikson's psychosocial stage theory"; stored without a KP
- Q62（psychology-ap-2017-mcq-062）：keyword 'intimacy versus isolation': not a known alias of 'Intimacy'; stored without a KP
- Q62（psychology-ap-2017-mcq-062）：keyword 'identity versus role confusion': not a known alias of 'Identity'; stored without a KP
- Q63（psychology-ap-2017-mcq-063）：supporting 'Egocentric' duplicates a confusable; dropped
- Q63（psychology-ap-2017-mcq-063）：keyword 'tall, thin container': not a known alias of 'Conservation'; stored without a KP
- Q64（psychology-ap-2017-mcq-064）：supporting 'Retina' is not in the correct option or the core subheading; dropped
- Q64（psychology-ap-2017-mcq-064）：keyword 'rods and cones': not a known alias of 'Rods'; stored without a KP
- Q65（psychology-ap-2017-mcq-065）：confusable 'Central nervous system (CNS)' is not named in option 'B' and is not in the core subheading; dropped
- Q65（psychology-ap-2017-mcq-065）：confusable 'Peripheral nervous system (PNS)' is in option 'E' but not in the core's narrow domain; dropped
- Q65（psychology-ap-2017-mcq-065）：keyword 'too much dopamine in the brain': whole/long option text; dropped
- Q66（psychology-ap-2017-mcq-066）：confusable 'Unconscious' is not named in option 'C' and is not in the core subheading; dropped
- Q66（psychology-ap-2017-mcq-066）：keyword 'random stimulation from the brain stem': not a known alias of 'Activation-synthesis theory of dreaming'; stored without a KP
- Q66（psychology-ap-2017-mcq-066）：keyword 'Activation-synthesis': not a known alias of 'Activation-synthesis theory of dreaming'; stored without a KP
- Q67（psychology-ap-2017-mcq-067）：confusable 'Percentile rank' is not named in option 'A' and is not in the core subheading; dropped
- Q67（psychology-ap-2017-mcq-067）：keyword 'normal': not a known alias of 'Normal curve'; stored without a KP
- Q67（psychology-ap-2017-mcq-067）：keyword 'percentage': not a known alias of 'Percentile rank'; stored without a KP
- Q68（psychology-ap-2017-mcq-068）：supporting 'Intrapersonal intelligence' is not in the correct option or the core subheading; dropped
- Q68（psychology-ap-2017-mcq-068）：supporting 'Multiple intelligences' is not in the correct option or the core subheading; dropped
- Q68（psychology-ap-2017-mcq-068）：confusable 'Naturalist intelligence' is not named in option 'C' and is not in the core subheading; dropped
- Q68（psychology-ap-2017-mcq-068）：keyword 'Howard Gardner': not a known alias of 'Multiple intelligences'; stored without a KP
- Q68（psychology-ap-2017-mcq-068）：keyword 'Intrapersonal': not a known alias of 'Intrapersonal intelligence'; stored without a KP
- Q68（psychology-ap-2017-mcq-068）：keyword 'Naturalist': not a known alias of 'Naturalist intelligence'; stored without a KP
- Q68（psychology-ap-2017-mcq-068）：校验错误：confusable: option 'B' is not a wrong option
- Q69（psychology-ap-2017-mcq-069）：supporting 'Standardized test' is not in the correct option or the core subheading; dropped
- Q69（psychology-ap-2017-mcq-069）：confusable 'Individual tests' is not named in option 'B' and is not in the core subheading; dropped
- Q69（psychology-ap-2017-mcq-069）：confusable 'Projective tests' is not named in option 'E' and is not in the core subheading; dropped
- Q69（psychology-ap-2017-mcq-069）：keyword 'standardized tests': not a known alias of 'Standardized test'; stored without a KP
- Q69（psychology-ap-2017-mcq-069）：keyword 'administered and scored in a consistent manner': not a known alias of 'Standardization'; stored without a KP
- Q69（psychology-ap-2017-mcq-069）：keyword 'administered individually': not a known alias of 'Individual tests'; stored without a KP
- Q69（psychology-ap-2017-mcq-069）：keyword 'projective': not a known alias of 'Projective tests'; stored without a KP
- Q70（psychology-ap-2017-mcq-070）：supporting 'Reinforcement schedule' is not in the correct option or the core subheading; dropped
- Q70（psychology-ap-2017-mcq-070）：supporting 'Reinforcement' is not in the correct option or the core subheading; dropped
- Q70（psychology-ap-2017-mcq-070）：confusable 'Variable-ratio (VR) schedule' is not named in option 'C' and is not in the core subheading; dropped
- Q70（psychology-ap-2017-mcq-070）：confusable 'Fixed-interval (FI) schedule' is not named in option 'B' and is not in the core subheading; dropped
- Q70（psychology-ap-2017-mcq-070）：confusable 'Variable-interval (VI) schedule' is not named in option 'D' and is not in the core subheading; dropped
- Q70（psychology-ap-2017-mcq-070）：confusable 'Continuous reinforcement' is not named in option 'E' and is not in the core subheading; dropped
- Q70（psychology-ap-2017-mcq-070）：keyword 'reinforcement schedules': not a known alias of 'Reinforcement schedule'; stored without a KP
- Q70（psychology-ap-2017-mcq-070）：keyword 'Fixed ratio': not a known alias of 'Fixed-ratio (FR) schedule'; stored without a KP
- Q70（psychology-ap-2017-mcq-070）：keyword 'Fixed interval': not a known alias of 'Fixed-interval (FI) schedule'; stored without a KP
- Q70（psychology-ap-2017-mcq-070）：keyword 'Variable ratio': not a known alias of 'Variable-ratio (VR) schedule'; stored without a KP
- Q70（psychology-ap-2017-mcq-070）：keyword 'Variable interval': not a known alias of 'Variable-interval (VI) schedule'; stored without a KP
- Q70（psychology-ap-2017-mcq-070）：keyword 'Continuous': not a known alias of 'Continuous reinforcement'; stored without a KP
- Q71（psychology-ap-2017-mcq-071）：supporting 'Hypnosis' is not in the correct option or the core subheading; dropped
- Q71（psychology-ap-2017-mcq-071）：supporting 'Evidence-based practice' is not in the correct option or the core subheading; dropped
- Q71（psychology-ap-2017-mcq-071）：confusable 'Prejudice' is not named in option 'E' and is not in the core subheading; dropped
- Q71（psychology-ap-2017-mcq-071）：keyword 'empirical support': not a known alias of 'Evidence-based practice'; stored without a KP
- Q71（psychology-ap-2017-mcq-071）：keyword 'negative bias': not a known alias of 'Prejudice'; stored without a KP
- Q72（psychology-ap-2017-mcq-072）：supporting 'Aphasia' is not in the correct option or the core subheading; dropped
- Q72（psychology-ap-2017-mcq-072）：keyword 'comprehending the meaning of words': not a known alias of 'Wernicke’s area'; stored without a KP
- Q72（psychology-ap-2017-mcq-072）：校验错误：confusable: option 'B' is not a wrong option
- Q73（psychology-ap-2017-mcq-073）：supporting 'Token economy' is not in the correct option or the core subheading; dropped
- Q73（psychology-ap-2017-mcq-073）：keyword 'star': not a known alias of 'Secondary reinforcers'; stored without a KP
- Q73（psychology-ap-2017-mcq-073）：keyword 'behaves well': not a known alias of 'Reinforcer'; stored without a KP
- Q73（psychology-ap-2017-mcq-073）：keyword 'prize': not a known alias of 'Secondary reinforcers'; stored without a KP
- Q73（psychology-ap-2017-mcq-073）：keyword 'secondary reinforcer': not a known alias of 'Secondary reinforcers'; stored without a KP
- Q74（psychology-ap-2017-mcq-074）：supporting 'Trauma-and-stressor-related disorders' is not in the correct option or the core subheading; dropped
- Q74（psychology-ap-2017-mcq-074）：keyword 'lost his ability to see': not a known alias of 'Conversion disorder'; stored without a KP
- Q74（psychology-ap-2017-mcq-074）：keyword 'unable to find a biological reason': not a known alias of 'Conversion disorder'; stored without a KP
- Q74（psychology-ap-2017-mcq-074）：keyword 'witnessed a burglary': not a known alias of 'Trauma-and-stressor-related disorders'; stored without a KP
- Q75（psychology-ap-2017-mcq-075）：confusable 'Experiment' is not named in option 'B' and is not in the core subheading; dropped
- Q75（psychology-ap-2017-mcq-075）：confusable 'Quantitative research' is not named in option 'C' and is not in the core subheading; dropped
- Q76（psychology-ap-2017-mcq-076）：keyword 'stimulus generalization': not a known alias of 'Generalization'; stored without a KP
- Q76（psychology-ap-2017-mcq-076）：keyword 'nauseous': not a known alias of 'Taste aversion'; stored without a KP
- Q77（psychology-ap-2017-mcq-077）：confusable 'Statistical significance' is not named in option 'D' and is not in the core subheading; dropped
- Q77（psychology-ap-2017-mcq-077）：keyword 'Intelligence quotient (IQ) scores': not a known alias of 'IQ'; stored without a KP
- Q77（psychology-ap-2017-mcq-077）：keyword 'statistically significant': not a known alias of 'Statistical significance'; stored without a KP
- Q78（psychology-ap-2017-mcq-078）：confusable 'Difference threshold' is not named in option 'E' and is not in the core subheading; dropped
- Q78（psychology-ap-2017-mcq-078）：keyword 'attention': not a known alias of 'Selective attention'; stored without a KP
- Q78（psychology-ap-2017-mcq-078）：keyword 'just-noticeable difference': not a known alias of 'Difference threshold'; stored without a KP
- Q79（psychology-ap-2017-mcq-079）：supporting 'Levels of processing model' is not in the correct option or the core subheading; dropped
- Q79（psychology-ap-2017-mcq-079）：supporting 'Deeply encoded' is not in the correct option or the core subheading; dropped
- Q79（psychology-ap-2017-mcq-079）：keyword 'levels of processing': not a known alias of 'Levels of processing model'; stored without a KP
- Q79（psychology-ap-2017-mcq-079）：keyword 'Deciding whether an umbrella would be useful to pack for a trip': whole/long option text; dropped
- Q79（psychology-ap-2017-mcq-079）：keyword 'Counting the number of syllables': not a known alias of 'Shallow processing'; stored without a KP
- Q79（psychology-ap-2017-mcq-079）：keyword 'Mentally spelling': not a known alias of 'Shallow processing'; stored without a KP
- Q79（psychology-ap-2017-mcq-079）：keyword 'rhymes': not a known alias of 'Shallow processing'; stored without a KP
- Q80（psychology-ap-2017-mcq-080）：校验错误：confusable: option 'B' is not a wrong option
- Q81（psychology-ap-2017-mcq-081）：confusable 'Behavioral perspective' is not named in option 'A' and is not in the core subheading; dropped
- Q81（psychology-ap-2017-mcq-081）：confusable 'Cognitive Perspective' is not named in option 'B' and is not in the core subheading; dropped
- Q81（psychology-ap-2017-mcq-081）：confusable 'Biopsychology (or Neuroscience) Perspective' is not named in option 'E' and is not in the core subheading; dropped
- Q81（psychology-ap-2017-mcq-081）：keyword 'Big Five personality factors': not a known alias of 'Big Five personality traits'; stored without a KP
- Q81（psychology-ap-2017-mcq-081）：keyword 'Trait psychology': not a known alias of 'Traits'; stored without a KP
- Q82（psychology-ap-2017-mcq-082）：supporting 'Selective attention' is not in the correct option or the core subheading; dropped
- Q82（psychology-ap-2017-mcq-082）：keyword 'attention is focused': not a known alias of 'Selective attention'; stored without a KP
- Q82（psychology-ap-2017-mcq-082）：keyword 'unable to recall': not a known alias of 'Recall'; stored without a KP
- Q82（psychology-ap-2017-mcq-082）：keyword 'encoding failure': not a known alias of 'Encoding'; stored without a KP
- Q82（psychology-ap-2017-mcq-082）：keyword 'retrieval failure': not a known alias of 'Retrieval'; stored without a KP
- Q83（psychology-ap-2017-mcq-083）：confusable 'Secondary reinforcers' is not named in option 'E' and is not in the core subheading; dropped
- Q83（psychology-ap-2017-mcq-083）：keyword "Ivan Pavlov's classical conditioning paradigm": not a known alias of 'Classical conditioning'; stored without a KP
- Q83（psychology-ap-2017-mcq-083）：keyword 'salivated in response to the food': not a known alias of 'Unconditioned stimulus (US or UCS)'; stored without a KP
- Q84（psychology-ap-2017-mcq-084）：supporting 'Unconscious' is not in the correct option or the core subheading; dropped
- Q84（psychology-ap-2017-mcq-084）：confusable 'Behavioral perspective' is not named in option 'B' and is not in the core subheading; dropped
- Q84（psychology-ap-2017-mcq-084）：confusable 'Humanistic theories' is not named in option 'C' and is not in the core subheading; dropped
- Q84（psychology-ap-2017-mcq-084）：confusable 'Cognitive theorists' is not named in option 'D' and is not in the core subheading; dropped
- Q84（psychology-ap-2017-mcq-084）：confusable 'Social-cognitive theory' is not named in option 'E' and is not in the core subheading; dropped
- Q84（psychology-ap-2017-mcq-084）：keyword 'personalities': not a known alias of 'Personality'; stored without a KP
- Q84（psychology-ap-2017-mcq-084）：keyword 'draw pictures': not a known alias of 'Projective tests'; stored without a KP
- Q84（psychology-ap-2017-mcq-084）：keyword 'drawings will reveal underlying personality characteristics': not a known alias of 'Projective tests'; stored without a KP
- Q84（psychology-ap-2017-mcq-084）：keyword 'Psychoanalytic': not a known alias of 'Psychoanalysis (theory)'; stored without a KP
- Q85（psychology-ap-2017-mcq-085）：confusable 'Behavior therapy' is not named in option 'B' and is not in the core subheading; dropped
- Q85（psychology-ap-2017-mcq-085）：confusable 'Psychodynamic therapy' is not named in option 'C' and is not in the core subheading; dropped
- Q85（psychology-ap-2017-mcq-085）：confusable 'Humanistic therapies' is not named in option 'D' and is not in the core subheading; dropped
- Q85（psychology-ap-2017-mcq-085）：keyword 'maladaptive thinking': not a known alias of 'Cognitive restructuring'; stored without a KP
- Q85（psychology-ap-2017-mcq-085）：keyword 'Cognitive': not a known alias of 'Cognitive therapy'; stored without a KP
- Q86（psychology-ap-2017-mcq-086）：supporting 'Schemata' is not in the correct option or the core subheading; dropped
- Q86（psychology-ap-2017-mcq-086）：keyword 'door opening': not a known alias of 'Mental set'; stored without a KP
- Q86（psychology-ap-2017-mcq-086）：keyword 'pulling on the handle': not a known alias of 'Mental set'; stored without a KP
- Q87（psychology-ap-2017-mcq-087）：supporting 'Smell (Olfaction)' is not in the correct option or the core subheading; dropped
- Q87（psychology-ap-2017-mcq-087）：confusable 'Difference threshold' is not named in option 'E' and is not in the core subheading; dropped
- Q87（psychology-ap-2017-mcq-087）：keyword 'no longer notices the strong smell of garlic': not a known alias of 'Sensory adaptation'; stored without a KP
- Q87（psychology-ap-2017-mcq-087）：keyword 'smell of garlic': not a known alias of 'Smell (Olfaction)'; stored without a KP
- Q87（psychology-ap-2017-mcq-087）：keyword 'subliminal perception': not a known alias of 'Subliminal'; stored without a KP
- Q87（psychology-ap-2017-mcq-087）：keyword 'just-noticeable difference': not a known alias of 'Difference threshold'; stored without a KP
- Q88（psychology-ap-2017-mcq-088）：supporting 'Neurocognitive disorders' is not in the correct option or the core subheading; dropped
- Q88（psychology-ap-2017-mcq-088）：confusable 'Recall' is not named in option 'C' and is not in the core subheading; dropped
- Q88（psychology-ap-2017-mcq-088）：confusable 'Proactive interference' is not named in option 'A' and is not in the core subheading; dropped
- Q88（psychology-ap-2017-mcq-088）：keyword 'Quickly learning': not a known alias of 'Learning'; stored without a KP
- Q89（psychology-ap-2017-mcq-089）：supporting 'Cognitive learning' is not in the correct option or the core subheading; dropped
- Q89（psychology-ap-2017-mcq-089）：confusable 'Observational learning' is not named in option 'A' and is not in the core subheading; dropped
- Q89（psychology-ap-2017-mcq-089）：confusable 'Classical conditioning' is not named in option 'E' and is not in the core subheading; dropped
- Q89（psychology-ap-2017-mcq-089）：keyword 'cognitive maps': not a known alias of 'Cognitive map'; stored without a KP
- Q90（psychology-ap-2017-mcq-090）：supporting 'Achievement tests' duplicates a confusable; dropped
- Q90（psychology-ap-2017-mcq-090）：keyword 'potential ability': not a known alias of 'Aptitude tests'; stored without a KP
- Q91（psychology-ap-2017-mcq-091）：confusable 'Obsessive-compulsive disorder (OCD)' is not named in option 'C' and is not in the core subheading; dropped
- Q91（psychology-ap-2017-mcq-091）：confusable 'Conversion disorder' is not named in option 'D' and is not in the core subheading; dropped
- Q91（psychology-ap-2017-mcq-091）：keyword 'posttraumatic stress': not a known alias of 'Post-traumatic stress disorder (PTSD)'; stored without a KP
- Q91（psychology-ap-2017-mcq-091）：keyword 'schizophrenia spectrum and other psychotic disorders': not a known alias of 'Schizophrenia spectrum disorders'; stored without a KP
- Q91（psychology-ap-2017-mcq-091）：keyword 'major depressive': not a known alias of 'Major depressive disorder'; stored without a KP
- Q91（psychology-ap-2017-mcq-091）：keyword 'obsessive-compulsive': not a known alias of 'Obsessive-compulsive disorder (OCD)'; stored without a KP
- Q91（psychology-ap-2017-mcq-091）：keyword 'conversion': not a known alias of 'Conversion disorder'; stored without a KP
- Q92（psychology-ap-2017-mcq-092）：supporting 'Memory' is not in the correct option or the core subheading; dropped
- Q92（psychology-ap-2017-mcq-092）：confusable 'Relearning effect' is not named in option 'B' and is not in the core subheading; dropped
- Q92（psychology-ap-2017-mcq-092）：keyword 'forgetting': not a known alias of 'Decay'; stored without a KP
- Q92（psychology-ap-2017-mcq-092）：keyword 'time': not a known alias of 'Decay'; stored without a KP
- Q92（psychology-ap-2017-mcq-092）：校验错误：confusable: option 'A' is not a wrong option
- Q93（psychology-ap-2017-mcq-093）：keyword 'perception of taste': not a known alias of 'Gustation'; stored without a KP
- Q93（psychology-ap-2017-mcq-093）：keyword 'sense of smell': not a known alias of 'Smell (Olfaction)'; stored without a KP
- Q93（psychology-ap-2017-mcq-093）：keyword 'flavor of food': not a known alias of 'Sensory interaction'; stored without a KP
- Q93（psychology-ap-2017-mcq-093）：keyword 'five primary taste qualities': not a known alias of 'Five different types of tastes'; stored without a KP
- Q93（psychology-ap-2017-mcq-093）：keyword 'Taste receptors': not a known alias of 'Taste buds'; stored without a KP
- Q94（psychology-ap-2017-mcq-094）：confusable 'Echoic memory' is not named in option 'E' and is not in the core subheading; dropped
- Q94（psychology-ap-2017-mcq-094）：confusable 'Procedural memory' is not named in option 'B' and is not in the core subheading; dropped
- Q94（psychology-ap-2017-mcq-094）：confusable 'Explicit memory' is not named in option 'C' and is not in the core subheading; dropped
- Q94（psychology-ap-2017-mcq-094）：confusable 'Implicit memory' is not named in option 'D' and is not in the core subheading; dropped
- Q94（psychology-ap-2017-mcq-094）：keyword 'glances at a graph': not a known alias of 'Iconic memory'; stored without a KP
- Q94（psychology-ap-2017-mcq-094）：keyword 'less than a second later': not a known alias of 'Iconic memory'; stored without a KP
- Q94（psychology-ap-2017-mcq-094）：keyword 'immediately remember': not a known alias of 'Sensory memory'; stored without a KP
- Q94（psychology-ap-2017-mcq-094）：keyword 'Iconic': not a known alias of 'Iconic memory'; stored without a KP
- Q94（psychology-ap-2017-mcq-094）：keyword 'Echoic': not a known alias of 'Echoic memory'; stored without a KP
- Q94（psychology-ap-2017-mcq-094）：keyword 'Procedural': not a known alias of 'Procedural memory'; stored without a KP
- Q94（psychology-ap-2017-mcq-094）：keyword 'Declarative': not a known alias of 'Explicit memory'; stored without a KP
- Q94（psychology-ap-2017-mcq-094）：keyword 'Implicit': not a known alias of 'Implicit memory'; stored without a KP
- Q95（psychology-ap-2017-mcq-095）：keyword 'strongly opposed to video game use': not a known alias of 'Confirmation bias'; stored without a KP
- Q95（psychology-ap-2017-mcq-095）：keyword 'the dangers of video games': not a known alias of 'Confirmation bias'; stored without a KP
- Q96（psychology-ap-2017-mcq-096）：supporting 'Random assignment' is not in the correct option or the core subheading; dropped
- Q96（psychology-ap-2017-mcq-096）：confusable 'Correlation' is not named in option 'C' and is not in the core subheading; dropped
- Q96（psychology-ap-2017-mcq-096）：keyword 'randomly assigned': not a known alias of 'Random assignment'; stored without a KP
- Q96（psychology-ap-2017-mcq-096）：keyword 'Experimental': not a known alias of 'Experiment'; stored without a KP
- Q96（psychology-ap-2017-mcq-096）：keyword 'Correlational': not a known alias of 'Correlation'; stored without a KP
- Q97（psychology-ap-2017-mcq-097）：supporting 'Dependent variable' duplicates a confusable; dropped
- Q97（psychology-ap-2017-mcq-097）：keyword 'cell phone use': not a known alias of 'Independent variable'; stored without a KP
- Q97（psychology-ap-2017-mcq-097）：keyword 'randomly assigned': not a known alias of 'Random assignment'; stored without a KP
- Q98（psychology-ap-2017-mcq-098）：supporting 'Nudge' is not in the correct option or the core subheading; dropped
- Q98（psychology-ap-2017-mcq-098）：keyword '95 percent success rate': not a known alias of 'Framing'; stored without a KP
- Q98（psychology-ap-2017-mcq-098）：keyword '5 percent failure rate': not a known alias of 'Framing'; stored without a KP
- Q99（psychology-ap-2017-mcq-099）：supporting 'Vicarious conditioning' is not in the correct option or the core subheading; dropped
- Q99（psychology-ap-2017-mcq-099）：keyword 'stimulus generalization': not a known alias of 'Generalization'; stored without a KP
- Q99（psychology-ap-2017-mcq-099）：keyword 'intermittent reinforcement': not a known alias of 'Partial-reinforcement effect'; stored without a KP
- Q100（psychology-ap-2017-mcq-100）：confusable 'Social anxiety disorder' is not named in option 'A' and is not in the core subheading; dropped
- Q100（psychology-ap-2017-mcq-100）：confusable 'Generalized anxiety disorder (GAD)' is not named in option 'C' and is not in the core subheading; dropped
- Q100（psychology-ap-2017-mcq-100）：confusable 'Obsessive-compulsive disorder (OCD)' is not named in option 'B' and is not in the core subheading; dropped
- Q100（psychology-ap-2017-mcq-100）：keyword 'persistent fear': not a known alias of 'Agoraphobia'; stored without a KP
- Q100（psychology-ap-2017-mcq-100）：keyword 'heart attack in public': not a known alias of 'Agoraphobia'; stored without a KP
- Q100（psychology-ap-2017-mcq-100）：keyword 'not wanting to leave his house': not a known alias of 'Agoraphobia'; stored without a KP
- Q100（psychology-ap-2017-mcq-100）：keyword 'severely limits the time he spends out in public': whole/long option text; dropped
- Q100（psychology-ap-2017-mcq-100）：keyword 'Social anxiety': not a known alias of 'Social anxiety disorder'; stored without a KP
- Q100（psychology-ap-2017-mcq-100）：keyword 'Obsessive-compulsive': not a known alias of 'Obsessive-compulsive disorder (OCD)'; stored without a KP
- Q100（psychology-ap-2017-mcq-100）：keyword 'Generalized anxiety': not a known alias of 'Generalized anxiety disorder (GAD)'; stored without a KP

## 复跑命令

```bash
python3 _tools/link_question_concepts.py --paper psychology-ap-2017 --force
```

---

> 本报告是链接工具的运行快照。之后对 6 道题做了人工概念修订，并移除了 2 道图片选项题的链接；最终状态见 `psychology-ap-2016-2017_ai_concepts_final.md`。
