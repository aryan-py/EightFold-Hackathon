from __future__ import annotations
import re
import logging
import uuid
from backend.scoring import calculate_final_score
from backend.db import get_skill_graph, get_bias_check, save_bias_check

logger = logging.getLogger(__name__)

DEMOGRAPHIC_PATTERNS: list[tuple[str, str]] = [
    # Name patterns
    (r'\b(Mr|Mrs|Ms|Dr|Prof)\.?\s+[A-Z][a-z]+ [A-Z][a-z]+\b', '[NAME]'),
    (r'\b[A-Z][a-z]+ [A-Z][a-z]+\b', '[NAME]'),

    # Gender signals
    (r'\b(he|him|his|she|her|hers|they|them|their)\b', '[PRONOUN]'),

    # Age / year of birth
    (r'\b(born|dob|date of birth)[^\n]{0,40}\d{4}\b', '[DOB REDACTED]'),
    (r'\bage[d]?\s*:?\s*\d{2}\b', '[AGE REDACTED]'),
    (r'\bclass of \d{4}\b', '[GRAD YEAR]'),

    # University prestige signals — normalize to generic
    (r'\b(IIT|IIM|NIT|BITS|IISC|Harvard|MIT|Stanford|Oxford|Cambridge|'
     r'Princeton|Yale|Columbia|Cornell|Caltech|UCB|UCLA)\b',
     '[UNIVERSITY]'),

    # Location / nationality that can proxy for bias
    (r'\b(Indian|American|Chinese|British|Pakistani|Bangladeshi|'
     r'Nigerian|German|French|Australian)\b', '[NATIONALITY]'),
]

MASKED_FIELD_LABELS = [
    "name", "pronouns", "age/dob", "university name", "nationality",
]

def mask_resume(text: str) -> tuple[str, list[str]]:
    """
    Apply demographic masking patterns to resume text.
    Returns (masked_text, list_of_fields_that_were_found_and_masked).
    Name patterns run without IGNORECASE to preserve case semantics.
    All other patterns run with IGNORECASE.
    """
    masked = text
    fields_masked: list[str] = []

    # (field_label, pattern_index, use_ignorecase)
    labels = [
        ("name",          0, False),
        ("name",          1, False),
        ("pronouns",      2, True),
        ("age/dob",       3, True),
        ("age/dob",       4, True),
        ("age/dob",       5, True),
        ("university name", 6, True),
        ("nationality",   7, True),
    ]

    for field_label, idx, use_ignorecase in labels:
        pattern, replacement = DEMOGRAPHIC_PATTERNS[idx]
        flags = re.IGNORECASE if use_ignorecase else 0
        new_text = re.sub(pattern, replacement, masked, flags=flags)
        if new_text != masked and field_label not in fields_masked:
            fields_masked.append(field_label)
        masked = new_text

    return masked, fields_masked


async def run_bias_check(
    candidate_id: str,
    run_id: str,
    resume_evidence_original: dict,
    resume_evidence_masked: dict,
    github_evidence: dict,
    skill_graph: dict,
    github_provided: bool,
    score_original: float,
    masked_fields: list[str],
) -> dict:
    """
    Computes masked score and saves the bias check result.
    Returns the full bias check record.
    """
    masked_result = calculate_final_score(
        resume_evidence_masked,
        github_evidence,
        skill_graph,
        github_provided,
    )
    score_masked = masked_result["final_score"]
    check_id = str(uuid.uuid4())

    record = await save_bias_check(
        check_id=check_id,
        candidate_id=candidate_id,
        run_id=run_id,
        score_original=score_original,
        score_masked=score_masked,
        masked_fields=masked_fields,
    )
    return record


def build_bias_check_explanation(record: dict) -> str:
    """
    Produces a recruiter-readable explanation of the bias check result.
    """
    delta_pct = record["delta"] * 100
    fields = record.get("masked_fields", [])
    masked_str = ", ".join(fields) if fields else "no demographic fields detected"

    if not record["is_biased"]:
        return (
            f"Bias check passed. Score changed by {delta_pct:.2f}% after masking "
            f"demographic fields ({masked_str}). "
            f"This candidate's ranking is based on verified skills, not identity signals."
        )
    else:
        return (
            f"Bias flag raised. Score changed by {delta_pct:.2f}% after masking "
            f"demographic fields ({masked_str}). "
            f"Review the resume for identity-correlated language that may be influencing the score."
        )
