## Changed files

- Added [decision_keywords.py](../../src/busfactor/decision_keywords.py) and [link_decisions.py](../../src/busfactor/link_decisions.py).
- Added [04d issue-ref](../../queries/04d_derive_implements_issue_ref.cypher), [04e rfc-doc](../../queries/04e_derive_implements_rfc_doc.cypher), and [04f title-keyword](../../queries/04f_load_implements_keyword.cypher).
- Updated [04b participation](../../queries/04b_derive_participated_pr.cypher), [04c participation](../../queries/04c_derive_participated_issue.cypher), [README.md](../../README.md), and [PROGRESS.md](../../docs/PROGRESS.md).
- Added keyword and query-contract coverage in [test_decision_keywords.py](../../tests/test_decision_keywords.py), [test_derive_queries.py](../../tests/test_derive_queries.py), and [test_graph_integration.py](../../tests/test_graph_integration.py).

`PARTICIPATED_IN` includes low-confidence title matches and copies their confidence so later queries can filter them. Issue participation is marked high confidence. The README documents the order: load all data → `link_decisions` → `derive`.

## Verification and live run

`.venv/Scripts/python -m pytest -q`: **27 passed**. The FalkorDB integration test ran successfully.

The live linker’s final run reported **26 issue-ref**, **27 rfc-doc**, and **229 title-keyword edges by strongest `via`**. It loaded 258 PR-title match rows; some matched existing high-confidence edges, which retained their high confidence. The linker also printed per-decision edge counts and the three most recent linked PRs. I then ran `derive`; it created 267 PR participation edges and reported participation for all 19 decisions.

The three query paths are:

- **issue-ref:** follows PR → referenced Issue ← tracked Decision. This is explicit issue evidence, so it sets high confidence.
- **rfc-doc:** follows a Commit’s touched RFC file to its PR, matching the file’s trailing slug to the Decision. It covers moved RFC files under `accepted/` or `rejected/` while excluding README and template files.
- **title-keyword:** Python matches curated, bounded patterns against PR titles and loads the matching PR/Decision pairs. It adds `title-keyword` to the evidence sources without downgrading a high-confidence edge.

## Calibration

Counts below are **git commit subjects / cached PR-title match pairs**. The PR cache had 3,599 PRs and 258 matching PR/decision pairs.

| Decision | Commits | PR titles |
|---|---:|---:|
| column-mapping-usage-tracking | 0 | 0 |
| collated-string-type | 3 | 5 |
| checkpoint-protection | 5 | 5 |
| iceberg-writer-compat-v1 | 12 | 15 |
| iceberg-compat-v3 | 11 | 13 |
| nanosecond-timestamps | 1 | 1 |
| iceberg-v4-metadata | 3 | 3 |
| interval-types | 2 | 4 |
| file-type | 2 | 3 |
| user-defined-types | 1 | 3 |
| concurrent-identity-columns | 3 | 8 |
| catalog-managed | 58 | 88 |
| vacuum-protocol-check | 1 | 3 |
| in-commit-timestamps | 14 | 20 |
| type-widening | 31 | 39 |
| variant-type | 7 | 11 |
| variant-shredding | 14 | 18 |
| materialize-partition-columns | 8 | 9 |
| managed-commits | 6 | 10 |

Five example matched PR titles for each decision with matches:

- **collated-string-type (5):** [Protocol RFC] Specify collation readers and writers requirements; [SPARK] Match collated StringType in TypeWideningMetadata; [KERNEL] Add support for writing collated tables; Reject collated StringType keys in MapType constructor; [Protocol] Accept collated string type RFC.
- **checkpoint-protection (5):** [Spark] Add support for dropping the CheckpointProtection table feature; [Spark] CheckpointProtectionTableFeature base implementation; [SPARK][PROTOCOL RFC] Checkpoint Protection; [Kernel] Add basic support for `checkpointProtection` by limiting log cleanup; [Kernel] Allow checkpointProtection in iceberg-compact.
- **iceberg-writer-compat-v1 (15):** Add RFC for IcebergWriterCompatV1; [Kernel] Initial introduction of table feature icebergWriterCompatV1 and the class for its validation/updates; [Kernel][icebergWriterCompatV1 - PR#1] Introduce table feature IcebergWriterCompatV1; [Kernel][icebergWriterCompatV1 - PR#2] Introduce IcebergWriterCompatV1MetadataValidatorAndUpdater; [Kernel][icebergWriterCompatV1 - PR#3] E2E integration of the metadata validator and updater.
- **iceberg-compat-v3 (13):** [Kernel] Introduce IcebergCompatV3; [Kernel][#1] IcebergCompatV3 - add icebergCompatV3 table feature; [Kernel][#2] IcebergCompatV3 - move IcebergCompatCheck to base class; [Kernel][#3][test-only] IcebergCompatV3 - refactor validator suites; RFC for IcebergCompatV3.
- **nanosecond-timestamps (1):** [Protocol RFC] Nanosecond timestamps feature.
- **iceberg-v4-metadata (3):** Plumb Adaptive Metadata Tree back references onto file actions; Make the adaptive metadata tree incremental checkpoint path truly incremental; [Delta] Log adaptive metadata tree invariant violations.
- **interval-types (4):** [PROTOCOL] Interval Types RFC; [PROTOCOL] Interval Types RFC Update; [Spark] unblock interval types; [PROTOCOL] Interval types RFC: preserve narrowed spellings.
- **file-type (3):** [Protocol RFC] File data type; [Spark] Add fileType-preview table feature; [Protocol RFC] File data type: add relative URI support.
- **user-defined-types (3):** Document the udt (UserDefinedType) data type disposition (two PRs); [PROTOCOL RFC] User-Defined Types (UDT).
- **concurrent-identity-columns (8):** [PROTOCOL RFC] Add Concurrent Identity Columns table feature; [Spark] Foundation for Concurrent Identity Columns: metadata key, error classes; [Spark] Concurrent Identity Columns: sequence-service abstraction + in-memory backend; [Spark] Concurrent Identity Columns: executors can reserve ranges from the driver; [Spark] Concurrent Identity Columns: INSERT/append write path and table feature.
- **catalog-managed (88):** [PROTOCOL RFC] Catalog-managed Tables; [Spark] [CatalogManaged] Generate appropriate `CoordinatedCommitsStats`; [Kernel][Catalog-Managed] ParsedLogData; [Kernel][Catalog-Managed] ParsedCheckpointData ordering (two PRs).
- **vacuum-protocol-check (3):** [Kernel] include vacuumProtocolCheck as a catalogManaged dependency; [Kernel] Add vacuumProtocolCheck to UC-managed table creation; [Kernel] Add vacuumProtocolCheck as required dependency for catalogManaged.
- **in-commit-timestamps (20):** [Spark] Move some ICT test helper utils to InCommitTimestampTestUtils.scala; [WIP] [Kernel] ICT log replay; [Spark][Version Checksum] Read Protocol, Metadata, and ICT directly from the Checksum; [PROTOCOL] InCommitTimestamp: make the feature name consistent in the spec; [Kernel][InCommitTimestamp] Use ICT (if available) as the commit timestamp in getChanges.
- **type-widening (39):** [Delta Sharing] Enable D2D delta sharing with type widening; [Spark] Fix dependent constraints/generated columns checker for type widening; [Spark] Handle type widening in Delta streaming source; Accept Type Widening RFC; [Spark] Transition Type Widening table feature from preview to stable.
- **variant-type (11):** [KERNEL][VARIANT] Add support for `variantType` GA table feature type; [VARIANT] Upgrade variantType-preview to variantType (two PRs); [VARIANT] Accept `variantType` RFC; [Spark] Add VariantType support in schema conversion.
- **variant-shredding (18):** [PROTOCOL RFC] Variant Shredding; [VARIANT] Add enableVariantShredding Table Property and VariantShredding-preview table feature (two PRs); [KERNEL] Add Variant shredding preview table feature; [DOCS] Add variant GA and variant shredding docs for 4.0.
- **materialize-partition-columns (9):** [Protocol] Add description for a new writer feature MaterializePartitionColumns; [kernel] Add support for the materializePartitionColumns writer feature; Add RFC for MaterializePartitionColumns; [Protocol] Clarify enablement/support of materializePartitionColumns; Implement MaterializePartitionColumns writer feature.
- **managed-commits (10):** [Delta] Update Coordinated Commits Usage Logs; [SPARK] Tests for streaming use case of coordinated commits; [Kernel] Remove Coordinated Commits from public API (two PRs); [Spark] Extend streaming tests with coordinated commits (1/2).

I removed broad patterns after checking their matched subjects: plain `column mapping` matched unrelated work such as “Support column mapping in Delta V2 optimistic transactions”; generic `Iceberg V4` mixed in other RFCs, including the commitInfo/contentRoot proposal; and generic `identity column` matched non-concurrent work such as “Fix flaky identity column streaming test.” Those now require the RFC-specific usage-tracking, adaptive metadata tree, or concurrent identity wording. Type widening matched 31 commit subjects versus the supplied calibration of 30; the extra subject, about default row commit version when type widening is enabled, appears relevant. No commit was made.