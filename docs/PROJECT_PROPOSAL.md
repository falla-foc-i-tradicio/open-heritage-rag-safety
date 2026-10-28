# Project proposal: safe multilingual heritage RAG

## Public objective

Build and evaluate a small, reproducible safety layer for retrieval-augmented assistants working with cultural-heritage collections in Valencian, Spanish, and English.

## Open outputs

- dependency-free reference implementation for bounded, ACL-first RAG context;
- citation-integrity checks tied to each turn's context;
- privacy-minimized usage accounting;
- synthetic evaluation cases for prompt injection, citation drift, multilingual queries, and over-sized source documents;
- documentation describing what the library deliberately does not solve.

## Compute-research direction

If a research collaborator joins, compute may be used for reproducible experiments comparing retrieval and answer-generation approaches across multilingual synthetic/public datasets. Metrics would include citation membership, citation coverage, resistance to instruction-like text inside documents, and resource consumption.

No grant compute would be used for the association's production ERP, member data, or commercial operation. Any future research application would accurately name the academic or research partner and use only permitted data.

## Why a standalone repository

The association's operational ERP remains private because it contains domain-specific business logic and integrations. This repository isolates a generic, reusable contribution and makes review possible without exposing personal data or the operational system.
