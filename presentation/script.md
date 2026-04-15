# **1NLP Video Presentation Script**

1. **Introduction \+ Motivation**  
   Medical question answering is a high-stakes NLP task where errors can have serious clinical consequences. While LLMs have shown impressive performance on general QA benchmarks, they tend to exhibit overconfidence in medical settings, either forcing definitive yes-or-no answers when the evidence is genuinely ambiguous or hedging unnecessarily when the evidence is clear. This overconfidence is particularly problematic for questions that require careful interpretation of statistical evidence, such as those in PubMedQA, where the correct answer is often "maybe" because the evidence is insufficient or contradictory. Existing approaches either rely solely on prompt engineering, which lacks systematic critique, or on fine-tuned models, which are constrained by their training distribution. In this work, we investigate whether a multi-agent adversarial debate pipeline where a Generator produces an initial answer, a Skeptic challenges it with statistical and logical critique, and a Judge synthesizes the debate into a final decision, can produce more accurate and better-calibrated answers than both single-agent prompting baselines and a fine-tuned PubMedBERT model. We evaluate across three medical QA datasets, namely PubMedQA, MedQA, and MMLU and compare multiple prompt strategies and model configurations to understand when debate helps and when it does not.

2. **System Architecture**  
   The system is built around a Generator-Skeptic-Judge pipeline. In the baseline configuration, n\\\_stages=1 runs only the Generator to produce a direct answer. In the standard debate configuration, n\\\_stages=3 passes the Generator's output sequentially to a Skeptic, which challenges it with critique, and then to a Judge, which synthesizes the exchange into a final decision. The v5\\\_angel\\\_devil variant takes an alternate approach and replaces the sequential path entirely: there is no generator stage. Instead, an Angel and a Devil advocate both receive the raw question directly, run in parallel with no shared context, and the Judge arbitrates between their independent arguments. 

   All inference is served through the Groq API, an OpenAI-compatible endpoint, using four hosted models: \`llama-3.3-70b-versatile\`, \`llama-3.1-8b-instant\`, \`qwen/qwen3-32b\`, and \`meta-llama/llama-4-scout-17b-16e-instruct\`. Token usage is recorded when returned by the API, accumulated per stage and per experiment to support cost-effectiveness analysis.

   PubMedBERT was evaluated externally rather than through the platform. The fine-tuned models were run offline and the results compared against the same 100-question sets used by the LLM platform, using the same evaluation code. This makes it a clean apples-to-apples comparison — same datasets, same evaluation logic — but a fundamentally different inference approach.

   Datasets are loaded from HuggingFace: PubMedQA as a three-label (yes/no/maybe) evidence QA task, MedQA as USMLE-style four-option multiple choice, and MMLU restricted to four medical subsets — clinical knowledge, medical genetics, anatomy, and professional medicine. The evaluator parses LLM outputs into normalized labels via extract\\\_answer(), and computes accuracy, F1 macro, per-class precision and recall, and maybe recall via compute\\\_metrics(). Experiments are persisted to a SQLite database with per-question debate logs and full token breakdowns.  
3. **Baselines used**  
   We establish five prompting baselines to evaluate the contribution of each design decision. The first is v1\\\_baseline at n\\\_stages=1, a single-agent direct prompt with no chain-of-thought, establishing the floor. The second is v1\\\_cot at n\\\_stages=1, which adds explicit step-by-step reasoning to the same single-agent setup, isolating the effect of structured reasoning from the effect of debate. The third is v1\\\_baseline at n\\\_stages=3, which runs the full three-stage debate pipeline using the same minimal prompts, isolating the structural contribution of the debate loop itself. The fourth is v2\\\_structured, a three-stage setup that adds an evidence-based reasoning scaffold for the Generator and a systematic critique checklist for the Skeptic. The fifth is v3\\\_skeptic\\\_strict, which tightens the Skeptic's mandate specifically around p-values, confounders, generalizability, overconfidence, cherry-picking, and logical leaps between evidence and conclusion. Together these five conditions allow us to test whether performance gains are attributable to CoT reasoning, debate structure, or progressively stricter adversarial prompting.  
   In addition to the prompting baselines, we introduce a classical NLP baseline using a fine-tuned PubMedBERT model. The motivation is to answer a fundamentally different question — not whether better prompting helps, but whether our multi-agent debate system can outperform a model that was explicitly trained on this data. We chose PubMedBERT over BioBERT because it was pre-trained from scratch exclusively on PubMed abstracts and full-text papers, giving it stronger biomedical language understanding without general-domain bias.  
   We fine-tuned three separate models — one per dataset — rather than a single combined model, to ensure a fair comparison. The architecture differs per task: a SequenceClassification head for PubMedQA's 3-class yes/no/maybe format, and a MultipleChoice head for MedQA and MMLU's 4-option format. A key challenge was class imbalance in PubMedQA — the maybe class is underrepresented, causing the model to never predict it initially. We addressed this using weighted cross-entropy loss, which brought maybe recall up to 0.53. Training was done on Kaggle GPU T4 x2 with a learning rate of 2e-5, warmup ratio of 0.1, weight decay of 0.01, and 5 epochs with early stopping. The three models were evaluated offline against the same question sets, with results imported into the platform for comparison.  
   The multi-model role ablations are covered separately by other team members.  
     
4. **Platform Walkthrough**  
   To support reproducible experimentation across the team, we built a full-stack research platform. The Run tab accepts a single experiment configuration or a batch matrix across any combination of models, prompt versions, datasets, and stage counts. The Results tab displays all experiments in a sortable, filterable table with dropdown selectors for model, prompt, dataset, and stage count, and supports checkbox selection for multi-experiment comparison. The Detail tab shows the complete metrics breakdown, confusion matrix, and per-question results with expandable debate logs, plus editable notes and tags for annotation. The Compare tab renders a side-by-side metrics table with a per-question disagreement diff and a button that copies a generated LaTeX table to the clipboard. The Charts tab uses Recharts to visualize accuracy, per-class F1, and token usage across experiments, with PNG export via SVG-to-canvas conversion.  
5. **Results & Analysis**  
   We begin with our trained model ceiling. The fine-tuned PubMedBERT baseline achieved 40% accuracy on PubMedQA, 34% on MedQA, and 35% on MMLU, with F1 macro of 0.31, 0.32, and 0.34 respectively. Notably, maybe recall on PubMedQA reached 0.53 after applying weighted cross-entropy loss — meaning the model correctly identified over half of all ambiguous cases. These numbers set the bar that our prompting-only debate system needs to clear.  
   	Beyond prompt design, we investigated whether using different models in different debate roles could improve performance. In our multi-model ablation, we systematically swapped in Qwen-32B and Llama-8B across the Generator, Skeptic, and Judge positions, holding the prompt constant at v2\_structured.  
   On MedQA, the results were striking. The best configuration — Qwen as Generator, Llama-70B as Skeptic and Judge — reached 88% accuracy, up from the 77% all-70B baseline. This suggests that starting the debate with a different model's knowledge base creates more productive disagreement for the judge to resolve. However, on PubMedQA, all cross-model configurations underperformed the baseline — mixing models here hurt calibration on the ambiguous yes/no/maybe task.  
   We also implemented two novel debate strategies inspired by published work. First, v5 Counter-Argument — based on adversarial sequential debate — forces the skeptic to build the strongest possible case for a specific alternative, rather than merely finding flaws. This gave a modest \+5pp on PubMedQA.  
   Second, and most significantly, v5 Angel-Devil Debate — inspired by Du et al.'s Multiagent Debate paper — runs two independent advocates in parallel: an Angel arguing affirmatively and a Devil challenging every assumption, with neither seeing the other's reasoning. A structured judge then arbitrates using an explicit evidence-quality rubric. On PubMedQA, this jumped from 44% to 67% accuracy — a 23-percentage-point gain — our strongest single result. The independent parallel structure prevents anchoring bias from the generator's initial answer. However, on MedQA, it collapsed to 44% because the Angel's built-in bias toward affirmative answers is misaligned with multiple-choice questions that lack an inherent 'positive' option.  
   Comparing across all systems, the v5 Angel-Devil debate at 67% on PubMedQA comfortably exceeds the PubMedBERT fine-tuned baseline of 40%, demonstrating that a well-structured prompting approach can outperform a model trained specifically on the task. However, PubMedBERT's maybe recall of 0.53 remains competitive with several debate configurations, highlighting that uncertainty detection still benefits from task-specific training.

6. **Conclusion \+ Limitations**  
   Our results show that multi-agent debate, using only prompting and no task-specific training, can outperform a fine-tuned PubMedBERT model on overall accuracy — particularly with the Angel-Devil configuration which reached 67% on PubMedQA compared to PubMedBERT's 40%. However, PubMedBERT's maybe recall of 0.53 remained competitive, suggesting that uncertainty detection specifically still benefits from training on labeled ambiguous cases. A key limitation of the fine-tuned baseline is the small PubMedQA training set of only 900 examples — with more data, a fine-tuned model could potentially close the gap.  
   On the infrastructure side, Groq's free-tier rate limits required deliberate pacing between API calls — 0.5 seconds between debate stages and 0.3 seconds between questions — and the team's parallel experiment workflows necessitated a JSON export and import system to prevent database conflicts across local environments.

**PPT Slide Breakdown (Draft)**

**Slide 1 — Title**

* Project title, all team member names

**Slide 2 — Abstract / Motivation**

* One paragraph: problem, contribution, key finding  
* Keep it tight — mirrors the abstract

**Slide 3 — Introduction**

* Why medical QA is hard  
* Why ambiguous cases (maybe) matter clinically  
* Why current single-model approaches fall short  
* Your research question explicitly stated:  
  * Does multi-agent debate improve over single-agent?  
  * Does debate beat a model trained on the task?

**Slide 5 — Datasets**

* Table: PubMedQA / MedQA / MMLU with task, labels, size, source  
* Call out PubMedQA class imbalance — critical for maybe recall

**Slide 6 — Approach: System Architecture** 

* Generator → Skeptic → Judge diagram  
* Multi-model variant: different models per stage  
* PubMedBERT classifier — bypasses debate pipeline, direct inference  
* Alternate Architecture: Angel, Devil → Judge diagram  
* Prompt versions table: v1\_baseline, v1\_cot, v2\_structured, v3\_skeptic\_strict, v5\_counter\_argument, v5\_angel\_devil

**Slide 7 — Approach: Baselines** 

* **Classical NLP baseline** — PubMedBERT fine-tuned   
  \- SequenceClassification (PubMedQA) / MultipleChoice (MedQA, MMLU)  
  \- Weighted loss to handle maybe class imbalance  
* **Prompting baselines** — 1-stage direct, 1-stage CoT (establishes reasoning helps)  
* **Debate variants** — v1, v2, v3 prompts (establishes debate structure helps)  
* **Scale variants** — 70B vs 8B (establishes model size effect)  
* **Multi-model variants** — \`llama-3.3-70b-versatile\`, \`llama-3.1-8b-instant\`, \`qwen/qwen3-32b\`, and \`meta-llama/llama-4-scout-17b-16e-instruct\`. Swarangi's work  
* **Independent debate variant** — v5 prompt (alternate debate structure)

**Slide 8 — Evaluation Metrics**

Primary Metrics:

• Accuracy: Overall correctness across all 47 experiments

• F1 Macro: Macro-averaged F1 score across all classes

  \- Handles class imbalance by treating all classes equally

  \- Dataset means: MedQA 0.680, MMLU 0.750, PubMedQA 0.393

• Maybe Recall: Recall specifically for "maybe" class in PubMedQA

  \- Mean: 0.557 across 23 PubMedQA experiments

  \- Critical for detecting clinically ambiguous cases

  \- Rare class challenge: only \~15% of PubMedQA samples are "maybe"

Why F1 Macro?

Better than accuracy alone for imbalanced datasets where "maybe" is underrepresented. Standard metric for multi-class classification that doesn't favor majority classes.

Why Maybe Recall?

In clinical practice, saying "maybe" when evidence is genuinely ambiguous is the correct medical decision. Missing these cases means forcing false confidence when uncertainty exists. PubMedBERT achieved 0.53 maybe recall after weighted loss training.

**Script :** "We evaluated 47 experiments using four key metrics. Accuracy measures overall correctness, but for PubMedQA's imbalanced dataset—where 'maybe' is only 15% of cases—we need F1 Macro, which treats all classes equally. Our results show striking differences: mean F1 of 0.75 on MMLU, 0.68 on MedQA, but only 0.39 on PubMedQA, highlighting the challenge of ambiguous reasoning versus factual recall.

Maybe Recall is particularly critical for medical AI—correctly identifying uncertainty when evidence is insufficient. Our baseline achieved 53% maybe recall, while debate configurations varied dramatically from 0% to 92%, showing different calibration strategies."

**Slide 9 — Platform Demo** 

* Screenshot: RunTab — selecting model, dataset, stages  
* Screenshot: Results tab — experiment comparison  
* Screenshot: Compare tab — side by side metrics  
* Keep brief — 30 seconds in the video

**Slide 10 — Main Results Table** ( copy paste-PPT\_MAIN\_RESULTS\_TABLE.csv)

System                       | PubMedQA Acc | MedQA Acc | MMLU Acc | F1 Macro | Maybe Recall

\-----------------------------|--------------|-----------|----------|----------|-------------

PubMedBERT (fine-tuned)      | 40%          | 34%       | 35%      | 0.32     | 0.53

Single agent v1 (direct)     | 70%          | 78%       | 88%      | 0.75     | 0.13

Single agent v1 \+ CoT        | 71%          | 79%       | 90%      | 0.74     | 0.00

Multi-agent v2 (structured)  | 44%          | 77%       | 94%      | 0.72     | 0.93

Multi-agent v3 (strict)      | 21%          | 30%       | 38%      | 0.36     | 0.92

v5 counter-argument          | 49%          | 61%       | \-        | 0.49     | 0.07

v5 angel-devil (debate)      | 67%          | 44%       | \-        | 0.55     | 0.07

v5 angel-devil (hetero)      | \-            | 59%       | \-        | 0.70     | \-

Key Observations:

• v2\_structured achieves highest MCQ accuracy (94% MMLU) with strong F1 (0.94)

• v3\_skeptic\_strict catastrophically fails (F1 \= 0.36) due to over-skepticism

• v5\_angel\_devil partially recovers PubMedQA (67% vs v3's 21%) but debate setup collapses on MedQA (44%)

• v5\_angel\_devil heterogeneous (multi-model) performs better on MedQA (59%) with F1=0.70

• F1 Macro shows debate helps on MCQ but hurts on PubMedQA's ambiguous task

• Maybe Recall varies dramatically: v2=93%, v1\_cot=0%, v5=7%, showing different calibration strategies

• v5\_counter\_argument shows modest PubMedQA gain (49%) with 61% on MedQA

• Most LLM configs beat PubMedBERT on accuracy — exceptions: v3_skeptic_strict (21% PubMedQA, 30% MedQA) and most v2_structured heterogeneous PubMedQA runs (21–44%) fall below the 40% baseline; PubMedBERT maybe recall (0.53) remains competitive

**Script :** "Looking at our results, we see stark dataset-dependent performance. Our baseline v1 direct prompting achieved 70% on PubMedQA and 88% on MMLU. Adding chain-of-thought improved MCQ accuracy to 90% but eliminated maybe predictions entirely—revealing how explicit reasoning can override natural uncertainty.

V2\_structured achieved our best MCQ results: 94% on MMLU with near-perfect F1. On PubMedQA, despite dropping to 44% accuracy, it achieved 93% maybe recall—the system correctly identified ambiguous cases at the cost of overall accuracy.

Then v3\_skeptic\_strict catastrophically failed with only 21% accuracy on PubMedQA and F1 of 0.36. It achieved 92% maybe recall by defaulting to 'maybe' for nearly everything—the skeptic was too aggressive.

V5\_angel\_devil partially recovered with 67% on PubMedQA, but collapsed to 44% on MedQA because the Angel's affirmative bias misaligns with multiple-choice questions."

**Slide 11 — Ablation Study:**  (Use 4 confusion matrices (MMLU: v1→v2, v1→v3) to show Fix/break visualization)

**Agent Attribution Analysis:** (Use agent\_attribution\_summary.png)

What breaks and what fixes in multi-agent debate?

Agent Attribution Results (35 3-stage experiments):

• v2\_structured: Fixed 459, Broke 484 → Net \-25 (includes debate \+86 and heterogeneous \-111)

• v3\_skeptic\_strict: Fixed 92, Broke 324 → Net \-232 (catastrophic)

• v5\_angel\_devil: Fixed 60, Broke 55 → Net \+5 (slightly helpful)

• v5\_counter\_argument: Fixed 41, Broke 46 → Net \-5 (slightly harmful)

• v1\_baseline: Fixed 4, Broke 6 → Net \-2 (one 3-stage experiment)

Setup Comparison:

• 3-stage Debate: Fixed 295, Broke 452 → Net \-157 (overall harmful)

• 3-stage Heterogeneous: Fixed 361, Broke 463 → Net \-102 (harmful but less so)

Best Case: v2\_structured \+ Llama-70B on MedQA

• Fixed 51 wrong answers, Broke only 1 correct answer → Net \+50 (HELPED)

• 94% MMLU accuracy: Fixed 47, Broke 0 → Net \+47 (HELPED)

Worst Case: v3\_skeptic\_strict \+ Llama-8B on MMLU

• Fixed 3, Broke 71 → Net \-68 (catastrophic over-skepticism)

Multi-Model:

• Qwen-32B as Generator \+ Llama-70B as Skeptic/Judge: 88% on MedQA (best MCQ)

• Cross-model configurations underperform on PubMedQA (mixing hurts calibration)

• Key insight: Different model knowledge bases create productive disagreement on MCQ but hurt ambiguous tasks

Key Finding:

Debate is a double-edged sword \- v2\_structured debate fixed 126 errors but broke 40 correct answers (net \+86), while heterogeneous configurations fixed 333 but broke 444 (net \-111). The skeptic's aggression level is the critical tuning parameter.

**Script :** "To understand why debate helps or hurts, we conducted agent attribution analysis across all 35 3-stage experiments. For each question, we compare the Generator's initial answer against the final answer after Skeptic and Judge intervention—giving us four categories: both correct, fixed by debate, broke by debate, and both wrong. Net impact equals fixes minus breaks.

Debate is fundamentally a double-edged sword. Only v5\_angel\_devil showed positive net impact: \+5 (60 fixed, 55 broke). V2\_structured in homogeneous debate mode achieved net \+86 (126 fixed, 40 broke)—showing debate can work when calibrated. But aggregating all v2\_structured including heterogeneous configurations: net \-25 (459 fixed, 484 broke).

The best case was v2\_structured with Llama-70B on MedQA: net \+50 (51 fixed, 1 broke). On MMLU: net \+47 (47 fixed, 0 broke)—debate working perfectly.

The worst case was v3\_skeptic\_strict: net \-232 overall (92 fixed, 324 broke). On MMLU with Llama-8B: net \-68 (3 fixed, 71 broke)—pure over-skepticism destroying correct answers.

Key insight: debate effectiveness isn't universal—it's tuned through prompt design. The skeptic's aggression is the critical parameter."

**Slide 12 — Statistical Significance & Qualitative Analysis** ( Use accuracy\_by\_dataset.png \- Main visual showing all configurations ), ( statistical\_comparions.csv)

Statistical Validation:

23/35 experiments show p \< 0.001 (McNemar's test with continuity correction)

• Highly significant differences in majority of experiments \- not due to random chance

• 2 experiments: p \< 0.01, 2 experiments: p \< 0.05, 8 experiments: not significant

• Paired test on same 100 questions ensures valid comparison

• Debate effects are real and statistically robust where significant

Key Patterns by Dataset:

PubMedQA (Yes/No/Maybe):

• Challenge: 3-class imbalanced task (\~15% maybe class)

• v2\_structured: 44% accuracy, 93% maybe recall → over-predicts ambiguity

• v3\_skeptic\_strict: 21% accuracy, 92% maybe recall → says "maybe" to nearly everything

• v5\_angel\_devil: 67% accuracy, 7% maybe recall → recovers from v3's collapse

• Finding: Skeptic aggression directly trades off accuracy vs uncertainty detection

MedQA (4-option MCQ):

• Challenge: USMLE-style medical knowledge questions

• v2\_structured: 77% (70B), 88% (Qwen+70B heterogeneous)

• Debate helps: Net \+50 fix-to-break ratio on best configuration

• Finding: Critique improves reasoning on knowledge-based MCQs

MMLU Medical (4-option MCQ):

• Challenge: Fact recall across anatomy, genetics, clinical knowledge

• v2\_structured: 94% accuracy, F1 \= 0.94 (near-perfect)

• Debate helps: Fixed 47, broke 0 on best run

• v3\_skeptic\_strict: 38% accuracy → over-critique destroys factual recall

• Finding: Lighter skepticism works better on fact-based questions

Qualitative Error Types:

1\. Generator overconfidence → Skeptic corrects → Improved (Type 1: Fixed by debate)

2\. Generator correct → Skeptic introduces doubt → Judge changes answer → Worse (Type 2: Broke by debate)

3\. Generator wrong → Skeptic wrong → Judge wrong → Same error (Type 3: Both wrong)

4\. Over-skepticism → Judge says "maybe" to clear yes/no → Calibration failure

Example Debate Patterns:

• Best: Generator gives B, Skeptic finds logical flaw, Judge changes to correct C

• Worst: Generator correct with A, Skeptic raises irrelevant doubt, Judge switches to wrong D

• Catastrophic: Any clear answer → Skeptic insists "insufficient evidence" → Judge defaults to "maybe"

**Script:** "Our statistical analysis confirms these effects are real—23 out of 35 experiments showed p \< 0.001 with McNemar's test, highly significant and not due to chance.

Breaking down by dataset, task structure dictates debate behavior. On PubMedQA, v2\_structured achieved 93% maybe recall but dropped to 44% accuracy by over-predicting uncertainty. V3\_skeptic\_strict achieved 92% maybe recall by defaulting to 'maybe' for nearly everything—collapsing accuracy to 21%. This is catastrophic over-skepticism: the judge loses confidence even with clear evidence.

V5\_angel\_devil offers recovery: parallel advocacy instead of sequential critique reached 67% accuracy, avoiding v3's failure but dropping maybe recall to 7%—the opposite extreme.

On MCQ tasks, debate worked much better. MedQA with heterogeneous Qwen-32B and Llama-70B achieved 88% accuracy. On MMLU, v2\_structured reached 94% with net \+47 impact—fixing 47 errors without breaking any correct answers.

From qualitative analysis, we identified four error patterns: Generator overconfidence corrected by Skeptic (intended success), Generator correct but Skeptic introduces doubt (broke by debate), both wrong (knowledge gap), and calibration failures where Skeptic defaults to 'maybe' inappropriately.

The consistent pattern: debate improves MCQ reasoning where critique catches errors without excessive doubt, but on ambiguous tasks, skepticism breaks correct answers more than it fixes wrong ones unless carefully calibrated."

**Slide 13 — Conclusion & Limitations**

* Does debate beat fine-tuning? (answer this directly)  
* Key findings in 3 bullet points  
* Limitations: small PubMedQA training set, Groq rate limits, maybe class   
* Future work: larger models, human evaluation, more datasets

**Slide 14 — Team Contributions**

* One line per person — mirrors the report's team contributions section  
* Matches what you'll submit in the report

