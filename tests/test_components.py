from busfactor.ingest.components import component_of


def test_main_and_test_sources_share_a_component():
    main = "spark/src/main/scala/org/apache/spark/sql/delta/coordinatedcommits/Commit.scala"
    test = "spark/src/test/scala/org/apache/spark/sql/delta/coordinatedcommits/CommitSuite.scala"
    assert component_of(main) == "spark/coordinatedcommits"
    assert component_of(test) == component_of(main)


def test_package_root_and_longest_kernel_defaults_prefix():
    assert component_of("kernel/kernel-api/src/main/java/io/delta/kernel/Engine.java") == "kernel/kernel-api/(core)"
    assert component_of(
        "kernel/kernel-defaults/src/main/java/io/delta/kernel/defaults/internal/DefaultFileSystem.java"
    ) == "kernel/kernel-defaults/(core)"


def test_non_source_and_root_paths_use_documented_fallbacks():
    assert component_of("docs/source/quick-start.md") == "docs/source"
    assert component_of(".github/workflows/ci.yml") == ".github/workflows"
    assert component_of("connectors/docs/README.md") == "connectors/docs"
    assert component_of("pom.xml") == "root"


def test_real_spark_kernel_sharing_and_standalone_package_prefixes():
    assert component_of(
        "spark/v2/src/main/java/io/delta/spark/internal/v2/adapters/DeltaAdapter.java"
    ) == "spark/v2/adapters"
    assert component_of(
        "kernel-spark/src/main/java/io/delta/kernel/spark/catalog/CatalogManager.java"
    ) == "kernel-spark/catalog"
    assert component_of(
        "sharing/src/main/scala/io/delta/sharing/spark/client/DeltaSharingClient.scala"
    ) == "sharing/client"
    assert component_of(
        "connectors/standalone/src/main/scala/io/delta/standalone/internal/DeltaLog.scala"
    ) == "connectors/standalone/(core)"
    assert component_of(
        "connectors/standalone/src/main/scala/io/delta/standalone/DeltaLog.scala"
    ) == "connectors/standalone/(core)"
    assert component_of(
        "iceberg/src/main/java/org/apache/iceberg/util/DeltaLakeFileIO.java"
    ) == "iceberg/util"
    assert component_of(
        "spark/src/main/scala/com/databricks/spark/util/TestBarrier.scala"
    ) == "spark/util"


def test_versioned_sources_reverse_dns_and_test_resources():
    assert component_of(
        "connectors/standalone/src/main/scala-2.12/io/delta/standalone/internal/DeltaLog.scala"
    ) == "connectors/standalone/(core)"
    assert component_of(
        "connectors/examples/flink-example/src/main/java/org/example/sink/DeltaSinkExample.java"
    ) == "connectors/examples/flink-example/(core)"
    assert component_of(
        "spark/src/test/resources/delta/variant-stats-no-checkpoint/part-00000.parquet"
    ) == "spark/(test-resources)"
    assert component_of("spark/src/main/resources/error/delta-error-classes.json") == "spark/error"


def test_two_segment_paths_are_bucketed_as_files_not_components():
    assert component_of(".github/CODEOWNERS") == ".github/(files)"
    assert component_of("docs/.nvmrc") == "docs/(files)"
    assert component_of("flink/README.md") == "flink/(files)"
    assert component_of("project/SparkMimaExcludes.scala") == "project/(files)"
    assert component_of("protocol_rfcs/catalog-managed.md") == "protocol_rfcs/(files)"
