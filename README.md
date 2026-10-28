# Open Heritage RAG Safety Kit

`Open Heritage RAG Safety Kit` is a small, dependency-free Python toolkit for building safer retrieval-augmented generation (RAG) prototypes around cultural-heritage material.

It is deliberately **not** a full RAG platform. It does not crawl, embed, retrieve, authenticate users, decide permissions, call a model, or host data. Instead, it makes a narrow boundary safer after a trusted application has made those decisions:

- accept only fragments that were already authorized by an upstream access-control layer;
- minimize metadata and apply deterministic context budgets;
- represent retrieved documents as untrusted data, not instructions;
- keep citations tied to the exact context used in a turn;
- record aggregate model usage without prompts, documents, identities, or user data.

The project is designed for multilingual public-interest archives and demonstrations. The included sample material is synthetic; it does not contain FallaERP data, member data, banking data, credentials, emails, or private association records.

## Why this exists

Heritage associations and small cultural institutions often want an assistant over their archive, but need to avoid turning every retrieved document into an instruction, leaking internal storage metadata, or letting a model fabricate document citations. This library isolates a conservative part of that problem so that it can be reviewed and tested independently.

## Scope and non-goals

| Included | Explicitly out of scope |
| --- | --- |
| Authorized-fragment validation | Retrieval, embeddings and vector stores |
| Context minimization and bounded selection | Authentication or access-control decisions |
| Citation membership validation | Model invocation, inference, training or fine-tuning |
| Privacy-minimized usage accounting | Production hosting or a user interface |

Using this library does **not** make a system secure by itself. The caller remains responsible for identity, access control, data protection, copyright, moderation, model safety, and human review.

## Quick start

Requires Python 3.10 or later. Runtime dependencies: none.

```python
from heritage_rag_safety import AuthorizedFragment, build_authorized_context, validate_answer_citations

context = build_authorized_context([
    AuthorizedFragment(
        citation="ARCHIVE-001#P1",
        source_label="Synthetic archive",
        version="v1",
        title="Community archive example",
        content="This is synthetic archival material for a safe RAG demonstration.",
        semantic_score=0.93,
        acl_authorized=True,
    )
])

answer = validate_answer_citations(
    "The archive contains a synthetic demonstration record.",
    ["ARCHIVE-001#P1"],
    context,
)
```

Run the local test suite without installing any package:

```bash
python -m unittest discover -s tests -v
```

Or run the example:

```bash
PYTHONPATH=src python examples/synthetic_heritage_demo.py
```

On Windows PowerShell, use `$env:PYTHONPATH='src'; python examples/synthetic_heritage_demo.py`.

## Proposed research direction

The next public milestone is a reproducible benchmark for citation integrity and prompt-injection resistance in Valencian, Spanish, and English cultural-heritage RAG workflows. It will use only synthetic, public-domain, or explicitly licensed material.

See [the proposal note](docs/PROJECT_PROPOSAL.md), [data governance](docs/DATA_GOVERNANCE.md), and [the threat-model summary](docs/THREAT_MODEL.md).

## License

MIT. See [LICENSE](LICENSE).

## Status

Pre-release `0.1.0`. The code is prepared as a standalone public project but has not yet been published or connected to any production association data.
