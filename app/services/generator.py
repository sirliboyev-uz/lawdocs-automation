"""Draft generation: summaries, checklists, and cover letters via LLM."""

import logging

from app.services import llm

logger = logging.getLogger(__name__)

PROMPTS: dict[str, str] = {
    "summary": (
        "You are a legal assistant. Summarize the following legal documents concisely.\n"
        "Focus on: key parties, dates, claims, findings, and important details.\n"
        "Use clear headings and bullet points.\n\n"
        "Documents:\n{documents}"
    ),
    "checklist": (
        "You are a legal assistant. Based on the following case documents, generate a checklist of:\n"
        "1. Documents received (with categories)\n"
        "2. Documents still potentially needed\n"
        "3. Key deadlines or dates mentioned\n"
        "4. Action items\n\n"
        "Format as a clean markdown checklist.\n\n"
        "Case: {case_name}\n"
        "Documents:\n{documents}"
    ),
    "cover_letter": (
        "You are a legal assistant. Draft a professional cover letter for transmitting "
        "the following documents.\n"
        "Include: sender placeholder, recipient placeholder, date, list of enclosed "
        "documents, and professional closing.\n\n"
        "Case: {case_name}\n"
        "Documents being transmitted:\n{documents}"
    ),
}


def generate_draft(
    draft_type: str,
    case_name: str,
    documents: list[dict],
) -> tuple[str, str]:
    """Generate a draft using the LLM. Returns (title, content)."""
    if draft_type not in PROMPTS:
        raise ValueError(f"Unknown draft type: {draft_type}. Options: {list(PROMPTS.keys())}")

    doc_blocks = []
    for doc in documents:
        block = f"**{doc['filename']}** ({doc['category']})\n{doc['text'][:2000]}"
        doc_blocks.append(block)

    documents_text = "\n\n---\n\n".join(doc_blocks)
    prompt = PROMPTS[draft_type].format(case_name=case_name, documents=documents_text)

    title = f"{draft_type.replace('_', ' ').title()} — {case_name}"

    if not llm.is_configured():
        return title, _fallback_content(draft_type, documents)

    try:
        content = llm.complete(prompt, max_tokens=4096)
        return title, content

    except Exception as exc:
        logger.error("Draft generation failed: %s — using fallback", exc)
        return title, _fallback_content(draft_type, documents)


def _fallback_content(draft_type: str, documents: list[dict]) -> str:
    """Basic content returned when no API key is available."""
    lines = [
        f"# {draft_type.replace('_', ' ').title()}",
        "",
        "**Documents:**",
        "",
    ]
    for doc in documents:
        lines.append(f"- {doc['filename']} ({doc['category']})")
    lines.append("")
    lines.append("*Configure an LLM API key in .env for AI-generated content.*")
    return "\n".join(lines)
