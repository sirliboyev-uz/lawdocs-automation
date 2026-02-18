"""Document classification via LLM with keyword-based fallback."""

import logging

from app.config import settings
from app.services import llm

logger = logging.getLogger(__name__)

CATEGORIES = "\n".join(f"- {cat}" for cat in settings.document_categories)

CLASSIFICATION_PROMPT = f"""Classify this legal document into exactly one category.

Categories:
{CATEGORIES}

Rules:
1. Return ONLY the category name, nothing else.
2. If uncertain, use "Other".
3. Base classification on document content, structure, and legal terminology.

Document text (first 3000 characters):
{{text}}"""


def classify_document(text: str) -> str:
    """Classify a document using the LLM. Returns a category name."""
    if not text.strip():
        return "Other"

    if not llm.is_configured():
        logger.warning("No LLM API key configured, using rule-based classification")
        return _rule_based_classify(text)

    try:
        result = llm.complete(
            CLASSIFICATION_PROMPT.format(text=text[:3000]),
            max_tokens=50,
        )
        category = result.strip()

        if category not in settings.document_categories:
            logger.warning("LLM returned unknown category '%s', falling back to Other", category)
            return "Other"
        return category

    except Exception as exc:
        logger.error("LLM classification failed: %s — falling back to rules", exc)
        return _rule_based_classify(text)


def _rule_based_classify(text: str) -> str:
    """Keyword-based fallback when no API key is configured or the API fails."""
    text_lower = text.lower()

    rules: list[tuple[str, list[str]]] = [
        ("Deposition Transcript", ["deposition of", "q.", "a.", "court reporter", "sworn testimony"]),
        ("Court Filing",          ["court of", "plaintiff", "defendant", "motion to", "order of the court"]),
        ("Contract",              ["agreement", "hereby agree", "terms and conditions", "party of the first"]),
        ("Invoice",               ["invoice", "amount due", "bill to", "payment terms", "total due"]),
        ("Medical Record",        ["patient", "diagnosis", "medical history", "treatment plan", "physician"]),
        ("Police Report",         ["incident report", "officer", "suspect", "witness statement", "badge"]),
        ("Expert Report",         ["expert opinion", "methodology", "findings", "conclusion", "analysis"]),
        ("Correspondence",        ["dear", "sincerely", "regards", "re:", "attention"]),
    ]

    for category, keywords in rules:
        matches = sum(1 for kw in keywords if kw in text_lower)
        if matches >= 2:
            return category

    return "Other"
