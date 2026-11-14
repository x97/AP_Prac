# 题目概念关联报告（概念层）

- 生成时间：2026-11-02T13:58:39+08:00
- 试卷：`psychology-ap-2016`
- 模型：`deepseek-flash[1m]`
- Prompt：`question-concept-link-v2`
- 题目：97；失败：0

> 核心概念按“正确选项倒推”生成；干扰项只进入 confusable。
> 写库目标：`question_concept_links`；`question_kp_links` 仅作 legacy 兼容。

| 题号 | 状态 | 核心概念 | 辅助 | 易混淆 | 关键字 | 备注 |
|---:|---|---|---|---|---|---|
| 4 | linked | Linear perspective（30.4）、Monocular depth cues（64.3） | Depth perception | Convergence（A）、Similarity (visual)（D）、Closure（E） | patch over the eye（未收录）、distance objects are from her（未收录）、Linear perspective、Convergence、Binocular disparity（未收录）、Similarity、Closure | Core concept is linear perspective as a monocular depth cue usable with one eye. The patched eye makes binocular cues (convergence, retinal disparity) unavailable. Supporting concept depth perception frames the task. |
| 5 | linked | Active listening（66.5） | Person-centered therapy | Unconditional positive regard（B） | client-centered therapy（未收录）、rephrases things that Gerry has said（未收录）、asks for clarification（未收录）、Active listening、Empathy（未收录）、Unconditional positive regard | Active listening is the tested behavior (echoing/clarifying); client-centered therapy is the broader context. Genuineness (C) and self-worth (E) are not in the candidate list and are only loosely related, so omitted from confusables. |
| 6 | linked | Reliability（78.0） | Test-retest reliability | Validity（A）、Standardization（C）、Statistical significance（D） | same test（未收录）、test scores are similar（未收录）、two administrations（未收录）、test properties（未收录）、Reliability | The item tests the general concept of reliability through a test-retest scenario; test-retest reliability is a supporting subtype. Validity, standardization, and statistical significance are the plausible same-domain distractors. |
| 7 | linked | Ventromedial hypothalamus（25.5） | Lateral hypothalamus | Homeostasis（A）、Set-point theory（C） | gain weight（未收录）、ventromedial hypothalamus、homeostasis、set point、basal metabolism rate（未收录） | The item tests knowledge that damage to the ventromedial (satiety) hypothalamus causes overeating and weight gain. The lateral hypothalamus (C11) is a supporting contrast concept, though not named in the options. |
| 8 | linked | Levels of processing model（38.5） | Deeply encoded、Shallowly encoded | Selective attention（B） | levels of processing（未收录）、memorize each fact（未收录）、selective attention | The item tests the levels-of-processing model: deep, meaning-based encoding (Emma) versus shallow rote memorization (Sophie). |
| 9 | linked | Endorphins（65.6） | — | Teratogens（D） | endorphins、well-being、teratogens、gamma-aminobutyric acid (GABA)（未收录）、acetylcholine（未收录）、glutamate（未收录） | The item tests the role of endorphins in exercise-induced energy and well-being. GABA, acetylcholine, and glutamate are neurotransmitter distractors but are not in the candidate list, so they are recorded as null-concept keywords. |
| 10 | linked | Opponent-process theory (color vision)（73.7） | Afterimage | Color constancy（A） | opponent-process theory、color vision（未收录）、Afterimages（未收录）、Color constancy、Feature detection（未收录）、Parallel processing | Core is the opponent-process theory of color vision; afterimages are the supporting phenomenon that demonstrates it. Subtractive color mixing and parallel processing are not close enough to the core to be confusables. |
| 11 | linked | Psychoanalysis (theory)（30.0）、Behaviorism（30.0） | — | — | chronological order（未收录）、Behaviorism、Psychoanalysis、Structuralism（未收录）、Humanism（未收录）、perspectives of psychology（未收录） | The item tests knowledge of the historical sequence of major psychological perspectives. Structuralism is a key term but has no candidate concept; it is included as a keyword with concept=null. Core concepts are Psychoanalysis and Behaviorism because they are named in the stem and their chronological placement is essential to selecting the correct order. |
| 12 | linked | Incentive（30.0） | — | — | Incentive theories of motivation（未收录）、external stimuli（未收录）、motivation、physiological equilibrium（未收录）、internal states of tension（未收录）、cognitive dissonance（未收录） | Incentive theory is best captured by C03 (incentive as external stimulus motivating behavior); C55 is an alternate incentive concept but C03 matches the correct option wording more directly. |
| 13 | linked | Proactive interference（68.3） | Interference | Retroactive interference（D） | proactive interference、retroactive interference | The stem describes old learning (Japanese) interfering with new learning (Chinese), which is proactive interference. Retroactive interference is the tempting near-miss distractor. |
| 14 | linked | Evolutionary (or Darwinian) Perspective（39.6） | — | Action potential（B） | evolutionary psychologist（未收录）、innate fear of the dark（未收录）、action potential、first words（未收录）、features of a car（未收录） | Core is the evolutionary perspective; the correct option's 'innate fear' reflects a sociobiological/evolutionary explanation. Distractors map to other psychological domains (biological, developmental, human factors). |
| 15 | linked | Shaping（71.6） | Positive reinforcement、Operant conditioning | Negative reinforcement（A）、Spontaneous recovery（B）、Latent learning（D） | praised（未收录）、shaping、negative reinforcement、spontaneous recovery、latent learning | The scenario illustrates successive approximations reinforced toward a target behavior, which is shaping. Praise is positive reinforcement supporting the shaping process. Implicit learning (E) is a loosely related distractor and omitted as a confusable. |
| 16 | linked | Sensory adaptation（73.5） | — | Weber’s law（C）、Accommodation (sensory)（A）、Assimilation（D）、Phi phenomenon（E） | no longer detects the smell（未收录）、strong odor of chocolate chip cookies（未收录）、Sensory adaptation | Core is sensory adaptation; smell/olfaction supports the scenario. Distractors are near-miss sensory/perceptual or adaptation-sounding concepts. |
| 17 | linked | Systematic desensitization（79.8）、Specific phobia（75.1） | Exposure therapies | Major depressive disorder（B）、Bipolar disorder（C）、Antisocial personality disorder（E） | Systematic desensitization、Specific phobia disorder（未收录）、Major depressive disorder、Bipolar disorder、Schizophrenia、Antisocial personality disorder | Systematic desensitization is an exposure-based behavioral therapy indicated for specific phobias; other options are disorders treated by different modalities. |
| 18 | linked | Observational learning（76.9） | — | — | social learning theorist（未收录）、fear of flying（未收录）、observed someone else’s fear of flying（未收录） | Social learning theory is represented by observational learning (C20) and the supporting social learning theory concept (C29). |
| 19 | linked | Stage theories（38.2） | — | — | Jean Piaget’s stages of cognitive development（未收录）、underestimated children’s abilities（未收录） | The item tests the modern critique of Piaget's stage theory (underestimation of children's abilities), best mapped to stage theories (C16) with information processing (C02) as a supporting alternative account of gradual development. No candidate directly names the underestimation critique, so confidence is moderate. |
| 20 | linked | Functional fixedness（38.2） | — | Framing（D）、Availability heuristic（E） | functional fixedness、coin（未收录）、screw（未收录） | The coin-as-tool example illustrates overcoming functional fixedness by using an object in a novel way. Only functional fixedness is tested; other options are unrelated judgment biases. |
| 21 | linked | Superego（60.8） | — | Ego（B）、Id（A）、Collective unconscious（E） | Sigmund Freud（未收录）、personality structure（未收录）、moral values（未收录）、superego、id、ego、collective unconscious | Core is the superego as the moral/conscience structure. Ego and id are same-domain Freudian structures and serve as confusables; collective unconscious is a Jungian near-miss. 'Self' (option D) is not a Freudian structure and is omitted as a confusable. |
| 22 | linked | Alarm reaction（27.4） | General adaptation syndrome (GAS) | — | increase in his breathing and heart rate（未收录）、Alarm reaction、Parasympathetic response（未收录） | The stem describes sympathetic arousal typical of Selye's alarm stage; the correct option is Alarm reaction. The parasympathetic option is the narrow-domain near-miss. |
| 23 | linked | Latent learning（74.0） | — | Modeling（A）、Spontaneous recovery（B）、Classical conditioning（C）、Generalization（D） | Latent learning、campus tour（未收录）、Modeling、Spontaneous recovery、Classical conditioning、Stimulus generalization（未收录） | Kelly's ability to navigate campus reflects learning that occurred during the tour but was not demonstrated until needed, which is the definition of latent learning. |
| 24 | linked | REM sleep behavior disorder（30.0） | — | Sleep cycle（B）、Sleep spindles（E） | sleep、dreams、act out their dreams（未收录）、first sleep cycle（未收录）、REM sleep、Sleep spindles、night terrors | The correct answer hinges on REM paralysis preventing acting out dreams; REM sleep behavior disorder is the near-miss disorder concept. Option D mentions Freud but is not a confusable for the core sleep/dreaming concept. |
| 25 | linked | Inferential statistics（63.4） | — | Factor analysis（D） | statistical approach（未收录）、forming conclusions（未收录）、independent variable、dependent variable、Inferential（未收录） | The item tests inferential statistics as the approach for drawing conclusions about IV effects on DV variation. Descriptive statistics and factor analysis are the closest statistical near-misses; correlational and qualitative are broader research-approach distractors. |
| 26 | linked | Cognitive map（69.8） | — | Heuristic（C）、Algorithm（A）、Mental set（B） | mental image（未收录）、spatial layout（未收录）、cognitive map、algorithm、mental set、heuristic、insight（未收录） | Core concept is cognitive map, directly defined by the stem as a mental image of a spatial layout. Distractors are other cognition/problem-solving terms. |
| 27 | linked | Displacement（27.7） | — | Projection（B）、Reaction Formation（C）、Regression（D）、Rationalization（A） | takes out his anger on his best friend（未收录）、displacement、rationalization、projection、reaction formation、regression | The item tests the psychodynamic defense mechanism of displacement: anger from one source is redirected toward a safer target. All four distractors are other defense mechanisms, so each is a legitimate confusable. |
| 28 | linked | Language acquisition device（26.8） | Overgeneralization | — | overregularizing（未收录）、logical grammatical rule（未收录）、Noam Chomsky（未收录） | Core concept is Chomsky's language acquisition device (nativist view), supported by overgeneralization/overregularization and grammar. Confusables are other theorists in options who are near-misses in developmental/learning psychology. |
| 29 | linked | Foot-in-the-door technique（67.7） | — | — | sign a petition（未收录）、donation（未收录）、foot in the door（未收录）、door in the face（未收录） | Stem describes a small initial request (signing a petition) followed by a larger request (donation), the defining pattern of foot-in-the-door. Door-in-the-face is the only same-domain distractor; lowball, that's not all, and bait and switch are related compliance tactics but not in the candidate list. |
| 30 | linked | Meta-analysis（68.8） | — | Naturalistic observation（B）、Case study method（E）、Survey method（D）、Experiment（C） | relationship between weight loss and mood（未收录）、analyzes the results of several previous studies（未收录）、Meta-analysis、Naturalistic observation、An experiment（未收录）、A survey（未收录）、A case study（未收录） | Core is meta-analysis because the stem describes statistically combining results of several prior studies. Correlation is supporting since the underlying interest is a relationship between two variables, but the tested strategy is meta-analysis. |
| 31 | linked | Observational learning（76.9） | — | Operant conditioning（A）、Classical conditioning（B） | Observational learning、Operant conditioning、Classical conditioning、Prepared conditioning（未收录）、Self-actualization | The stem refers to unspecified data, so the core is derived from the correct option. Self-actualization is unrelated to learning and is not treated as a confusable. |
| 32 | linked | Wernicke’s area（70.2） | — | — | aphasia、Wernicke’s area、Occipital lobe（未收录）、Parietal lobe（未收录） | Core is Wernicke's area as the language-comprehension region whose damage produces aphasia; aphasia is supporting. Broca's area and temporal lobe are the most tempting near-miss distractors. |
| 33 | linked | Stimulants（62.8） | Psychoactive drugs | — | psychoactive drugs、nervous system activity（未收录）、Cocaine（未收录）、Alcohol（未收录）、Morphine（未收录）、barbiturate（未收录） | The item tests classification of cocaine as a stimulant (increases nervous system activity). Heroin (E) is also an opioid depressant but omitted as confusable to keep the list focused on the most tempting near-misses. |
| 34 | linked | Cerebellum（75.4） | Hindbrain | Amygdala（A）、Hippocampus（B） | typing smoothly（未收录）、cerebellum、amygdala、hippocampus | Cerebellum coordinates habitual muscle movements such as typing. Amygdala and hippocampus are same-domain brain-structure distractors; pituitary gland and lateral ventricle are unrelated. |
| 35 | linked | Algorithm（75.0） | — | Heuristic（A） | anagram（未收录）、rearranging every letter one at a time（未收录）、algorithm、heuristic | The exhaustive letter-by-letter method is a step-by-step procedure guaranteeing the solution, i.e., an algorithm. The faster letter-pairing shortcut she avoided is a heuristic, making option A the tempting near-miss. |
| 36 | linked | Classical conditioning（80.0） | — | Operant conditioning（B）、Discrimination (conditioning)（C）、Observational learning（D） | Classical conditioning、Operant conditioning、Discrimination、Observational learning、learning processes（未收录） | The stem describes a neutral stimulus (spider) becoming associated with a bite, producing a learned fear response, which is classical conditioning. Scaffolding (E) is unrelated to learning processes in this context and is omitted from confusables. |
| 37 | linked | Sensory interaction（30.0） | Gustation | Vestibular sense（A） | taste（未收录）、Sensory interaction、Vestibular sense、Just-noticeable difference（未收录） | The item tests sensory interaction: a cold affecting smell, which in turn alters taste. Gustation is a supporting concept because taste is the affected sense. |
| 38 | linked | Hemispheric specialization (brain lateralization)（32.9） | — | Hemispheres（D） | cerebral hemispheres（未收录）、specialized（未收录）、right-brained（未收录）、left-brained（未收录） | Core is hemispheric specialization; hemispheres is supporting. Option D is the only same-domain near-miss (hemisphere-based claim), so it is the sole confusable. |
| 39 | linked | Negative reinforcement（75.1） | — | Partial-reinforcement effect（A） | Negative（未收录）、Positive（未收录）、Intermittent、Vicarious（未收录） | Negative reinforcement is tested: removing the uncle's requests strengthens garbage-taking. Positive reinforcement is the key near-miss distractor. |
| 40 | needs_review | Transference（64.4） | — | Resistance（A）、Catharsis（D）、Reaction Formation（E） | psychoanalytically oriented therapist（未收录）、acts very angry toward the therapist（未收录）、just as she acts toward her mother（未收录）、transference、resistance、catharsis、reaction formation | Countertransference (option C) has no candidate concept; omitted from confusables. Core is transference: client redirects feelings about her mother onto the therapist. |
| 41 | linked | Attribution theory（68.8） | Attribution | Social cognition（A）、Persuasion（E） | evaluates the causes（未收录）、other people’s behavior（未收录）、attribution、social cognition、cognitive dissonance（未收录）、persuasion | Compliance (B) is a social-influence concept but not a close near-miss to attribution, so it was omitted from confusables. |
| 42 | linked | Learned helplessness（70.5） | — | — | learned helplessness | Learned helplessness is the only candidate concept in the same domain as the item; distractors reference unrelated concepts (teacher quality, tutoring, effort optimism) and do not map to narrow-domain near-misses. |
| 43 | linked | Identity（30.0） | — | Intimacy（D） | Erik Erikson（未收录）、primary conflict（未收录）、teenager（未收录）、Identity versus role confusion（未收录）、Intimacy versus isolation（未收录） | Core is Erikson's adolescent identity-versus-role-confusion stage. Autonomy and intimacy are included as confusable Erikson stages; initiative, generativity, and stagnation lack dedicated candidate keys. |
| 44 | linked | Hypnosis（30.0） | — | Control group（B） | hypnosis、hypnotized（未收录）、control group | The item tests the methodological difficulty of verifying hypnosis (no reliable indicator), which maps to the Hypnosis concept; the control-group distractor is a near-miss research-design concept. |
| 45 | linked | Correlation coefficient（73.9） | Negative correlation | — | strongest correlation（未收录）、negative .90（未收录） | The item tests understanding that correlation strength is the absolute value of the coefficient, so -.90 is strongest. C04 (correlation coefficient) captures the statistic; C01/C02 support the relationship and sign interpretation. |
| 46 | linked | Predictive validity（72.1） | Validity | Content validity（B）、Face validity（A）、Test-retest reliability（D）、Split-half reliability（E） | predict（未收录）、correlates the test score（未收录）、criterion-related validity（未收录）、face validity、content validity、test-retest reliability、split-half reliability | Criterion-related validity is the umbrella term; predictive validity (C03) is the specific form tested here because the test forecasts future pilot performance. C01 Validity is a broader supporting concept. |
| 47 | linked | Self（30.0） | — | Bottom-up processing（A） | recall、personally relevant（未收录）、Self-reference effect（未收录）、Visual imagery（未收录）、Dual encoding（未收录）、Bottom-up processing | The correct answer is the self-reference effect, which is best captured by the candidate concept 'Self' (C03). Supporting concepts Recall (C02) and Deeply encoded (C04) help explain why personally relevant information is better remembered. |
| 48 | linked | Psychological disorder（67.5） | — | — | abnormal（未收录） | The item tests the dysfunction/impairment criterion of psychological disorder; the correct option is the only one describing interference with life functioning. |
| 49 | linked | Big Five personality traits（77.5）、Traits（72.7） | Personality | Collective unconscious（B）、Unconscious（D） | five-factor model of personality（未收录）、personality traits（未收录）、five major traits（未收录）、personality、psychosexual stages（未收录）、collective unconscious、unconscious | Core is the Big Five trait model; the correct option states that most traits derive from the five major traits. Distractors reference psychodynamic alternatives (Freud, Jung, conscious/unconscious). |
| 50 | linked | Cones（74.3） | — | Rods（A）、Optic chiasm（E） | vibrant colors（未收录）、cones、dim light（未收录）、rods、optic chiasm | Core is cone function for color vision in dim light; rods are a near-miss photoreceptor distractor. |
| 51 | linked | Object permanence（77.0） | — | Conservation（A）、Egocentric（B） | object permanence、conservation、egocentrism、size constancy | Decentration (E) is a loosely related Piagetian term but not a close enough near-miss to include as a confusable. |
| 52 | linked | Fixed-ratio (FR) schedule（64.3） | — | — | rewarded every third trial（未收录）、reinforcement schedules（未收录）、Fixed-ratio（未收录）、Variable-ratio（未收录）、Fixed-interval（未收录）、Variable-interval（未收录）、Continuous（未收录） | The item tests distinguishing ratio (response-based) from interval (time-based) schedules and fixed from variable; 'every third trial' signals a set number of responses, i.e., fixed-ratio. |
| 53 | linked | Bipolar disorder（71.1） | — | Major depressive disorder（D）、Obsessive-compulsive disorder (OCD)（B）、Bulimia（C）、Conversion disorder（E） | devastating sadness（未收录）、weight loss（未收录）、feelings of worthlessness（未收录）、inability to concentrate（未收录）、tremendous elation（未收录）、excessive excitement（未收录）、racing thoughts（未收录）、elevated self-esteem（未收录）、has not slept for several days（未收录）、Bipolar disorder、Major depressive disorder、Obsessive-compulsive disorder、Bulimia nervosa、Conversion disorder | Core is bipolar disorder because the stem describes both depressive and manic episodes. Major depressive disorder is the key confusable since it matches only the depressive half. |
| 54 | linked | Mode（76.6） | Mean | Percentile rank（A）、Standard deviation（B）、Negatively skewed distribution（D） | normally distributed（未收录）、percentile rank、standard deviation、variance（未收录）、skew（未收录）、mode | Adding a constant shifts all measures of central tendency (mean, median, mode) but leaves spread and shape unchanged; the mode is the only listed measure that must change. |
| 55 | linked | Corpus callosum（30.0） | — | Narcolepsy（C）、Obsessive-compulsive disorder (OCD)（D）、Major depressive disorder（E） | corpus callosum、Epilepsy（未收录）、Schizophrenia、Narcolepsy、Obsessive-compulsive disorder、Major depressive disorder | Epilepsy is not in the candidate list, so it is recorded as a keyword with concept=null. The core concept is the corpus callosum, whose severing (split-brain procedure) is used to treat severe epilepsy. |
| 56 | linked | Cognitive therapy（77.8） | Cognitive restructuring | — | cognitive therapist（未收录）、anxiety（未收录）、changing the way she interprets her circumstances（未收录） | Cognitive therapy is the core; cognitive restructuring is a supporting synonym. Options A and B are operant-conditioning distractors. |
| 57 | linked | Independent variable（90.3） | Dependent variable | — | independent variable、Method of note-taking（未收录）、Grades（未收录） | The item tests identification of the independent variable as the manipulated factor (note-taking method). Grades is the dependent variable and serves as the main confusable distractor. |
| 58 | linked | In-group bias（71.2） | — | Scapegoat theory（A）、Groupthink（D）、Social facilitation（B） | athletes from their own country（未收录）、athletes from other countries cheat（未收录）、In-group bias、Scapegoat theory、Social facilitation、Groupthink、Mere-exposure effect | The stem illustrates in-group bias by favoring one's own national group and distrusting out-group athletes. Supporting concept C53 (ingroup) is implied by 'their own country' but not named verbatim; it is included only as a conceptual aid. |
| 59 | linked | Savant syndrome（30.0） | — | Antisocial personality disorder（D） | IQ of 60（未收录）、complex calculations in his head（未收录）、does not engage socially（未收录）、Savant syndrome | Core is savant syndrome: limited mental ability combined with an exceptional specific skill (calculation). IQ is supporting context. Antisocial personality disorder and Down syndrome are the narrow-domain confusables. |
| 60 | linked | Motor development（31.6） | — | — | fine motor skills、gross motor skills、balance（未收录）、visual acuity（未收录）、hemispheric specialization | Fine motor skills are a subcomponent of motor development (C01); gross motor skills (option D) is the same broad domain but not a near-miss for the specific fine-motor deficit. |
| 61 | linked | Cognitive dissonance theory（74.4） | — | Homeostasis（A）、Approach-avoidance conflict（D）、Social facilitation（E） | behavior that is against their principles（未收录）、cognitive dissonance（未收录） | The stem describes inconsistency between behavior and principles, which is the core of cognitive dissonance. Homeostasis and approach-avoidance conflict are plausible tension-related distractors; social facilitation is a weaker social psychology distractor. |
| 62 | linked | Facial expressions（35.5） | Sociobiology | Polygraph（C） | emotions（未收录）、universal emotions（未收录）、polygraph、Emotional intelligence、Type A personality（未收录）、cerebellum | Correct answer reflects the universality of basic emotions (facial expressions). Polygraph, emotional intelligence, Type A, and cerebellum appear only in distractors and are treated as confusables, not core. |
| 63 | linked | Mere exposure effect（74.4） | — | Companionate love（E）、Altruism（D）、Social trap（A） | social psychological term（未收录）、attraction（未收录）、Mere-exposure effect、Companionate love、Altruism、Social trap | The stem describes repeated daily exposure leading to fondness, which is the mere-exposure effect. Proximity is a plausible supporting concept but is not an option; it is included only as weak support. |
| 64 | linked | Serotonin selective reuptake inhibitor drugs (SSRIs)（27.0） | — | — | selective serotonin reuptake inhibitors (SSRIs)（未收录）、reuptake | Figure-based item; correct option C indicates the synapse/sending neuron where reuptake occurs. No candidate distractor concepts are present in the options (A-E are figure labels), so confusables are empty. |
| 65 | linked | Neurotransmitters（69.3） | — | — | neurotransmitter（未收录）、dopamine（未收录） | Figure-based item; correct option E corresponds to a brain region (likely a dopamine pathway), but no candidate concept names that region. Core is neurotransmitter communication; dopamine itself is not in the candidate list. |
| 66 | linked | Sampling bias（30.0） | Sampling | Social desirability bias（D）、Debriefing（A） | generalizable（未收录）、sampling bias、ask only their friends to participate（未收录）、survey、social desirability bias、placebo effects（未收录）、debriefing | Core is sampling bias: selecting only friends yields an unrepresentative sample, so results cannot be generalized. Convenience sampling and sampling are supporting mechanisms. Participant bias (C) is a loosely related distractor and was omitted as a confusable. |
| 67 | linked | Selective attention（70.8） | — | Sensory adaptation（C）、Perceptual constancy（A）、Blindsight（D） | cell phones while driving（未收录）、accidents、selective attention | The stem describes divided attention: using a phone while driving requires focusing awareness on one stimulus (the phone) at the expense of another (driving), which is selective attention. Accidents is a mentioned outcome, not the tested concept. |
| 68 | linked | Behavioral perspective（76.2） | — | Gestalt psychology（E） | Token economies（未收录）、theoretical perspective（未收录）、Behavioral（未收录）、Psychodynamic（未收录）、Humanistic（未收录）、Cognitive（未收录）、Gestalt | Token economy is the treatment technique; the tested perspective is behavioral because tokens are reinforcers based on conditioning. Supporting concept C01 clarifies the technique, while core C02 identifies the theoretical perspective. |
| 69 | linked | Priming（64.0） | — | Habituation（B）、Generalization（D）、Discrimination (conditioning)（E）、Conditioned response (CR)（C） | Priming、watched a cartoon about a sarcastic rabbit（未收录）、Habituation、Conditioned response、Stimulus generalization（未收录）、Discrimination | Priming is the core: prior exposure to the rabbit cartoon activates the rabbit interpretation of the ambiguous figure. Recognition is a plausible supporting process for identifying the image. |
| 70 | linked | Social loafing（72.2） | — | — | social loafing、group science project（未收录）、barely works（未收录） | Correct option C directly illustrates reduced individual effort in a group setting, the defining feature of social loafing. Diffusion of responsibility is a related explanatory mechanism. |
| 71 | linked | Unconditional positive regard（74.0） | Humanistic therapies | — | unconditional positive regard、accepted him（未收录）、authoritarian parenting（未收录）、ambivalent attachment（未收录） | Stem describes Rogers' unconditional positive regard (blanket acceptance) applied by parents; authoritarian parenting and ambivalent attachment are the same-domain near-miss distractors. |
| 72 | linked | Conditioned stimulus (CS)（74.7） | Classical conditioning、Unconditioned stimulus (US or UCS) | Conditioned response (CR)（D）、Unconditioned response (UR or UCR)（C） | conditioned stimulus、Sweetened water（未收录）、paired（未收录）、The drug（未收录） | The item tests identification of the CS in a classical conditioning scenario; the drug is the US and immune weakening is the UR/CR. |
| 73 | linked | Hallucinations（71.3） | Schizophrenia、Positive symptoms | — | schizophrenia、Hallucinations、Multiple personalities（未收录）、Mood swings（未收录）、Amnesia（未收录） | Hallucinations are a positive symptom of schizophrenia; the item tests recognition of a characteristic symptom. Frequent hand washing (D) is an OCD-related compulsion and not a close confusable in the schizophrenia domain, so it was omitted. |
| 74 | linked | Social facilitation（79.5） | Social impairment | Bystander effect（A） | performance（未收录）、crowd watching her gets larger（未收录）、social facilitation、bystander effect | The item tests social facilitation: improved performance in the presence of others. The bystander effect is the only same-domain distractor worth flagging; the others are unrelated. |
| 75 | linked | Linguistic relativity hypothesis（27.5） | — | Language acquisition device（D） | linguistic relativity hypothesis、language、cognition、concepts、culture、language acquisition device | Core is Whorf's linguistic relativity hypothesis; linguistic determinism (C06) is a close supporting synonym. Distractors A, C, and E invoke universal concepts, private speech, and schemas, which are only loosely related and omitted as confusables. |
| 76 | linked | Major depressive disorder（77.5） | — | Specific phobia（E） | selective serotonin reuptake inhibitor、Major depressive（未收录）、Schizophrenia、Somatic symptom（未收录）、Antisocial personality（未收录）、Specific phobia | Core concept is major depressive disorder, inferred from the SSRI treatment clue. Supporting concepts include SSRI and antidepressant drugs. Confusables are limited to same-domain disorder categories from the options. |
| 77 | linked | Insight learning（70.3） | Insight | Latent learning（D）、Spontaneous recovery（A）、Discrimination (conditioning)（C） | suddenly thinks of a solution（未收录）、insight learning、latent learning、spontaneous recovery、discrimination | The item tests insight learning: Dylan's sudden realization of the solution. Social learning (B) is only loosely related and omitted as a confusable. |
| 78 | linked | Anxiety disorders（73.4） | Social anxiety disorder | — | afraid to leave his house（未收录）、apprehensive（未收录）、go out in public（未收录）、Anxiety（未收录） | The stem describes fear and apprehension about leaving the house and going out in public, which points to an anxiety disorder category. Social anxiety disorder is a plausible supporting concept, but the correct answer is the broader Anxiety category. |
| 79 | linked | Stress（71.3）、Endocrine system（64.1） | — | Hippocampus（B） | Stress hormones（未收录）、immune system（未收录）、hippocampus、hardening her arteries（未收录） | Core is stress (C04) as the trigger and endocrine/hormonal mechanism (C02) affecting immunity; psychoneuroimmunology (C05) supports the link. Distractors A and B are plausible stress-related biological effects but not immune suppression. |
| 80 | linked | Secure attachment（72.3） | — | — | attachment、Secure（未收录）、Avoidant（未收录）、Anxious ambivalent（未收录）、Resistant（未收录） | Jeremy's confident exploration, distress at separation, quick soothing, and happy reunion match secure attachment. Disorganized/disoriented (E) is a same-domain distractor but is not in the candidate list, so it is omitted from confusables. |
| 81 | linked | Identical twins (monozygotic twins)（72.9） | Intelligence | — | biological basis for behavior（未收录）、Identical twins、intelligence | The item tests the heritability/biological basis inference from identical twins reared apart; intelligence is the trait measured, supporting the twin evidence. |
| 82 | linked | Amygdala（76.2） | Aggression | Memory（C）、Sleep（E） | amygdala、Aggression、Memory loss（未收录）、Sleep | The item tests the amygdala's role in emotion/aggression. Memory loss is a near-miss tied to the hippocampus; sleep is a looser limbic-system distractor. |
| 83 | linked | Correlation（92.2）、Positive correlation（45.0） | — | Negative correlation（C） | scatterplot、positive correlation、negative correlation、no relationship（未收录） | Core is the correlation relationship shown by the scatterplot, specifically positive correlation. Scatterplot supports reading the graph. |
| 84 | linked | Evolutionary (or Darwinian) Perspective（39.6） | — | — | evolutionary approach（未收录）、sexual attraction（未收录）、potential mates（未收录）、appear fertile（未收录） | The item tests the evolutionary perspective (C25) applied to mate selection; 'appear fertile' is the correct answer but has no dedicated candidate concept. Distractors (financial resources, social status, height, education) are not near-miss concepts in the candidate list, so no confusables. |
| 85 | linked | Drive reduction theory（76.0） | Drive | Self-determination theory（C）、Achievement motivation（E） | theory of motivation（未收录）、intense hunger（未收录）、Drive reduction（未收录）、Arousal（未收录）、Self-determination theory、Achievement motivation | Drive reduction theory is the core because hunger creates a biological need and drive to eat. Social learning (B) is a learning theory, not a motivation theory, so it is not a close confusable. |
| 86 | linked | Standard deviation（87.8） | Mean | — | mean、standard deviation、within one standard deviation of the mean（未收录） | Item tests applying the standard deviation to identify scores within one SD of the mean (76-84); 77 is the only option in range. |
| 87 | linked | Supertasters（24.7） | Taste buds | — | supertaster（未收录）、very sensitive to hot peppers（未收录）、taste buds、learned（未收录） | Supertasting is a biological density-of-taste-buds trait; the correct inference is heightened sensitivity. Option C inverts the actual density, and E wrongly frames it as observational learning. |
| 88 | linked | Occipital lobes（73.9） | — | — | occipital lobe（未收录）、visual deficit（未收录） | The item tests knowledge that the occipital lobe handles visual information; the correct answer is visual deficit. |
| 89 | linked | Projective tests（72.4） | Rorschach inkblot test、Thematic apperception test (TAT) | — | Rorschach inkblot test、Thematic Apperception Test (TAT)、Projective（未收录）、Aptitude（未收录） | The item asks for the test category that includes Rorschach and TAT; the core concept is projective tests, with the two specific projective instruments as supporting concepts. |
| 90 | linked | Delusions（69.9） | — | Hallucinations（C）、Catatonia（B）、Flat affect（E） | delusions of reference（未收录）、visual hallucinations（未收录）、catatonia、flat affect | The item tests delusions of reference, a subtype of delusions (C01). Hallucinations, catatonia, and flat affect are same-domain schizophrenia-spectrum distractors. |
| 91 | linked | Critical period（72.4） | Language | Grammar（B） | critical period、second languages（未收录）、pronunciation（未收录）、grammar | Core is the critical period for second-language acquisition; the correct answer reflects that pronunciation is most affected by age of acquisition. Grammar in option B is a near-miss language concept. |
| 92 | linked | Procedural memory（38.6） | Implicit memory | — | Memories of well-learned skills（未收录）、riding a bicycle（未收录）、procedural（未收录）、semantic（未收录）、declarative（未收录）、iconic（未收录）、echoic（未收录） | Core is procedural memory (C01), directly matching the correct answer. Implicit memory (C02) is a supporting concept since procedural memory is a form of implicit/nondeclarative memory. Confusables are the other memory-type options in the same narrow domain. |
| 93 | linked | Schizophrenia（48.8） | — | Specific phobia（E） | antipsychotic medication（未收录）、Schizophrenia | The question tests knowledge that antipsychotic medication is the primary treatment for schizophrenia. The core concept is schizophrenia, supported by antipsychotic drugs. |
| 94 | linked | Memory（30.0） | — | Delusions（B）、Dissociation（A） | dementia（未收录）、Deterioration in memory（未收录）、Dissociation、Delusions、Compulsions（未收录） | Core concept is memory deterioration as the hallmark symptom of dementia. Alzheimer's disease is a supporting concept because it is a form of dementia characterized by deteriorating memory. Confusables are drawn from wrong options that are psychiatric symptoms in the same broad domain. |
| 95 | linked | Collective unconscious（55.0） | Archetypes、Unconscious | Id（A）、Ego（B）、Superego（C） | Carl Jung（未收录）、Collective unconscious、Id、Ego、Superego | Core is Jung's collective unconscious; archetypes and unconscious are supporting. Personal unconscious (D) is a near-miss but has no candidate key, so omitted from confusables. |
| 96 | linked | Persistent depressive disorder（62.8） | — | — | lacked enthusiasm for work and other activities（未收录）、for a number of years（未收录）、poor appetite（未收录）、fatigued（未收录）、Persistent depressive（未收录）、Bipolar（未收录）、Social anxiety（未收录）、Generalized anxiety（未收录）、Antisocial personality（未收录） | Core is persistent depressive disorder because the stem emphasizes long-lasting (years) low enthusiasm plus appetite and fatigue; major depressive disorder is the key near-miss but is not an option, so it is listed as a confusable tied to option B's depressive-disorder family. |
| 97 | linked | Babinski reflex（20.0） | Reflexes | Grasping reflex（B） | Babinski reflex | The item tests knowledge of the Babinski reflex specifically; the general concept of reflexes (C04) supports understanding that it is an inborn automatic response. |
| 98 | linked | Industrial-organizational (I/O) psychology（25.0） | Personnel psychology、Organizational psychology | — | field of psychology（未收录）、hiring（未收录）、basic training（未收录）、management leadership skills training（未收录）、Industrial/organizational（未收录）、Quantitative（未收录）、Clinical（未收录） | I/O psychology is the core; personnel and organizational psychology are its subfields and support the hiring/training and leadership aspects. Quantitative and clinical are the nearest same-domain distractors (other applied/research fields). |
| 99 | linked | Hippocampus（70.8） | Anterograde amnesia | Hypothalamus（A）、Cerebellum（B）、Thalamus（D） | brain（未收录）、infantile amnesia（未收录）、Hippocampus | Core is the hippocampus as the late-developing memory structure explaining infantile amnesia; supporting link to anterograde amnesia is indirect. Distractors are other brain structures, so confusables are limited to same-domain brain regions. |
| 100 | linked | Antisocial personality disorder（72.0） | Personality disorders、Cluster B | — | superficially charming（未收录）、exploiting people for his own gain（未收录）、impulsive（未收录）、irresponsible（未收录）、disregards social norms（未收录）、Antisocial personality（未收录）、Schizoid personality（未收录）、Dissociative identity（未收录）、Conversion（未收录）、Bipolar（未收录） | Core is antisocial personality disorder; supporting concepts include personality disorders broadly and Cluster B impulsivity. Schizoid personality is a Cluster A disorder and is less directly confusable than the other distractors, so it is listed only as a keyword. |

## 覆盖

- linked：96
- needs_review：1
- no_match：0

## 校验记录

- Q4（psychology-ap-2016-mcq-004）：confusable 'Retinal disparity' is not named in option 'B' and is not in the core subheading; dropped
- Q4（psychology-ap-2016-mcq-004）：keyword 'patch over the eye': not a known alias of 'Monocular depth cues'; stored without a KP
- Q4（psychology-ap-2016-mcq-004）：keyword 'distance objects are from her': not a known alias of 'Depth perception'; stored without a KP
- Q4（psychology-ap-2016-mcq-004）：keyword 'Binocular disparity': not a known alias of 'Retinal disparity'; stored without a KP
- Q5（psychology-ap-2016-mcq-005）：keyword 'client-centered therapy': not a known alias of 'Person-centered therapy'; stored without a KP
- Q5（psychology-ap-2016-mcq-005）：keyword 'rephrases things that Gerry has said': not a known alias of 'Active listening'; stored without a KP
- Q5（psychology-ap-2016-mcq-005）：keyword 'asks for clarification': not a known alias of 'Active listening'; stored without a KP
- Q6（psychology-ap-2016-mcq-006）：keyword 'same test': not a known alias of 'Test-retest reliability'; stored without a KP
- Q6（psychology-ap-2016-mcq-006）：keyword 'test scores are similar': not a known alias of 'Reliability'; stored without a KP
- Q6（psychology-ap-2016-mcq-006）：keyword 'two administrations': not a known alias of 'Test-retest reliability'; stored without a KP
- Q7（psychology-ap-2016-mcq-007）：confusable 'Basal metabolic rate' is not named in option 'D' and is not in the core subheading; dropped
- Q7（psychology-ap-2016-mcq-007）：keyword 'basal metabolism rate': not a known alias of 'Basal metabolic rate'; stored without a KP
- Q8（psychology-ap-2016-mcq-008）：keyword 'levels of processing': not a known alias of 'Levels of processing model'; stored without a KP
- Q8（psychology-ap-2016-mcq-008）：keyword 'memorize each fact': not a known alias of 'Shallowly encoded'; stored without a KP
- Q8（psychology-ap-2016-mcq-008）：keyword 'relate the new information to things she has experienced': whole/long option text; dropped
- Q9（psychology-ap-2016-mcq-009）：supporting 'Well-being' is not in the correct option or the core subheading; dropped
- Q10（psychology-ap-2016-mcq-010）：confusable 'Young-Helmholtz trichromatic (three-color) theory' is not named in option 'B' and is not in the core subheading; dropped
- Q10（psychology-ap-2016-mcq-010）：keyword 'color vision': not a known alias of 'Opponent-process theory (color vision)'; stored without a KP
- Q10（psychology-ap-2016-mcq-010）：keyword 'Afterimages': not a known alias of 'Afterimage'; stored without a KP
- Q10（psychology-ap-2016-mcq-010）：keyword 'Feature detection': not a known alias of 'Feature detectors'; stored without a KP
- Q11（psychology-ap-2016-mcq-011）：supporting 'Humanist Perspective' is not in the correct option or the core subheading; dropped
- Q11（psychology-ap-2016-mcq-011）：confusable 'Behavioral perspective' is not named in option 'A' and is not in the core subheading; dropped
- Q11（psychology-ap-2016-mcq-011）：confusable 'Psychodynamic Perspective' is not named in option 'B' and is not in the core subheading; dropped
- Q11（psychology-ap-2016-mcq-011）：keyword 'Humanism': not a known alias of 'Humanist Perspective'; stored without a KP
- Q12（psychology-ap-2016-mcq-012）：supporting 'Motivation' is not in the correct option or the core subheading; dropped
- Q12（psychology-ap-2016-mcq-012）：confusable 'Drive reduction theory' is not named in option 'B' and is not in the core subheading; dropped
- Q12（psychology-ap-2016-mcq-012）：confusable 'Homeostasis' is not named in option 'A' and is not in the core subheading; dropped
- Q12（psychology-ap-2016-mcq-012）：confusable 'Cognitive dissonance theory' is not named in option 'E' and is not in the core subheading; dropped
- Q12（psychology-ap-2016-mcq-012）：keyword 'Incentive theories of motivation': not a known alias of 'Incentive'; stored without a KP
- Q12（psychology-ap-2016-mcq-012）：keyword 'external stimuli': not a known alias of 'Incentive'; stored without a KP
- Q12（psychology-ap-2016-mcq-012）：keyword 'physiological equilibrium': not a known alias of 'Homeostasis'; stored without a KP
- Q12（psychology-ap-2016-mcq-012）：keyword 'internal states of tension': not a known alias of 'Drive reduction theory'; stored without a KP
- Q12（psychology-ap-2016-mcq-012）：keyword 'cognitive dissonance': not a known alias of 'Cognitive dissonance theory'; stored without a KP
- Q13（psychology-ap-2016-mcq-013）：keyword 'earlier Japanese vocabulary was competing with the new Chinese words': whole/long option text; dropped
- Q14（psychology-ap-2016-mcq-014）：supporting 'Sociobiology' is not in the correct option or the core subheading; dropped
- Q14（psychology-ap-2016-mcq-014）：confusable 'Telegraphic speech' is not named in option 'A' and is not in the core subheading; dropped
- Q14（psychology-ap-2016-mcq-014）：confusable 'Human factors psychology' is not named in option 'E' and is not in the core subheading; dropped
- Q14（psychology-ap-2016-mcq-014）：keyword 'evolutionary psychologist': not a known alias of 'Evolutionary (or Darwinian) Perspective'; stored without a KP
- Q14（psychology-ap-2016-mcq-014）：keyword 'innate fear of the dark': not a known alias of 'Sociobiology'; stored without a KP
- Q14（psychology-ap-2016-mcq-014）：keyword 'first words': not a known alias of 'Telegraphic speech'; stored without a KP
- Q14（psychology-ap-2016-mcq-014）：keyword 'features of a car': not a known alias of 'Human factors psychology'; stored without a KP
- Q15（psychology-ap-2016-mcq-015）：keyword 'praised': not a known alias of 'Positive reinforcement'; stored without a KP
- Q16（psychology-ap-2016-mcq-016）：supporting 'Smell (Olfaction)' is not in the correct option or the core subheading; dropped
- Q16（psychology-ap-2016-mcq-016）：keyword 'no longer detects the smell': not a known alias of 'Sensory adaptation'; stored without a KP
- Q16（psychology-ap-2016-mcq-016）：keyword 'strong odor of chocolate chip cookies': not a known alias of 'Smell (Olfaction)'; stored without a KP
- Q17（psychology-ap-2016-mcq-017）：keyword 'Specific phobia disorder': not a known alias of 'Specific phobia'; stored without a KP
- Q18（psychology-ap-2016-mcq-018）：supporting 'Social learning theory' is not in the correct option or the core subheading; dropped
- Q18（psychology-ap-2016-mcq-018）：confusable 'Operant conditioning' is not named in option 'C' and is not in the core subheading; dropped
- Q18（psychology-ap-2016-mcq-018）：confusable 'Specific phobia' is not named in option 'E' and is not in the core subheading; dropped
- Q18（psychology-ap-2016-mcq-018）：keyword 'social learning theorist': not a known alias of 'Social learning theory'; stored without a KP
- Q18（psychology-ap-2016-mcq-018）：keyword 'fear of flying': not a known alias of 'Specific phobia'; stored without a KP
- Q18（psychology-ap-2016-mcq-018）：keyword 'observed someone else’s fear of flying': not a known alias of 'Observational learning'; stored without a KP
- Q19（psychology-ap-2016-mcq-019）：supporting 'Information processing model' is not in the correct option or the core subheading; dropped
- Q19（psychology-ap-2016-mcq-019）：confusable 'Concrete operational stage' is not named in option 'C' and is not in the core subheading; dropped
- Q19（psychology-ap-2016-mcq-019）：keyword 'Jean Piaget’s stages of cognitive development': not a known alias of 'Stage theories'; stored without a KP
- Q21（psychology-ap-2016-mcq-021）：supporting 'Psychoanalysis (theory)' is not in the correct option or the core subheading; dropped
- Q21（psychology-ap-2016-mcq-021）：keyword 'Sigmund Freud': not a known alias of 'Psychoanalysis (theory)'; stored without a KP
- Q21（psychology-ap-2016-mcq-021）：keyword 'personality structure': not a known alias of 'Personality'; stored without a KP
- Q21（psychology-ap-2016-mcq-021）：keyword 'moral values': not a known alias of 'Superego'; stored without a KP
- Q22（psychology-ap-2016-mcq-022）：confusable 'Parasympathetic nervous system' is not named in option 'D' and is not in the core subheading; dropped
- Q22（psychology-ap-2016-mcq-022）：keyword 'increase in his breathing and heart rate': not a known alias of 'Alarm reaction'; stored without a KP
- Q22（psychology-ap-2016-mcq-022）：keyword 'Parasympathetic response': not a known alias of 'Parasympathetic nervous system'; stored without a KP
- Q23（psychology-ap-2016-mcq-023）：supporting 'Cognitive learning' is not in the correct option or the core subheading; dropped
- Q23（psychology-ap-2016-mcq-023）：keyword 'campus tour': not a known alias of 'Latent learning'; stored without a KP
- Q23（psychology-ap-2016-mcq-023）：keyword 'Stimulus generalization': not a known alias of 'Generalization'; stored without a KP
- Q24（psychology-ap-2016-mcq-024）：supporting 'REM sleep' is not in the correct option or the core subheading; dropped
- Q24（psychology-ap-2016-mcq-024）：keyword 'act out their dreams': not a known alias of 'REM sleep behavior disorder'; stored without a KP
- Q24（psychology-ap-2016-mcq-024）：keyword 'first sleep cycle': not a known alias of 'Sleep cycle'; stored without a KP
- Q25（psychology-ap-2016-mcq-025）：supporting 'Independent variable' is not in the correct option or the core subheading; dropped
- Q25（psychology-ap-2016-mcq-025）：supporting 'Dependent variable' is not in the correct option or the core subheading; dropped
- Q25（psychology-ap-2016-mcq-025）：confusable 'Descriptive statistics' is not named in option 'A' and is not in the core subheading; dropped
- Q25（psychology-ap-2016-mcq-025）：confusable 'Correlation' is not named in option 'B' and is not in the core subheading; dropped
- Q25（psychology-ap-2016-mcq-025）：confusable 'Qualitative research' is not named in option 'E' and is not in the core subheading; dropped
- Q25（psychology-ap-2016-mcq-025）：keyword 'forming conclusions': not a known alias of 'Inferential statistics'; stored without a KP
- Q25（psychology-ap-2016-mcq-025）：keyword 'Inferential': not a known alias of 'Inferential statistics'; stored without a KP
- Q26（psychology-ap-2016-mcq-026）：confusable 'Insight learning' is not named in option 'E' and is not in the core subheading; dropped
- Q26（psychology-ap-2016-mcq-026）：keyword 'mental image': not a known alias of 'Cognitive map'; stored without a KP
- Q26（psychology-ap-2016-mcq-026）：keyword 'spatial layout': not a known alias of 'Cognitive map'; stored without a KP
- Q26（psychology-ap-2016-mcq-026）：keyword 'insight': not a known alias of 'Insight learning'; stored without a KP
- Q27（psychology-ap-2016-mcq-027）：supporting 'Catharsis' is not in the correct option or the core subheading; dropped
- Q27（psychology-ap-2016-mcq-027）：keyword 'takes out his anger on his best friend': not a known alias of 'Displacement'; stored without a KP
- Q28（psychology-ap-2016-mcq-028）：supporting 'Grammar' is not in the correct option or the core subheading; dropped
- Q28（psychology-ap-2016-mcq-028）：confusable 'Zone of proximal development' is not named in option 'B' and is not in the core subheading; dropped
- Q28（psychology-ap-2016-mcq-028）：confusable 'Classical conditioning' is not named in option 'C' and is not in the core subheading; dropped
- Q28（psychology-ap-2016-mcq-028）：confusable 'Bobo doll experiment' is not named in option 'D' and is not in the core subheading; dropped
- Q28（psychology-ap-2016-mcq-028）：confusable 'Law of effect' is not named in option 'E' and is not in the core subheading; dropped
- Q28（psychology-ap-2016-mcq-028）：keyword 'overregularizing': not a known alias of 'Overgeneralization'; stored without a KP
- Q28（psychology-ap-2016-mcq-028）：keyword 'logical grammatical rule': not a known alias of 'Grammar'; stored without a KP
- Q28（psychology-ap-2016-mcq-028）：keyword 'Noam Chomsky': not a known alias of 'Language acquisition device'; stored without a KP
- Q29（psychology-ap-2016-mcq-029）：confusable 'Door-in-the-face technique' is not named in option 'B' and is not in the core subheading; dropped
- Q29（psychology-ap-2016-mcq-029）：keyword 'sign a petition': not a known alias of 'Foot-in-the-door technique'; stored without a KP
- Q29（psychology-ap-2016-mcq-029）：keyword 'donation': not a known alias of 'Foot-in-the-door technique'; stored without a KP
- Q29（psychology-ap-2016-mcq-029）：keyword 'foot in the door': not a known alias of 'Foot-in-the-door technique'; stored without a KP
- Q29（psychology-ap-2016-mcq-029）：keyword 'door in the face': not a known alias of 'Door-in-the-face technique'; stored without a KP
- Q30（psychology-ap-2016-mcq-030）：supporting 'Correlation' is not in the correct option or the core subheading; dropped
- Q30（psychology-ap-2016-mcq-030）：keyword 'relationship between weight loss and mood': not a known alias of 'Correlation'; stored without a KP
- Q30（psychology-ap-2016-mcq-030）：keyword 'analyzes the results of several previous studies': not a known alias of 'Meta-analysis'; stored without a KP
- Q30（psychology-ap-2016-mcq-030）：keyword 'An experiment': not a known alias of 'Experiment'; stored without a KP
- Q30（psychology-ap-2016-mcq-030）：keyword 'A survey': not a known alias of 'Survey method'; stored without a KP
- Q30（psychology-ap-2016-mcq-030）：keyword 'A case study': not a known alias of 'Case study method'; stored without a KP
- Q31（psychology-ap-2016-mcq-031）：supporting 'Cognitive learning' is not in the correct option or the core subheading; dropped
- Q31（psychology-ap-2016-mcq-031）：confusable 'Biological preparedness' is not named in option 'C' and is not in the core subheading; dropped
- Q31（psychology-ap-2016-mcq-031）：keyword 'Prepared conditioning': not a known alias of 'Biological preparedness'; stored without a KP
- Q32（psychology-ap-2016-mcq-032）：supporting 'Aphasia' is not in the correct option or the core subheading; dropped
- Q32（psychology-ap-2016-mcq-032）：confusable 'Temporal lobes' is not named in option 'C' and is not in the core subheading; dropped
- Q32（psychology-ap-2016-mcq-032）：keyword 'Occipital lobe': not a known alias of 'Occipital lobes'; stored without a KP
- Q32（psychology-ap-2016-mcq-032）：keyword 'Parietal lobe': not a known alias of 'Parietal lobes'; stored without a KP
- Q32（psychology-ap-2016-mcq-032）：校验错误：confusable: option 'B' is not a wrong option
- Q33（psychology-ap-2016-mcq-033）：supporting 'Nervous system' is not in the correct option or the core subheading; dropped
- Q33（psychology-ap-2016-mcq-033）：confusable 'Depressants' is not named in option 'B' and is not in the core subheading; dropped
- Q33（psychology-ap-2016-mcq-033）：confusable 'Barbiturates' is not named in option 'D' and is not in the core subheading; dropped
- Q33（psychology-ap-2016-mcq-033）：confusable 'Opioids' is not named in option 'C' and is not in the core subheading; dropped
- Q33（psychology-ap-2016-mcq-033）：keyword 'nervous system activity': not a known alias of 'Nervous system'; stored without a KP
- Q33（psychology-ap-2016-mcq-033）：keyword 'Cocaine': not a known alias of 'Stimulants'; stored without a KP
- Q33（psychology-ap-2016-mcq-033）：keyword 'Alcohol': not a known alias of 'Depressants'; stored without a KP
- Q33（psychology-ap-2016-mcq-033）：keyword 'Morphine': not a known alias of 'Opioids'; stored without a KP
- Q33（psychology-ap-2016-mcq-033）：keyword 'barbiturate': not a known alias of 'Barbiturates'; stored without a KP
- Q34（psychology-ap-2016-mcq-034）：keyword 'typing smoothly': not a known alias of 'Cerebellum'; stored without a KP
- Q35（psychology-ap-2016-mcq-035）：supporting 'Heuristic' duplicates a confusable; dropped
- Q35（psychology-ap-2016-mcq-035）：keyword 'rearranging every letter one at a time': not a known alias of 'Algorithm'; stored without a KP
- Q36（psychology-ap-2016-mcq-036）：supporting 'Associative learning' is not in the correct option or the core subheading; dropped
- Q36（psychology-ap-2016-mcq-036）：keyword 'learning processes': not a known alias of 'Learning'; stored without a KP
- Q37（psychology-ap-2016-mcq-037）：confusable 'Difference threshold' is not named in option 'B' and is not in the core subheading; dropped
- Q37（psychology-ap-2016-mcq-037）：keyword 'taste': not a known alias of 'Gustation'; stored without a KP
- Q37（psychology-ap-2016-mcq-037）：keyword 'Just-noticeable difference': not a known alias of 'Difference threshold'; stored without a KP
- Q38（psychology-ap-2016-mcq-038）：supporting 'Hemispheres' duplicates a confusable; dropped
- Q38（psychology-ap-2016-mcq-038）：keyword 'cerebral hemispheres': not a known alias of 'Hemispheres'; stored without a KP
- Q38（psychology-ap-2016-mcq-038）：keyword 'specialized': not a known alias of 'Hemispheric specialization (brain lateralization)'; stored without a KP
- Q39（psychology-ap-2016-mcq-039）：supporting 'Reinforcement' is not in the correct option or the core subheading; dropped
- Q39（psychology-ap-2016-mcq-039）：confusable 'Positive reinforcement' is not named in option 'B' and is not in the core subheading; dropped
- Q39（psychology-ap-2016-mcq-039）：confusable 'Vicarious conditioning' is not named in option 'D' and is not in the core subheading; dropped
- Q39（psychology-ap-2016-mcq-039）：keyword 'more likely to take out the garbage in the future': whole/long option text; dropped
- Q39（psychology-ap-2016-mcq-039）：keyword 'Negative': not a known alias of 'Negative reinforcement'; stored without a KP
- Q39（psychology-ap-2016-mcq-039）：keyword 'Positive': not a known alias of 'Positive reinforcement'; stored without a KP
- Q39（psychology-ap-2016-mcq-039）：keyword 'Vicarious': not a known alias of 'Vicarious conditioning'; stored without a KP
- Q40（psychology-ap-2016-mcq-040）：core 'Transference': evidence is not an exact quote from stem/context/correct option
- Q40（psychology-ap-2016-mcq-040）：keyword 'acts very angry toward the therapist': not a known alias of 'Transference'; stored without a KP
- Q40（psychology-ap-2016-mcq-040）：keyword 'just as she acts toward her mother': not a known alias of 'Transference'; stored without a KP
- Q41（psychology-ap-2016-mcq-041）：confusable 'Cognitive dissonance theory' is not named in option 'C' and is not in the core subheading; dropped
- Q41（psychology-ap-2016-mcq-041）：keyword 'evaluates the causes': not a known alias of 'Attribution theory'; stored without a KP
- Q41（psychology-ap-2016-mcq-041）：keyword 'other people’s behavior': not a known alias of 'Attribution theory'; stored without a KP
- Q41（psychology-ap-2016-mcq-041）：keyword 'cognitive dissonance': not a known alias of 'Cognitive dissonance theory'; stored without a KP
- Q42（psychology-ap-2016-mcq-042）：keyword 'Why study? There isn’t anything I can do to improve my Spanish skills.': whole/long option text; dropped
- Q43（psychology-ap-2016-mcq-043）：supporting 'Psychosocial stage theory' is not in the correct option or the core subheading; dropped
- Q43（psychology-ap-2016-mcq-043）：confusable 'Autonomy (Erikson)' is in option 'A' but not in the core's narrow domain; dropped
- Q43（psychology-ap-2016-mcq-043）：keyword 'primary conflict': not a known alias of 'Conflict'; stored without a KP
- Q43（psychology-ap-2016-mcq-043）：keyword 'Identity versus role confusion': not a known alias of 'Identity'; stored without a KP
- Q43（psychology-ap-2016-mcq-043）：keyword 'Autonomy versus shame and doubt': whole/long option text; dropped
- Q43（psychology-ap-2016-mcq-043）：keyword 'Intimacy versus isolation': not a known alias of 'Intimacy'; stored without a KP
- Q44（psychology-ap-2016-mcq-044）：keyword 'hypnotized': not a known alias of 'Hypnosis'; stored without a KP
- Q45（psychology-ap-2016-mcq-045）：supporting 'Correlation' is not in the correct option or the core subheading; dropped
- Q45（psychology-ap-2016-mcq-045）：confusable 'Positive correlation' is not named in option 'D' and is not in the core subheading; dropped
- Q45（psychology-ap-2016-mcq-045）：keyword 'strongest correlation': not a known alias of 'Correlation coefficient'; stored without a KP
- Q45（psychology-ap-2016-mcq-045）：keyword 'negative .90': not a known alias of 'Negative correlation'; stored without a KP
- Q46（psychology-ap-2016-mcq-046）：keyword 'predict': not a known alias of 'Predictive validity'; stored without a KP
- Q46（psychology-ap-2016-mcq-046）：keyword 'correlates the test score': not a known alias of 'Predictive validity'; stored without a KP
- Q46（psychology-ap-2016-mcq-046）：keyword 'criterion-related validity': not a known alias of 'Predictive validity'; stored without a KP
- Q47（psychology-ap-2016-mcq-047）：supporting 'Recall' is not in the correct option or the core subheading; dropped
- Q47（psychology-ap-2016-mcq-047）：supporting 'Deeply encoded' is not in the correct option or the core subheading; dropped
- Q47（psychology-ap-2016-mcq-047）：confusable 'Dual processing' is not named in option 'C' and is not in the core subheading; dropped
- Q47（psychology-ap-2016-mcq-047）：confusable 'Mnemonics' is not named in option 'B' and is not in the core subheading; dropped
- Q47（psychology-ap-2016-mcq-047）：keyword 'personally relevant': not a known alias of 'Self'; stored without a KP
- Q47（psychology-ap-2016-mcq-047）：keyword 'Self-reference effect': not a known alias of 'Self'; stored without a KP
- Q47（psychology-ap-2016-mcq-047）：keyword 'Visual imagery': not a known alias of 'Mnemonics'; stored without a KP
- Q47（psychology-ap-2016-mcq-047）：keyword 'Dual encoding': not a known alias of 'Dual processing'; stored without a KP
- Q48（psychology-ap-2016-mcq-048）：supporting 'Abnormal psychology' is not in the correct option or the core subheading; dropped
- Q48（psychology-ap-2016-mcq-048）：confusable 'Antisocial personality disorder' is not named in option 'C' and is not in the core subheading; dropped
- Q48（psychology-ap-2016-mcq-048）：keyword 'abnormal': not a known alias of 'Abnormal psychology'; stored without a KP
- Q48（psychology-ap-2016-mcq-048）：keyword 'interfere with some aspect of the person’s life': whole/long option text; dropped
- Q49（psychology-ap-2016-mcq-049）：keyword 'five-factor model of personality': not a known alias of 'Big Five personality traits'; stored without a KP
- Q49（psychology-ap-2016-mcq-049）：keyword 'personality traits': not a known alias of 'Traits'; stored without a KP
- Q49（psychology-ap-2016-mcq-049）：keyword 'five major traits': not a known alias of 'Big Five personality traits'; stored without a KP
- Q50（psychology-ap-2016-mcq-050）：supporting 'Rods' duplicates a confusable; dropped
- Q50（psychology-ap-2016-mcq-050）：keyword 'vibrant colors': not a known alias of 'Cones'; stored without a KP
- Q50（psychology-ap-2016-mcq-050）：keyword 'dim light': not a known alias of 'Rods'; stored without a KP
- Q51（psychology-ap-2016-mcq-051）：confusable 'Size constancy' is in option 'D' but not in the core's narrow domain; dropped
- Q51（psychology-ap-2016-mcq-051）：keyword 'looks for him on the other side of the rack': whole/long option text; dropped
- Q52（psychology-ap-2016-mcq-052）：supporting 'Reinforcement schedule' is not in the correct option or the core subheading; dropped
- Q52（psychology-ap-2016-mcq-052）：confusable 'Variable-ratio (VR) schedule' is not named in option 'C' and is not in the core subheading; dropped
- Q52（psychology-ap-2016-mcq-052）：confusable 'Fixed-interval (FI) schedule' is not named in option 'A' and is not in the core subheading; dropped
- Q52（psychology-ap-2016-mcq-052）：confusable 'Variable-interval (VI) schedule' is not named in option 'D' and is not in the core subheading; dropped
- Q52（psychology-ap-2016-mcq-052）：confusable 'Continuous reinforcement' is not named in option 'E' and is not in the core subheading; dropped
- Q52（psychology-ap-2016-mcq-052）：keyword 'rewarded every third trial': not a known alias of 'Fixed-ratio (FR) schedule'; stored without a KP
- Q52（psychology-ap-2016-mcq-052）：keyword 'reinforcement schedules': not a known alias of 'Reinforcement schedule'; stored without a KP
- Q52（psychology-ap-2016-mcq-052）：keyword 'Fixed-ratio': not a known alias of 'Fixed-ratio (FR) schedule'; stored without a KP
- Q52（psychology-ap-2016-mcq-052）：keyword 'Variable-ratio': not a known alias of 'Variable-ratio (VR) schedule'; stored without a KP
- Q52（psychology-ap-2016-mcq-052）：keyword 'Fixed-interval': not a known alias of 'Fixed-interval (FI) schedule'; stored without a KP
- Q52（psychology-ap-2016-mcq-052）：keyword 'Variable-interval': not a known alias of 'Variable-interval (VI) schedule'; stored without a KP
- Q52（psychology-ap-2016-mcq-052）：keyword 'Continuous': not a known alias of 'Continuous reinforcement'; stored without a KP
- Q53（psychology-ap-2016-mcq-053）：supporting 'Mania' is not in the correct option or the core subheading; dropped
- Q53（psychology-ap-2016-mcq-053）：supporting 'Major depressive disorder' duplicates a confusable; dropped
- Q53（psychology-ap-2016-mcq-053）：keyword 'devastating sadness': not a known alias of 'Major depressive disorder'; stored without a KP
- Q53（psychology-ap-2016-mcq-053）：keyword 'tremendous elation': not a known alias of 'Mania'; stored without a KP
- Q53（psychology-ap-2016-mcq-053）：keyword 'excessive excitement': not a known alias of 'Mania'; stored without a KP
- Q53（psychology-ap-2016-mcq-053）：keyword 'racing thoughts': not a known alias of 'Mania'; stored without a KP
- Q53（psychology-ap-2016-mcq-053）：keyword 'elevated self-esteem': not a known alias of 'Self-esteem'; stored without a KP
- Q53（psychology-ap-2016-mcq-053）：keyword 'has not slept for several days': not a known alias of 'Sleep'; stored without a KP
- Q54（psychology-ap-2016-mcq-054）：keyword 'normally distributed': not a known alias of 'Normal curve'; stored without a KP
- Q54（psychology-ap-2016-mcq-054）：keyword 'skew': not a known alias of 'Negatively skewed distribution'; stored without a KP
- Q55（psychology-ap-2016-mcq-055）：supporting 'Split-brain patients' is not in the correct option or the core subheading; dropped
- Q55（psychology-ap-2016-mcq-055）：confusable 'Schizophrenia' is in option 'A' but not in the core's narrow domain; dropped
- Q56（psychology-ap-2016-mcq-056）：confusable 'Operant conditioning' is not named in option 'A' and is not in the core subheading; dropped
- Q56（psychology-ap-2016-mcq-056）：confusable 'Operant conditioning' is not named in option 'B' and is not in the core subheading; dropped
- Q56（psychology-ap-2016-mcq-056）：keyword 'cognitive therapist': not a known alias of 'Cognitive therapy'; stored without a KP
- Q56（psychology-ap-2016-mcq-056）：keyword 'changing the way she interprets her circumstances': not a known alias of 'Cognitive therapy'; stored without a KP
- Q57（psychology-ap-2016-mcq-057）：confusable 'Dependent variable' is not named in option 'B' and is not in the core subheading; dropped
- Q57（psychology-ap-2016-mcq-057）：keyword 'Method of note-taking': not a known alias of 'Independent variable'; stored without a KP
- Q57（psychology-ap-2016-mcq-057）：keyword 'Grades': not a known alias of 'Dependent variable'; stored without a KP
- Q58（psychology-ap-2016-mcq-058）：supporting 'Ingroup' is not in the correct option or the core subheading; dropped
- Q58（psychology-ap-2016-mcq-058）：confusable 'Mere exposure effect' is not named in option 'E' and is not in the core subheading; dropped
- Q58（psychology-ap-2016-mcq-058）：keyword 'athletes from their own country': not a known alias of 'In-group bias'; stored without a KP
- Q58（psychology-ap-2016-mcq-058）：keyword 'athletes from other countries cheat': not a known alias of 'In-group bias'; stored without a KP
- Q59（psychology-ap-2016-mcq-059）：supporting 'IQ' is not in the correct option or the core subheading; dropped
- Q59（psychology-ap-2016-mcq-059）：confusable 'Down syndrome' is in option 'E' but not in the core's narrow domain; dropped
- Q59（psychology-ap-2016-mcq-059）：keyword 'IQ of 60': not a known alias of 'IQ'; stored without a KP
- Q59（psychology-ap-2016-mcq-059）：keyword 'complex calculations in his head': not a known alias of 'Savant syndrome'; stored without a KP
- Q60（psychology-ap-2016-mcq-060）：confusable 'Vestibular sense' is not named in option 'C' and is not in the core subheading; dropped
- Q60（psychology-ap-2016-mcq-060）：keyword 'balance': not a known alias of 'Vestibular sense'; stored without a KP
- Q61（psychology-ap-2016-mcq-061）：keyword 'behavior that is against their principles': not a known alias of 'Cognitive dissonance theory'; stored without a KP
- Q61（psychology-ap-2016-mcq-061）：keyword 'cognitive dissonance': not a known alias of 'Cognitive dissonance theory'; stored without a KP
- Q62（psychology-ap-2016-mcq-062）：confusable 'Emotional intelligence' is in option 'D' but not in the core's narrow domain; dropped
- Q62（psychology-ap-2016-mcq-062）：confusable 'Cerebellum' is in option 'E' but not in the core's narrow domain; dropped
- Q62（psychology-ap-2016-mcq-062）：keyword 'emotions': not a known alias of 'Facial expressions'; stored without a KP
- Q62（psychology-ap-2016-mcq-062）：keyword 'universal emotions': not a known alias of 'Facial expressions'; stored without a KP
- Q62（psychology-ap-2016-mcq-062）：keyword 'Type A personality': not a known alias of 'Type A'; stored without a KP
- Q63（psychology-ap-2016-mcq-063）：supporting 'Proximity (attraction)' is not in the correct option or the core subheading; dropped
- Q63（psychology-ap-2016-mcq-063）：keyword 'attraction': not a known alias of 'Mere exposure effect'; stored without a KP
- Q64（psychology-ap-2016-mcq-064）：supporting 'Reuptake' is not in the correct option or the core subheading; dropped
- Q64（psychology-ap-2016-mcq-064）：keyword 'selective serotonin reuptake inhibitors (SSRIs)': not a known alias of 'Serotonin selective reuptake inhibitor drugs (SSRIs)'; stored without a KP
- Q65（psychology-ap-2016-mcq-065）：supporting 'Dopamine hypothesis' is not in the correct option or the core subheading; dropped
- Q65（psychology-ap-2016-mcq-065）：keyword 'neurotransmitter': not a known alias of 'Neurotransmitters'; stored without a KP
- Q66（psychology-ap-2016-mcq-066）：supporting 'Convenience sampling' is not in the correct option or the core subheading; dropped
- Q66（psychology-ap-2016-mcq-066）：confusable 'Placebo effect' is not named in option 'E' and is not in the core subheading; dropped
- Q66（psychology-ap-2016-mcq-066）：keyword 'generalizable': not a known alias of 'Sampling bias'; stored without a KP
- Q66（psychology-ap-2016-mcq-066）：keyword 'ask only their friends to participate': not a known alias of 'Convenience sampling'; stored without a KP
- Q66（psychology-ap-2016-mcq-066）：keyword 'neglect to ask the rest of the student body': whole/long option text; dropped
- Q66（psychology-ap-2016-mcq-066）：keyword 'placebo effects': not a known alias of 'Placebo effect'; stored without a KP
- Q67（psychology-ap-2016-mcq-067）：confusable 'Feature detectors' is not named in option 'B' and is not in the core subheading; dropped
- Q68（psychology-ap-2016-mcq-068）：supporting 'Token economy' is not in the correct option or the core subheading; dropped
- Q68（psychology-ap-2016-mcq-068）：confusable 'Psychodynamic Perspective' is not named in option 'A' and is not in the core subheading; dropped
- Q68（psychology-ap-2016-mcq-068）：confusable 'Cognitive Perspective' is not named in option 'C' and is not in the core subheading; dropped
- Q68（psychology-ap-2016-mcq-068）：confusable 'Humanist Perspective' is not named in option 'B' and is not in the core subheading; dropped
- Q68（psychology-ap-2016-mcq-068）：keyword 'Token economies': not a known alias of 'Token economy'; stored without a KP
- Q68（psychology-ap-2016-mcq-068）：keyword 'Behavioral': not a known alias of 'Behavioral perspective'; stored without a KP
- Q68（psychology-ap-2016-mcq-068）：keyword 'Psychodynamic': not a known alias of 'Psychodynamic Perspective'; stored without a KP
- Q68（psychology-ap-2016-mcq-068）：keyword 'Humanistic': not a known alias of 'Humanist Perspective'; stored without a KP
- Q68（psychology-ap-2016-mcq-068）：keyword 'Cognitive': not a known alias of 'Cognitive Perspective'; stored without a KP
- Q69（psychology-ap-2016-mcq-069）：supporting 'Recognition' is not in the correct option or the core subheading; dropped
- Q69（psychology-ap-2016-mcq-069）：keyword 'watched a cartoon about a sarcastic rabbit': not a known alias of 'Priming'; stored without a KP
- Q69（psychology-ap-2016-mcq-069）：keyword 'readily identified it as a rabbit instead of a duck': whole/long option text; dropped
- Q69（psychology-ap-2016-mcq-069）：keyword 'Stimulus generalization': not a known alias of 'Generalization'; stored without a KP
- Q70（psychology-ap-2016-mcq-070）：supporting 'Diffusion of responsibility' is not in the correct option or the core subheading; dropped
- Q70（psychology-ap-2016-mcq-070）：confusable 'Conformity' is not named in option 'A' and is not in the core subheading; dropped
- Q70（psychology-ap-2016-mcq-070）：keyword 'group science project': not a known alias of 'Social loafing'; stored without a KP
- Q70（psychology-ap-2016-mcq-070）：keyword 'barely works': not a known alias of 'Social loafing'; stored without a KP
- Q71（psychology-ap-2016-mcq-071）：confusable 'Authoritarian parents' is not named in option 'D' and is not in the core subheading; dropped
- Q71（psychology-ap-2016-mcq-071）：confusable 'Anxious/ambivalent attachment' is not named in option 'C' and is not in the core subheading; dropped
- Q71（psychology-ap-2016-mcq-071）：keyword 'accepted him': not a known alias of 'Unconditional positive regard'; stored without a KP
- Q71（psychology-ap-2016-mcq-071）：keyword 'authoritarian parenting': not a known alias of 'Authoritarian parents'; stored without a KP
- Q71（psychology-ap-2016-mcq-071）：keyword 'ambivalent attachment': not a known alias of 'Anxious/ambivalent attachment'; stored without a KP
- Q72（psychology-ap-2016-mcq-072）：confusable 'Unconditioned stimulus (US or UCS)' is not named in option 'A' and is not in the core subheading; dropped
- Q72（psychology-ap-2016-mcq-072）：keyword 'Sweetened water': not a known alias of 'Conditioned stimulus (CS)'; stored without a KP
- Q72（psychology-ap-2016-mcq-072）：keyword 'paired': not a known alias of 'Classical conditioning'; stored without a KP
- Q72（psychology-ap-2016-mcq-072）：keyword 'The drug': not a known alias of 'Unconditioned stimulus (US or UCS)'; stored without a KP
- Q73（psychology-ap-2016-mcq-073）：confusable 'Dissociative identity disorder (DID)' is not named in option 'A' and is not in the core subheading; dropped
- Q73（psychology-ap-2016-mcq-073）：confusable 'Bipolar disorder' is not named in option 'C' and is not in the core subheading; dropped
- Q73（psychology-ap-2016-mcq-073）：confusable 'Dissociative amnesia' is not named in option 'E' and is not in the core subheading; dropped
- Q73（psychology-ap-2016-mcq-073）：keyword 'Multiple personalities': not a known alias of 'Dissociative identity disorder (DID)'; stored without a KP
- Q73（psychology-ap-2016-mcq-073）：keyword 'Mood swings': not a known alias of 'Bipolar disorder'; stored without a KP
- Q73（psychology-ap-2016-mcq-073）：keyword 'Amnesia': not a known alias of 'Dissociative amnesia'; stored without a KP
- Q74（psychology-ap-2016-mcq-074）：keyword 'performance': not a known alias of 'Social facilitation'; stored without a KP
- Q74（psychology-ap-2016-mcq-074）：keyword 'crowd watching her gets larger': not a known alias of 'Social facilitation'; stored without a KP
- Q75（psychology-ap-2016-mcq-075）：supporting 'Linguistic determinism' is not in the correct option or the core subheading; dropped
- Q75（psychology-ap-2016-mcq-075）：supporting 'Cognition' is not in the correct option or the core subheading; dropped
- Q75（psychology-ap-2016-mcq-075）：confusable 'Universal grammar' is not named in option 'D' and is not in the core subheading; dropped
- Q76（psychology-ap-2016-mcq-076）：supporting 'Selective serotonin reuptake inhibitor' is not in the correct option or the core subheading; dropped
- Q76（psychology-ap-2016-mcq-076）：supporting 'Antidepressant drugs' is not in the correct option or the core subheading; dropped
- Q76（psychology-ap-2016-mcq-076）：confusable 'Somatic symptom disorders' is not named in option 'B' and is not in the core subheading; dropped
- Q76（psychology-ap-2016-mcq-076）：confusable 'Antisocial personality disorder' is not named in option 'D' and is not in the core subheading; dropped
- Q76（psychology-ap-2016-mcq-076）：keyword 'Major depressive': not a known alias of 'Major depressive disorder'; stored without a KP
- Q76（psychology-ap-2016-mcq-076）：keyword 'Somatic symptom': not a known alias of 'Somatic symptom disorders'; stored without a KP
- Q76（psychology-ap-2016-mcq-076）：keyword 'Antisocial personality': not a known alias of 'Antisocial personality disorder'; stored without a KP
- Q77（psychology-ap-2016-mcq-077）：keyword 'suddenly thinks of a solution': not a known alias of 'Insight learning'; stored without a KP
- Q78（psychology-ap-2016-mcq-078）：confusable 'Dissociative disorders' is not named in option 'D' and is not in the core subheading; dropped
- Q78（psychology-ap-2016-mcq-078）：confusable 'Bipolar disorder' is not named in option 'C' and is not in the core subheading; dropped
- Q78（psychology-ap-2016-mcq-078）：keyword 'afraid to leave his house': not a known alias of 'Anxiety disorders'; stored without a KP
- Q78（psychology-ap-2016-mcq-078）：keyword 'apprehensive': not a known alias of 'Anxiety disorders'; stored without a KP
- Q78（psychology-ap-2016-mcq-078）：keyword 'go out in public': not a known alias of 'Social anxiety disorder'; stored without a KP
- Q78（psychology-ap-2016-mcq-078）：keyword 'Anxiety': not a known alias of 'Anxiety disorders'; stored without a KP
- Q79（psychology-ap-2016-mcq-079）：supporting 'Psychoneuroimmunology' is not in the correct option or the core subheading; dropped
- Q79（psychology-ap-2016-mcq-079）：supporting 'Hormones' is not in the correct option or the core subheading; dropped
- Q79（psychology-ap-2016-mcq-079）：confusable 'Coronary heart disease' is not named in option 'A' and is not in the core subheading; dropped
- Q79（psychology-ap-2016-mcq-079）：keyword 'Stress hormones': not a known alias of 'Hormones'; stored without a KP
- Q79（psychology-ap-2016-mcq-079）：keyword 'immune system': not a known alias of 'Psychoneuroimmunology'; stored without a KP
- Q79（psychology-ap-2016-mcq-079）：keyword 'suppressing white blood cells called T lymphocytes': whole/long option text; dropped
- Q79（psychology-ap-2016-mcq-079）：keyword 'hardening her arteries': not a known alias of 'Coronary heart disease'; stored without a KP
- Q80（psychology-ap-2016-mcq-080）：supporting 'Attachment' is not in the correct option or the core subheading; dropped
- Q80（psychology-ap-2016-mcq-080）：supporting 'Strange situation' is not in the correct option or the core subheading; dropped
- Q80（psychology-ap-2016-mcq-080）：confusable 'Avoidant attachment' is not named in option 'A' and is not in the core subheading; dropped
- Q80（psychology-ap-2016-mcq-080）：confusable 'Anxious/ambivalent attachment' is not named in option 'B' and is not in the core subheading; dropped
- Q80（psychology-ap-2016-mcq-080）：confusable 'Insecure attachment' is not named in option 'C' and is not in the core subheading; dropped
- Q80（psychology-ap-2016-mcq-080）：keyword 'Secure': not a known alias of 'Secure attachment'; stored without a KP
- Q80（psychology-ap-2016-mcq-080）：keyword 'Avoidant': not a known alias of 'Avoidant attachment'; stored without a KP
- Q80（psychology-ap-2016-mcq-080）：keyword 'Anxious ambivalent': not a known alias of 'Anxious/ambivalent attachment'; stored without a KP
- Q80（psychology-ap-2016-mcq-080）：keyword 'Resistant': not a known alias of 'Insecure attachment'; stored without a KP
- Q81（psychology-ap-2016-mcq-081）：confusable 'Classical conditioning' is not named in option 'A' and is not in the core subheading; dropped
- Q81（psychology-ap-2016-mcq-081）：confusable 'Misinformation effect' is not named in option 'B' and is not in the core subheading; dropped
- Q81（psychology-ap-2016-mcq-081）：confusable 'Modeling' is not named in option 'C' and is not in the core subheading; dropped
- Q81（psychology-ap-2016-mcq-081）：confusable 'Social loafing' is not named in option 'E' and is not in the core subheading; dropped
- Q82（psychology-ap-2016-mcq-082）：keyword 'Memory loss': not a known alias of 'Memory'; stored without a KP
- Q83（psychology-ap-2016-mcq-083）：supporting 'Scatterplot' is not in the correct option or the core subheading; dropped
- Q83（psychology-ap-2016-mcq-083）：confusable 'Illusory correlation' is not named in option 'A' and is not in the core subheading; dropped
- Q83（psychology-ap-2016-mcq-083）：keyword 'no relationship': not a known alias of 'Illusory correlation'; stored without a KP
- Q84（psychology-ap-2016-mcq-084）：supporting 'Evolutionary psychology' is not in the correct option or the core subheading; dropped
- Q84（psychology-ap-2016-mcq-084）：keyword 'evolutionary approach': not a known alias of 'Evolutionary (or Darwinian) Perspective'; stored without a KP
- Q85（psychology-ap-2016-mcq-085）：confusable 'Arousal theory' is not named in option 'A' and is not in the core subheading; dropped
- Q85（psychology-ap-2016-mcq-085）：keyword 'theory of motivation': not a known alias of 'Motivation'; stored without a KP
- Q85（psychology-ap-2016-mcq-085）：keyword 'intense hunger': not a known alias of 'Drive'; stored without a KP
- Q85（psychology-ap-2016-mcq-085）：keyword 'Drive reduction': not a known alias of 'Drive reduction theory'; stored without a KP
- Q85（psychology-ap-2016-mcq-085）：keyword 'Arousal': not a known alias of 'Arousal theory'; stored without a KP
- Q86（psychology-ap-2016-mcq-086）：keyword 'within one standard deviation of the mean': not a known alias of 'Standard deviation'; stored without a KP
- Q87（psychology-ap-2016-mcq-087）：confusable 'Observational learning' is not named in option 'E' and is not in the core subheading; dropped
- Q87（psychology-ap-2016-mcq-087）：keyword 'supertaster': not a known alias of 'Supertasters'; stored without a KP
- Q87（psychology-ap-2016-mcq-087）：keyword 'very sensitive to hot peppers': not a known alias of 'Taste buds'; stored without a KP
- Q87（psychology-ap-2016-mcq-087）：keyword 'learned': not a known alias of 'Observational learning'; stored without a KP
- Q88（psychology-ap-2016-mcq-088）：confusable 'Broca’s area' is not named in option 'A' and is not in the core subheading; dropped
- Q88（psychology-ap-2016-mcq-088）：confusable 'Motor cortex' is not named in option 'C' and is not in the core subheading; dropped
- Q88（psychology-ap-2016-mcq-088）：confusable 'Temporal lobes' is not named in option 'D' and is not in the core subheading; dropped
- Q88（psychology-ap-2016-mcq-088）：confusable 'Medulla' is not named in option 'E' and is not in the core subheading; dropped
- Q88（psychology-ap-2016-mcq-088）：keyword 'occipital lobe': not a known alias of 'Occipital lobes'; stored without a KP
- Q88（psychology-ap-2016-mcq-088）：keyword 'visual deficit': not a known alias of 'Occipital lobes'; stored without a KP
- Q89（psychology-ap-2016-mcq-089）：confusable 'Aptitude tests' is not named in option 'C' and is not in the core subheading; dropped
- Q89（psychology-ap-2016-mcq-089）：keyword 'Projective': not a known alias of 'Projective tests'; stored without a KP
- Q89（psychology-ap-2016-mcq-089）：keyword 'Aptitude': not a known alias of 'Aptitude tests'; stored without a KP
- Q90（psychology-ap-2016-mcq-090）：supporting 'Schizophrenia spectrum disorders' is not in the correct option or the core subheading; dropped
- Q90（psychology-ap-2016-mcq-090）：keyword 'delivering special messages to the test taker that others cannot detect': whole/long option text; dropped
- Q90（psychology-ap-2016-mcq-090）：keyword 'delusions of reference': not a known alias of 'Delusions'; stored without a KP
- Q90（psychology-ap-2016-mcq-090）：keyword 'visual hallucinations': not a known alias of 'Hallucinations'; stored without a KP
- Q91（psychology-ap-2016-mcq-091）：keyword 'second languages': not a known alias of 'Language'; stored without a KP
- Q92（psychology-ap-2016-mcq-092）：confusable 'Semantic memory' is not named in option 'B' and is not in the core subheading; dropped
- Q92（psychology-ap-2016-mcq-092）：confusable 'Explicit memory' is not named in option 'E' and is not in the core subheading; dropped
- Q92（psychology-ap-2016-mcq-092）：confusable 'Iconic memory' is not named in option 'A' and is not in the core subheading; dropped
- Q92（psychology-ap-2016-mcq-092）：confusable 'Echoic memory' is not named in option 'C' and is not in the core subheading; dropped
- Q92（psychology-ap-2016-mcq-092）：keyword 'Memories of well-learned skills': not a known alias of 'Procedural memory'; stored without a KP
- Q92（psychology-ap-2016-mcq-092）：keyword 'riding a bicycle': not a known alias of 'Procedural memory'; stored without a KP
- Q92（psychology-ap-2016-mcq-092）：keyword 'procedural': not a known alias of 'Procedural memory'; stored without a KP
- Q92（psychology-ap-2016-mcq-092）：keyword 'semantic': not a known alias of 'Semantic memory'; stored without a KP
- Q92（psychology-ap-2016-mcq-092）：keyword 'declarative': not a known alias of 'Explicit memory'; stored without a KP
- Q92（psychology-ap-2016-mcq-092）：keyword 'iconic': not a known alias of 'Iconic memory'; stored without a KP
- Q92（psychology-ap-2016-mcq-092）：keyword 'echoic': not a known alias of 'Echoic memory'; stored without a KP
- Q93（psychology-ap-2016-mcq-093）：supporting 'Antipsychotic drugs' is not in the correct option or the core subheading; dropped
- Q93（psychology-ap-2016-mcq-093）：confusable 'Obsessive-compulsive disorder (OCD)' is not named in option 'A' and is not in the core subheading; dropped
- Q93（psychology-ap-2016-mcq-093）：confusable 'Generalized anxiety disorder (GAD)' is not named in option 'B' and is not in the core subheading; dropped
- Q93（psychology-ap-2016-mcq-093）：confusable 'Somatic symptom disorders' is not named in option 'C' and is not in the core subheading; dropped
- Q93（psychology-ap-2016-mcq-093）：keyword 'antipsychotic medication': not a known alias of 'Antipsychotic drugs'; stored without a KP
- Q94（psychology-ap-2016-mcq-094）：supporting 'Alzheimer’s disease' is not in the correct option or the core subheading; dropped
- Q94（psychology-ap-2016-mcq-094）：confusable 'Obsessive-compulsive disorder (OCD)' is not named in option 'C' and is not in the core subheading; dropped
- Q94（psychology-ap-2016-mcq-094）：keyword 'dementia': not a known alias of 'Alzheimer’s disease'; stored without a KP
- Q94（psychology-ap-2016-mcq-094）：keyword 'Deterioration in memory': not a known alias of 'Memory'; stored without a KP
- Q94（psychology-ap-2016-mcq-094）：keyword 'Compulsions': not a known alias of 'Obsessive-compulsive disorder (OCD)'; stored without a KP
- Q95（psychology-ap-2016-mcq-095）：keyword 'Carl Jung': not a known alias of 'Collective unconscious'; stored without a KP
- Q95（psychology-ap-2016-mcq-095）：keyword 'storehouse of latent memory traces inherited from a person’s ancestral past': whole/long option text; dropped
- Q96（psychology-ap-2016-mcq-096）：supporting 'Depressive disorders' is not in the correct option or the core subheading; dropped
- Q96（psychology-ap-2016-mcq-096）：confusable 'Bipolar disorder' is not named in option 'C' and is not in the core subheading; dropped
- Q96（psychology-ap-2016-mcq-096）：confusable 'Social anxiety disorder' is not named in option 'D' and is not in the core subheading; dropped
- Q96（psychology-ap-2016-mcq-096）：confusable 'Generalized anxiety disorder (GAD)' is not named in option 'E' and is not in the core subheading; dropped
- Q96（psychology-ap-2016-mcq-096）：keyword 'lacked enthusiasm for work and other activities': not a known alias of 'Persistent depressive disorder'; stored without a KP
- Q96（psychology-ap-2016-mcq-096）：keyword 'for a number of years': not a known alias of 'Persistent depressive disorder'; stored without a KP
- Q96（psychology-ap-2016-mcq-096）：keyword 'poor appetite': not a known alias of 'Depressive disorders'; stored without a KP
- Q96（psychology-ap-2016-mcq-096）：keyword 'fatigued': not a known alias of 'Depressive disorders'; stored without a KP
- Q96（psychology-ap-2016-mcq-096）：keyword 'Persistent depressive': not a known alias of 'Persistent depressive disorder'; stored without a KP
- Q96（psychology-ap-2016-mcq-096）：keyword 'Bipolar': not a known alias of 'Bipolar disorder'; stored without a KP
- Q96（psychology-ap-2016-mcq-096）：keyword 'Social anxiety': not a known alias of 'Social anxiety disorder'; stored without a KP
- Q96（psychology-ap-2016-mcq-096）：keyword 'Generalized anxiety': not a known alias of 'Generalized anxiety disorder (GAD)'; stored without a KP
- Q96（psychology-ap-2016-mcq-096）：keyword 'Antisocial personality': not a known alias of 'Antisocial personality disorder'; stored without a KP
- Q96（psychology-ap-2016-mcq-096）：校验错误：confusable: option 'B' is not a wrong option
- Q97（psychology-ap-2016-mcq-097）：confusable 'Rooting reflex' is not named in option 'A' and is not in the core subheading; dropped
- Q97（psychology-ap-2016-mcq-097）：keyword 'stroke the sole of her baby’s foot': whole/long option text; dropped
- Q97（psychology-ap-2016-mcq-097）：keyword 'stroke her baby’s cheek': whole/long option text; dropped
- Q97（psychology-ap-2016-mcq-097）：keyword 'press on her baby’s palm': whole/long option text; dropped
- Q98（psychology-ap-2016-mcq-098）：confusable 'Quantitative research' is not named in option 'B' and is not in the core subheading; dropped
- Q98（psychology-ap-2016-mcq-098）：confusable 'Clinical psychologists' is not named in option 'A' and is not in the core subheading; dropped
- Q98（psychology-ap-2016-mcq-098）：keyword 'field of psychology': not a known alias of 'Psychology'; stored without a KP
- Q98（psychology-ap-2016-mcq-098）：keyword 'hiring': not a known alias of 'Personnel psychology'; stored without a KP
- Q98（psychology-ap-2016-mcq-098）：keyword 'basic training': not a known alias of 'Personnel psychology'; stored without a KP
- Q98（psychology-ap-2016-mcq-098）：keyword 'management leadership skills training': not a known alias of 'Leadership'; stored without a KP
- Q98（psychology-ap-2016-mcq-098）：keyword 'Industrial/organizational': not a known alias of 'Industrial-organizational (I/O) psychology'; stored without a KP
- Q98（psychology-ap-2016-mcq-098）：keyword 'Quantitative': not a known alias of 'Quantitative research'; stored without a KP
- Q98（psychology-ap-2016-mcq-098）：keyword 'Clinical': not a known alias of 'Clinical psychologists'; stored without a KP
- Q99（psychology-ap-2016-mcq-099）：confusable 'Pons' is in option 'C' but not in the core's narrow domain; dropped
- Q99（psychology-ap-2016-mcq-099）：keyword 'infantile amnesia': not a known alias of 'Anterograde amnesia'; stored without a KP
- Q100（psychology-ap-2016-mcq-100）：confusable 'Dissociative identity disorder (DID)' is not named in option 'C' and is not in the core subheading; dropped
- Q100（psychology-ap-2016-mcq-100）：confusable 'Conversion disorder' is not named in option 'D' and is not in the core subheading; dropped
- Q100（psychology-ap-2016-mcq-100）：confusable 'Bipolar disorder' is not named in option 'E' and is not in the core subheading; dropped
- Q100（psychology-ap-2016-mcq-100）：keyword 'superficially charming': not a known alias of 'Antisocial personality disorder'; stored without a KP
- Q100（psychology-ap-2016-mcq-100）：keyword 'exploiting people for his own gain': not a known alias of 'Antisocial personality disorder'; stored without a KP
- Q100（psychology-ap-2016-mcq-100）：keyword 'impulsive': not a known alias of 'Cluster B'; stored without a KP
- Q100（psychology-ap-2016-mcq-100）：keyword 'irresponsible': not a known alias of 'Antisocial personality disorder'; stored without a KP
- Q100（psychology-ap-2016-mcq-100）：keyword 'disregards social norms': not a known alias of 'Norms'; stored without a KP
- Q100（psychology-ap-2016-mcq-100）：keyword 'Antisocial personality': not a known alias of 'Antisocial personality disorder'; stored without a KP
- Q100（psychology-ap-2016-mcq-100）：keyword 'Schizoid personality': not a known alias of 'Cluster A'; stored without a KP
- Q100（psychology-ap-2016-mcq-100）：keyword 'Dissociative identity': not a known alias of 'Dissociative identity disorder (DID)'; stored without a KP
- Q100（psychology-ap-2016-mcq-100）：keyword 'Conversion': not a known alias of 'Conversion disorder'; stored without a KP
- Q100（psychology-ap-2016-mcq-100）：keyword 'Bipolar': not a known alias of 'Bipolar disorder'; stored without a KP

## 复跑命令

```bash
python3 _tools/link_question_concepts.py --paper psychology-ap-2016 --force
```

---

> 本报告是链接工具的运行快照。之后对 6 道题做了人工概念修订，并移除了 2 道图片选项题的链接；最终状态见 `psychology-ap-2016-2017_ai_concepts_final.md`。
