"""Small demonstration using synthetic, non-sensitive material."""

from heritage_rag_safety import AuthorizedFragment, build_authorized_context, validate_answer_citations


context = build_authorized_context(
    [
        AuthorizedFragment(
            citation="SYN-VAL-001#P1",
            source_label="Synthetic Valencian archive",
            version="v1",
            title="Arxiu sintètic de mostra",
            content="Aquest registre és fictici i només serveix per a proves de recuperació documental segura.",
            semantic_score=0.95,
            acl_authorized=True,
        )
    ]
)

answer = validate_answer_citations(
    "El registre de demostració és fictici i s'utilitza per a proves segures.",
    ["SYN-VAL-001#P1"],
    context,
)

print(answer)
print(context.model_context)
