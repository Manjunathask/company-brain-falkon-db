from busfactor.decision_keywords import KEYWORDS
from busfactor.link_decisions import matching_patterns, strongest_evidence, validate_keywords


def test_keyword_table_covers_all_rfc_slugs():
    assert {row["slug"] for row in validate_keywords()} == set(KEYWORDS)
    assert all(isinstance(patterns, list) for patterns in KEYWORDS.values())


def test_ict_is_case_sensitive_and_word_bounded():
    assert matching_patterns("Use ICT for commit timestamps", "in-commit-timestamps")
    assert not matching_patterns("Use ict for commit timestamps", "in-commit-timestamps")
    assert not matching_patterns("Use ICTs for commit timestamps", "in-commit-timestamps")
    assert not matching_patterns("conflict and dict handling", "in-commit-timestamps")


def test_variant_shredding_does_not_match_variant_type():
    assert matching_patterns("Enable variant shredding", "variant-shredding")
    assert matching_patterns("Enable variantShredding", "variant-shredding")
    assert not matching_patterns("Add variant type support", "variant-shredding")
    assert matching_patterns("Add variant type support", "variant-type")


def test_managed_commits_recognizes_renamed_feature():
    assert matching_patterns("Support coordinated commits", "managed-commits")
    assert matching_patterns("Support managed commits", "managed-commits")


def test_specific_patterns_avoid_known_false_positive_phrases():
    assert not matching_patterns("Support column mapping in Delta V2", "column-mapping-usage-tracking")
    assert not matching_patterns("Iceberg V4 commitInfo requirement", "iceberg-v4-metadata")
    assert not matching_patterns("Identity column high water mark", "concurrent-identity-columns")
    assert not matching_patterns("Set the file type", "file-type")
    assert not matching_patterns("Read an interval", "interval-types")
    assert not matching_patterns("Update timestamp", "nanosecond-timestamps")


def test_strongest_evidence_preserves_high_and_accumulates_sources():
    low = strongest_evidence(None, "title-keyword", "low")
    assert low == {"via": "title-keyword", "confidence": "low", "sources": ["title-keyword"]}
    high = strongest_evidence(low, "issue-ref", "high")
    assert high == {"via": "issue-ref", "confidence": "high", "sources": ["title-keyword", "issue-ref"]}
    still_high = strongest_evidence(high, "title-keyword", "low")
    assert still_high == high
    both_high = strongest_evidence(high, "rfc-doc", "high")
    assert both_high["confidence"] == "high"
    assert both_high["sources"] == ["title-keyword", "issue-ref", "rfc-doc"]

