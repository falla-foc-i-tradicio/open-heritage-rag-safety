"""Validated, minimized RAG context for already-authorized document fragments.

The module does not retrieve documents, decide access control, or invoke a
model. It turns fragments authorized by an upstream application into bounded,
model-facing data that is explicitly labelled as untrusted document content.
"""

from __future__ import annotations

import json
import math
import re
import unicodedata
from dataclasses import dataclass
from typing import Any, Mapping, Sequence


RAG_CONTEXT_VERSION = 1
MAX_CANDIDATES = 100
MAX_FRAGMENTS = 6
MAX_FRAGMENT_CHARS = 20_000
MAX_TOTAL_CONTENT_CHARS = 40_000
MAX_MODEL_CONTEXT_CHARS = 48_000
MAX_TITLE_CHARS = 300
MAX_SOURCE_LABEL_CHARS = 200
_TOKEN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/#-]{0,119}$")


@dataclass(frozen=True)
class AuthorizedFragment:
    """A document fragment already authorized by an upstream ACL layer."""

    citation: str
    source_label: str
    version: str
    title: str
    content: str
    semantic_score: float
    acl_authorized: bool

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "AuthorizedFragment":
        if not isinstance(value, Mapping):
            raise TypeError("A RAG fragment must be a mapping.")
        allowed = {
            "citation",
            "source_label",
            "version",
            "title",
            "content",
            "semantic_score",
            "acl_authorized",
        }
        unknown = sorted(set(value) - allowed)
        missing = sorted(allowed - set(value))
        if unknown:
            raise ValueError("Unexpected RAG metadata: " + ", ".join(unknown))
        if missing:
            raise ValueError("Missing RAG fields: " + ", ".join(missing))
        return cls(**{name: value[name] for name in allowed})


@dataclass(frozen=True)
class RagContext:
    """The bounded context delivered to a model adapter plus allowed citations."""

    model_context: str
    citations: tuple[str, ...]


def _validate_text(value: Any, *, field: str, max_chars: int, allow_newlines: bool) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field} must be text.")
    if not value or value != value.strip():
        raise ValueError(f"{field} cannot be empty or have outer whitespace.")
    if len(value) > max_chars:
        raise ValueError(f"{field} exceeds the allowed limit.")
    for char in value:
        if char in {"\n", "\t"} and allow_newlines:
            continue
        if unicodedata.category(char) in {"Cc", "Cf"}:
            raise ValueError(f"{field} contains an unsupported control character.")
    return value


def _validate_token(value: Any, *, field: str) -> str:
    if not isinstance(value, str) or not _TOKEN_RE.fullmatch(value):
        raise ValueError(f"{field} is not a safe canonical identifier.")
    return value


def _validated_fragment(fragment: AuthorizedFragment) -> AuthorizedFragment:
    if not isinstance(fragment, AuthorizedFragment):
        raise TypeError("Expected an AuthorizedFragment.")
    if fragment.acl_authorized is not True:
        raise PermissionError("The fragment is missing prior ACL authorization.")
    score = fragment.semantic_score
    if isinstance(score, bool) or not isinstance(score, (int, float)):
        raise TypeError("semantic_score must be numeric.")
    score = float(score)
    if not math.isfinite(score) or not 0.0 <= score <= 1.0:
        raise ValueError("semantic_score must be finite and between 0 and 1.")
    return AuthorizedFragment(
        citation=_validate_token(fragment.citation, field="citation"),
        source_label=_validate_text(
            fragment.source_label,
            field="source_label",
            max_chars=MAX_SOURCE_LABEL_CHARS,
            allow_newlines=False,
        ),
        version=_validate_token(fragment.version, field="version"),
        title=_validate_text(
            fragment.title,
            field="title",
            max_chars=MAX_TITLE_CHARS,
            allow_newlines=False,
        ),
        content=_validate_text(
            fragment.content,
            field="content",
            max_chars=MAX_FRAGMENT_CHARS,
            allow_newlines=True,
        ),
        semantic_score=score,
        acl_authorized=True,
    )


def build_authorized_context(
    fragments: Sequence[AuthorizedFragment],
    *,
    max_fragments: int = MAX_FRAGMENTS,
    max_total_content_chars: int = MAX_TOTAL_CONTENT_CHARS,
) -> RagContext:
    """Build deterministic, minimized model context from authorized fragments.

    Semantic scores and ACL markers guide selection but are never included in
    the model payload. Every source body stays structurally labelled as
    untrusted document data.
    """
    if isinstance(fragments, (str, bytes)) or not isinstance(fragments, Sequence):
        raise TypeError("fragments must be a sequence.")
    if len(fragments) > MAX_CANDIDATES:
        raise ValueError("Too many candidate fragments for one turn.")
    if isinstance(max_fragments, bool) or not isinstance(max_fragments, int) or not 1 <= max_fragments <= MAX_FRAGMENTS:
        raise ValueError("max_fragments is outside the safe range.")
    if (
        isinstance(max_total_content_chars, bool)
        or not isinstance(max_total_content_chars, int)
        or not 1 <= max_total_content_chars <= MAX_TOTAL_CONTENT_CHARS
    ):
        raise ValueError("max_total_content_chars is outside the safe range.")

    validated = [_validated_fragment(fragment) for fragment in fragments]
    citations = [fragment.citation for fragment in validated]
    if len(citations) != len(set(citations)):
        raise ValueError("Citations must be unique within a turn.")

    selected: list[AuthorizedFragment] = []
    total_chars = 0
    for fragment in sorted(validated, key=lambda item: (-item.semantic_score, item.citation)):
        if len(selected) >= max_fragments:
            break
        proposed_total = total_chars + len(fragment.content)
        if proposed_total > max_total_content_chars:
            continue
        selected.append(fragment)
        total_chars = proposed_total

    if validated and not selected:
        raise ValueError("No authorized fragment fits the context budget.")

    payload = {
        "trust": "UNTRUSTED_DOCUMENT_CONTEXT",
        "context_version": RAG_CONTEXT_VERSION,
        "fragments": [
            {
                "trust": "UNTRUSTED_DOCUMENT_DATA",
                "citation": fragment.citation,
                "source": fragment.source_label,
                "version": fragment.version,
                "title": fragment.title,
                "content": fragment.content,
            }
            for fragment in selected
        ],
    }
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    if len(encoded) > MAX_MODEL_CONTEXT_CHARS:
        raise ValueError("Final model context exceeds the allowed limit.")
    return RagContext(
        model_context=encoded,
        citations=tuple(fragment.citation for fragment in selected),
    )
