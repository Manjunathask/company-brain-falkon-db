"""Curated title patterns that provide low-confidence PR-to-RFC evidence."""

KEYWORDS: dict[str, list[str]] = {
    # Usage tracking is the distinguishing part; plain column-mapping work is broader.
    "column-mapping-usage-tracking": [r"\bcolumn[- ]mapping usage tracking\b", r"\bcolumnMappingUsageTracking\b"],
    # Collation work is relevant when the title explicitly names the collated type/table behavior.
    "collated-string-type": [r"\bcollated string(?:type)?\b", r"\bcollated tables?\b", r"\bcollation readers and writers\b"],
    # The RFC's feature flag/class name is more specific than generic checkpoint work.
    "checkpoint-protection": [r"\bcheckpoint protection\b", r"\bCheckpointProtection(?:TableFeature)?\b"],
    # This is the exact protocol feature identifier.
    "iceberg-writer-compat-v1": [r"\bIcebergWriterCompatV1\b"],
    # This is the exact protocol feature identifier.
    "iceberg-compat-v3": [r"\bIcebergCompatV3\b"],
    # Nanosecond is distinctive for this timestamp RFC.
    "nanosecond-timestamps": [r"\bnanosecond(?:s)?\b"],
    # Adaptive metadata tree distinguishes this RFC from other Iceberg V4 proposals.
    "iceberg-v4-metadata": [r"\badaptive metadata tree\b", r"\badaptiveMetadataTree\b"],
    # Require the type phrase; bare interval is common in unrelated code.
    "interval-types": [r"\binterval[- ]types?\b", r"\bintervalType\b"],
    # Exact RFC name and table feature spelling; avoid generic "file type".
    "file-type": [r"\bfile data type\b", r"\bfileType(?:-preview)?\b"],
    # UDT and user-defined type are the RFC's explicit names.
    "user-defined-types": [r"\buser[- ]defined types?\b", r"\bUDT\b"],
    # Concurrent is essential to distinguish this RFC from ordinary identity columns.
    "concurrent-identity-columns": [r"\bconcurrent identity columns?\b", r"\bconcurrentIdentityColumns?\b"],
    # Catalog-managed is a distinctive table feature and has a camel-case flag.
    "catalog-managed": [r"\bcatalog[- ]managed\b", r"\bcatalogManaged\b"],
    # The full feature phrase avoids unrelated vacuum protocol changes.
    "vacuum-protocol-check": [r"\bvacuum protocol check\b", r"\bvacuumProtocolCheck\b"],
    # ICT is deliberately case-sensitive and bounded; exclude ICTs and substrings.
    "in-commit-timestamps": [r"\bin[- ]commit timestamps?\b", r"\binCommitTimestamp\b", r"\bICT\b"],
    # Type Widening is the RFC and its feature-flag spelling.
    "type-widening": [r"\btype widening\b", r"\btypeWidening\b"],
    # Variant type identifies the base type RFC, including its flag spelling.
    "variant-type": [r"\bvariant type\b", r"\bvariantType\b"],
    # Require the feature name; bare "variant" is too broad.
    "variant-shredding": [r"\bvariant shredd(?:ing|ed)\b", r"\bvariantShredding\b", r"\benableVariantShredding\b"],
    # The action phrase or exact feature name is specific to this proposal.
    "materialize-partition-columns": [r"\bmaterializ\w* partition columns?\b", r"\bmaterializ\w*PartitionColumns\b"],
    # Coordinated Commits was the former name of the Managed Commits proposal.
    "managed-commits": [r"\bcoordinated commits?\b", r"\bmanaged commits?\b"],
}
