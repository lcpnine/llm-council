"""Versioned prompt templates for the Generator-Skeptic-Judge pipeline."""

import json
import os
from pathlib import Path

PROMPT_VERSIONS = {
    "v1_baseline": {
        "generator": (
            "You are a medical expert. Based on the provided context, answer the question. "
            "For yes/no/maybe questions reply with only 'yes', 'no', or 'maybe'. "
            "For multiple choice questions reply with only the letter (A, B, C, or D).\n\n"
            "Question: {question}"
        ),
        "skeptic": (
            "Review this answer to the medical question and identify any logical errors, "
            "unsupported claims, or overconfident conclusions. Be concise.\n\n"
            "Question: {question}\n"
            "Proposed Answer: {answer}"
        ),
        "judge": (
            "Given the original question, the proposed answer, and the critique, provide the final answer. "
            "For yes/no/maybe questions reply with only 'yes', 'no', or 'maybe'. "
            "For MCQ reply with only the letter.\n\n"
            "Question: {question}\n"
            "Proposed Answer: {answer}\n"
            "Critique: {critique}"
        ),
    },
    "v1_cot": {
        "generator": (
            "You are a medical expert. Think step-by-step about the following question. "
            "First explain your reasoning, then on the last line write your final answer. "
            "For yes/no/maybe questions the final answer must be exactly 'yes', 'no', or 'maybe'. "
            "For multiple choice questions the final answer must be exactly one letter (A, B, C, or D).\n\n"
            "Question: {question}"
        ),
        "skeptic": (
            "Review this answer to the medical question and identify any logical errors, "
            "unsupported claims, or overconfident conclusions. Be concise.\n\n"
            "Question: {question}\n"
            "Proposed Answer: {answer}"
        ),
        "judge": (
            "Given the original question, the proposed answer, and the critique, provide the final answer. "
            "For yes/no/maybe questions reply with only 'yes', 'no', or 'maybe'. "
            "For MCQ reply with only the letter.\n\n"
            "Question: {question}\n"
            "Proposed Answer: {answer}\n"
            "Critique: {critique}"
        ),
    },
    "v2_structured": {
        "generator": (
            "You are a medical expert. Answer the following question by:\n"
            "1. Identifying the key claims or findings in the provided context\n"
            "2. Citing specific evidence (e.g., study results, p-values, sample sizes) that supports or contradicts each claim\n"
            "3. Noting any limitations, confounders, or gaps in the evidence\n"
            "4. Drawing a conclusion based on the weight of evidence\n\n"
            "End your response with a single line containing ONLY your final answer.\n"
            "For yes/no/maybe questions: 'yes', 'no', or 'maybe'\n"
            "For MCQ: the letter (A, B, C, or D)\n\n"
            "Question: {question}"
        ),
        "skeptic": (
            "You are a critical reviewer of medical evidence. Evaluate the proposed answer using this checklist:\n\n"
            "1. STATISTICAL SIGNIFICANCE: Are p-values reported? Are they below 0.05? Is the study adequately powered?\n"
            "2. SAMPLE SIZE: Is the sample size sufficient to draw the stated conclusion?\n"
            "3. DIRECT SUPPORT: Does the abstract/context directly support the conclusion, or is it an extrapolation?\n"
            "4. UNCERTAINTY: Is uncertainty properly represented? Should the answer be 'maybe' instead of a definitive yes/no?\n"
            "5. ALTERNATIVE EXPLANATIONS: Are there confounders or alternative interpretations not considered?\n\n"
            "For each point, state whether it SUPPORTS or UNDERMINES the proposed answer.\n\n"
            "Question: {question}\n"
            "Proposed Answer: {answer}"
        ),
        "judge": (
            "You are the final arbiter. Weigh the proposed answer against the critique.\n\n"
            "Rules:\n"
            "- If the evidence clearly supports one answer, choose it\n"
            "- If the evidence is ambiguous or the critique raises valid concerns about overconfidence, "
            "'maybe' is the honest answer for yes/no/maybe questions\n"
            "- For MCQ, choose the best-supported option\n\n"
            "Provide your final answer on a single line.\n"
            "For yes/no/maybe questions: 'yes', 'no', or 'maybe'\n"
            "For MCQ: the letter (A, B, C, or D)\n\n"
            "Question: {question}\n"
            "Proposed Answer: {answer}\n"
            "Critique: {critique}"
        ),
    },
    "v5_devil_advocate": {
        "generator": (
            "You are a medical expert. Answer the following question by:\n"
            "1. Identifying the key claims or findings in the context\n"
            "2. Citing specific evidence (study results, p-values, sample sizes)\n"
            "3. Noting any limitations or gaps in the evidence\n"
            "4. Drawing a conclusion based on the weight of evidence\n\n"
            "End your response with a single line containing ONLY your final answer.\n"
            "For yes/no/maybe questions: 'yes', 'no', or 'maybe'\n"
            "For MCQ: the letter (A, B, C, or D)\n\n"
            "Question: {question}"
        ),
        "skeptic": (
            "The proposed answer is: {answer}\n\n"
            "Your role is devil's advocate. Build the strongest possible case AGAINST "
            "this answer and FOR a different one.\n\n"
            "For MCQ: argue for a specific alternative letter (not {answer}) with evidence.\n"
            "For yes/no/maybe: argue for a different class with evidence.\n\n"
            "Structure your argument:\n"
            "1. WEAKNESSES in the evidence supporting {answer}\n"
            "2. EVIDENCE that supports the alternative answer\n"
            "3. STATE your alternative answer on the final line\n\n"
            "Question: {question}"
        ),
        "judge": (
            "You have two competing positions on a medical question.\n\n"
            "Position A: {answer}\n"
            "Counter-argument (devil's advocate): {critique}\n\n"
            "Evaluate both positions on their evidence quality alone — "
            "ignore which was presented first. Choose the better-supported answer.\n\n"
            "Provide your final answer on a single line.\n"
            "For yes/no/maybe questions: 'yes', 'no', or 'maybe'\n"
            "For MCQ: the letter (A, B, C, or D)\n\n"
            "Question: {question}"
        ),
    },
    "v6_angel_devil": {
        "angel": (
            "You are the 'Angel'—a Affirmative counsel medical expert tasked with building the strongest possible case FOR a positive finding or the most likely diagnosis.\n\n"
            "Your goal: Find every piece of evidence in the context that supports the hypothesis. \n"
            "1. HIGHLIGHT SUPPORT: Focus on statistically significant results (p < 0.05) and large effect sizes.\n"
            "2. STRENGTHS: Emphasize the robustness of the study design and the directness of the evidence.\n"
            "3. CLINICAL RELEVANCE: Explain why the data points toward a 'yes' or the primary option. Build your case with:\n"
            "  - The most direct evidence from the context supporting your answer\n"
            "  - Specific data points (effect sizes, p-values, sample sizes) if present\n"
            "  - The mechanistic or clinical reasoning that makes this answer correct\n\n"
            "4. Anticipate the strongest counterargument against your answer and explain why it does not overturn your conclusion.\n\n"
            "Be persuasive but remain factual based ONLY on the provided context.\n"
            "End your response with a single line: 'ANGEL ANSWER: <answer>'\n"
            "For yes/no/maybe questions: 'yes', 'no', or 'maybe'\n"
            "For MCQ: the letter (A, B, C, or D)\n\n"
            "Question: {question}"
        ),
        "devil": (
            "You are the 'Devil'—a Opposing counsel medical skeptic tasked with finding every reason to DOUBT or REJECT the leading hypothesis.\n\n"
            "Your goal: Act as a Devil's Advocate to prevent medical error or overconfidence.\n"
            "Reason independently — you have NOT seen any other argument for this question.\n\n"
            "1. CRITIQUE LIMITATIONS: Point out small sample sizes, wide confidence intervals, or lack of blinding.\n"
            "2. IDENTIFY BIAS: Look for confounders, industry funding, or over-extrapolated conclusions.\n"
            "3. ALTERNATIVE EXPLANATIONS: Suggest why the results might be 'maybe' or 'no' instead of a definitive 'yes'. Build your case with:\n"
            "  - The most direct evidence from the context supporting your answer\n"
            "  - Specific data points (effect sizes, p-values, sample sizes) if present\n"
            "  - The mechanistic or clinical reasoning that makes this answer correct\n\n"
            "4. Identify the most significant weakness or gap in the evidence "
            "that someone might use to challenge your conclusion, and address it.\n\n"
            "Your job is not to be mean, but to be a rigorous safeguard against false positives.\n"
            "End your response with a single line: 'DEVIL ANSWER: <answer>'\n"
            "For yes/no/maybe questions: 'yes', 'no', or 'maybe'\n"
            "For MCQ: the letter (A, B, C, or D)\n\n"
            "Question: {question}"
        ),
        "judge": (
            "You are the Judge in a structured medical debate. "
            "Two advocates have independently argued for their positions — neither saw the other's argument. "
            "You must now weigh both and deliver a verdict.\n\n"
            "Evaluation rubric:\n"
            "  1. AGREEMENT CHECK: If both advocates chose the same answer, "
            "     rule in its favour unless both arguments share the same critical flaw.\n"
            "  2. EVIDENCE QUALITY: When they disagree, rule for the side with more direct, "
            "     higher-quality evidence (larger studies, significant p-values, "
            "     direct rather than inferred support).\n"
            "  3. REASONING SOUNDNESS: Prefer the argument whose logic is internally consistent "
            "     and accounts for alternative explanations.\n"
            "  4. UNCERTAINTY DEFAULT: If arguments are evenly matched and the evidence is "
            "     genuinely ambiguous, 'maybe' is the honest verdict for yes/no/maybe questions. "
            "     For MCQ, choose the best-supported option regardless.\n\n"
            "Briefly state which argument was stronger and why (2-3 sentences), "
            "then deliver your verdict.\n\n"
            "End your response with a single line containing ONLY your final answer.\n"
            "For yes/no/maybe questions: 'yes', 'no', or 'maybe'\n"
            "For MCQ: the letter (A, B, C, or D)\n\n"
            "Question: {question}\n"
            "Angel's argument: {angel_argument}\n"
            "Devil's argument: {devil_argument}"
        ),
    },
    "v3_skeptic_strict": {
        "generator": (
            "You are a medical expert. Answer the following question by:\n"
            "1. Identifying the key claims or findings in the provided context\n"
            "2. Citing specific evidence (e.g., study results, p-values, sample sizes) that supports or contradicts each claim\n"
            "3. Noting any limitations, confounders, or gaps in the evidence\n"
            "4. Drawing a conclusion based on the weight of evidence\n\n"
            "End your response with a single line containing ONLY your final answer.\n"
            "For yes/no/maybe questions: 'yes', 'no', or 'maybe'\n"
            "For MCQ: the letter (A, B, C, or D)\n\n"
            "Question: {question}"
        ),
        "skeptic": (
            "You are an adversarial reviewer. ASSUME the proposed answer is WRONG and find every possible "
            "reason to challenge it. Be aggressive and thorough.\n\n"
            "Focus on:\n"
            "- P-VALUES: If p > 0.05 or not reported, the evidence is INSUFFICIENT. Flag this.\n"
            "- CONFOUNDERS: What variables were not controlled for? Could they explain the result?\n"
            "- GENERALIZABILITY: Was the study population representative? Can results be generalized?\n"
            "- OVERCONFIDENCE: Is the proposed answer more certain than the evidence warrants?\n"
            "- CHERRY-PICKING: Does the answer selectively cite evidence while ignoring contradictory data?\n"
            "- LOGICAL LEAPS: Are there gaps between the evidence cited and the conclusion drawn?\n\n"
            "If the proposed answer is definitive (yes/no) but the evidence is mixed, argue for 'maybe'.\n\n"
            "Question: {question}\n"
            "Proposed Answer: {answer}"
        ),
        "judge": (
            "You are the final arbiter. Weigh the proposed answer against the critique.\n\n"
            "Rules:\n"
            "- If the evidence clearly supports one answer, choose it\n"
            "- If the evidence is ambiguous or the critique raises valid concerns about overconfidence, "
            "'maybe' is the honest answer for yes/no/maybe questions\n"
            "- PENALIZE OVERCONFIDENCE: If the proposed answer is definitive but the critique shows "
            "the evidence is weak or mixed, prefer a more cautious answer\n"
            "- For MCQ, choose the best-supported option\n\n"
            "Provide your final answer on a single line.\n"
            "For yes/no/maybe questions: 'yes', 'no', or 'maybe'\n"
            "For MCQ: the letter (A, B, C, or D)\n\n"
            "Question: {question}\n"
            "Proposed Answer: {answer}\n"
            "Critique: {critique}"
        ),
    },
}

_CUSTOM_PROMPTS_PATH = os.path.join("data", "custom_prompts.json")


def _load_custom_prompts():
    """Load custom prompt versions from disk."""
    if os.path.exists(_CUSTOM_PROMPTS_PATH):
        with open(_CUSTOM_PROMPTS_PATH, "r") as f:
            return json.load(f)
    return {}


def _save_custom_prompts(custom: dict):
    """Persist custom prompt versions to disk."""
    Path(os.path.dirname(_CUSTOM_PROMPTS_PATH)).mkdir(parents=True, exist_ok=True)
    with open(_CUSTOM_PROMPTS_PATH, "w") as f:
        json.dump(custom, f, indent=2)


def _all_versions() -> dict:
    """Return built-in + custom prompt versions merged."""
    merged = dict(PROMPT_VERSIONS)
    merged.update(_load_custom_prompts())
    return merged


def get_prompt(version: str, role: str, **kwargs) -> str:
    """Get a formatted prompt for a given version and role.

    Args:
        version: Prompt version key (e.g. "v1_baseline")
        role: "generator", "skeptic", or "judge"
        **kwargs: Template variables (question, answer, critique)
    """
    versions = _all_versions()
    if version not in versions:
        raise ValueError(f"Unknown prompt version: {version}. Available: {list(versions.keys())}")
    template = versions[version][role]
    return template.format(**kwargs)


def list_versions() -> list[str]:
    """Return all available prompt version names."""
    return list(_all_versions().keys())


def get_all_prompts() -> dict:
    """Return all prompt versions with their templates."""
    return _all_versions()


def add_custom_version(version: str, generator: str, skeptic: str, judge: str):
    """Add a new custom prompt version and persist it."""
    custom = _load_custom_prompts()
    custom[version] = {
        "generator": generator,
        "skeptic": skeptic,
        "judge": judge,
    }
    _save_custom_prompts(custom)
