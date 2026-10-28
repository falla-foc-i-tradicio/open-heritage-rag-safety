import unittest

from heritage_rag_safety.citations import validate_answer_citations
from heritage_rag_safety.context import AuthorizedFragment, build_authorized_context


def context():
    return build_authorized_context(
        [
            AuthorizedFragment(
                citation="DOC-1#P1",
                source_label="Synthetic source",
                version="v1",
                title="Title",
                content="Synthetic public test content.",
                semantic_score=0.9,
                acl_authorized=True,
            )
        ]
    )


class CitationTests(unittest.TestCase):
    def test_valid_citation_is_preserved(self):
        answer = validate_answer_citations("A documented answer.", ["DOC-1#P1"], context())
        self.assertEqual(("DOC-1#P1",), answer.citations)

    def test_rejects_citation_not_in_current_context(self):
        with self.assertRaises(PermissionError):
            validate_answer_citations("A documented answer.", ["DOC-999#P1"], context())

    def test_requires_citation_for_document_based_answer(self):
        with self.assertRaises(ValueError):
            validate_answer_citations("A documented answer.", [], context())

    def test_rejects_duplicate_citation(self):
        with self.assertRaises(ValueError):
            validate_answer_citations("A documented answer.", ["DOC-1#P1", "DOC-1#P1"], context())


if __name__ == "__main__":
    unittest.main()
