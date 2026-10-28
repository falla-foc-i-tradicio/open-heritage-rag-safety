"""Citation-membership validation for a single RAG answer turn."""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from typing import Sequence

from .context import RagContext


MAX_ANSWER_CHARS = 30_000
MAX_CITATIONS = 12


@dataclass(frozen=True)
class AnswerDraft:
    """An answer whose citations are constrained to the supplied context."""

    text: str
    citations: tuple[str, ...]


def _validate_answer_text(text: str) -> str:
    if not isinstance(text, str):
        raise TypeError("Answer text must be text.")
    if not text or text != text.strip():
        raise ValueError("Answer text cannot be empty or have outer whitespace.")
    if len(text) > MAX_ANSWER_CHARS:
        raise ValueError("Answer text exceeds the allowed limit.")
    for char in text:
        if char in {"\n", "\t"}:
            continue
        if unicodedata.category(char) in {"Cc", "Cf"}:
            raise ValueError("Answer text contains an unsupported control character.")
    return text


def validate_answer_citations(
    text: str,
    citations: Sequence[str],
    context: RagContext,
    *,
    require_citation_when_context_exists: bool = True,
) -> AnswerDraft:
    """Ensure that an answer cites only sources present in the turn context.

    This validates citation membership, not semantic truth. A host application
    may disable the requirement for a citation in operational messages that do
    not make a document-derived claim, but it can never introduce a citation
    absent from the selected context.
    """
    answer_text = _validate_answer_text(text)
    if not isinstance(context, RagContext):
        raise TypeError("context must be a RagContext.")
    if isinstance(citations, (str, bytes)) or not isinstance(citations, Sequence):
        raise TypeError("citations must be a sequence.")
    if len(citations) > MAX_CITATIONS:
        raise ValueError("Too many citations in one answer.")

    allowed = set(context.citations)
    normalized: list[str] = []
    seen: set[str] = set()
    for citation in citations:
        if not isinstance(citation, str) or not citation:
            raise ValueError("An answer citation is invalid.")
        if citation in seen:
            raise ValueError("An answer citation is duplicated.")
        if citation not in allowed:
            raise PermissionError("An answer citation is not present in this turn's context.")
        seen.add(citation)
        normalized.append(citation)

    if not allowed and normalized:
        raise PermissionError("A context with no sources cannot be cited.")
    if allowed and require_citation_when_context_exists and not normalized:
        raise ValueError("A document-based answer requires at least one allowed citation.")
    return AnswerDraft(text=answer_text, citations=tuple(normalized))
