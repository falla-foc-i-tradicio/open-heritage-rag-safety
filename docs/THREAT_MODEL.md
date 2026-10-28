# Threat-model summary

## Boundary

This package begins only after an upstream system has authenticated a person and made an access-control decision. It receives candidate fragments plus an explicit `acl_authorized=True` assertion.

It does not verify the upstream decision. That is intentional: authentication and authorization belong to the host application.

## Controls provided

- rejects fragments without an explicit prior authorization flag;
- accepts an allowlist of fragment fields only;
- validates bounded, canonical citation identifiers;
- does not expose semantic scores or ACL flags to the model context;
- labels every document payload as `UNTRUSTED_DOCUMENT_DATA`;
- bounds candidates, selected fragments, fragment size, and final model context;
- requires answer citations to come from the exact context of that turn;
- aggregates usage without retaining content, identities, or prompts.

## Non-controls

The package does not decide whether a source is accurate, whether a model's prose is true, whether a user has access, or whether a corpus may legally be used. It is not a substitute for human review, data protection assessment, copyright review, retrieval evaluation, or model-provider safety controls.
