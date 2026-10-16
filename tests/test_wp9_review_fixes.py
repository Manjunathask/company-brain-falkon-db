from busfactor.agent.memory import Memory, entity_keys
from busfactor.db import ROOT
from busfactor.refresh import count_commits_per_component


def test_wp9_query_numbering_has_one_feature_per_number_group():
    expected = {
        "15_refresh_watermarks.cypher", "15a_refresh_head_files.cypher", "15b_refresh_component_risk.cypher",
        "16_team_write_observation.cypher", "16b_team_recall.cypher",
        "16c_team_record_refresh.cypher", "16d_team_list.cypher",
    }
    found = {path.name for path in (ROOT / "queries").glob("*.cypher") if path.name.startswith(("15", "16"))}
    assert found == expected
    docs = (ROOT / "docs" / "QUERIES.md").read_text(encoding="utf-8")
    assert all(f"`{name}`" in docs for name in expected)


def test_refresh_summary_counts_distinct_commits_per_component():
    commits = [
        {"sha": "a", "files": [{"path": "kernel/api/A.scala"}, {"path": "kernel/api/B.scala"}]},
        {"sha": "b", "files": [{"path": "kernel/api/C.scala"}]},
    ]
    assert count_commits_per_component(commits) == {"kernel/api": 2}


class _RecallMemory(Memory):
    def __init__(self, rows):
        self.rows = rows
    def recall(self, **kwargs):
        return [dict(row) for row in self.rows]


def test_prompt_recall_prioritizes_question_caps_eight_and_drops_empty_or_unchanged():
    rows = [{"entity": f"person:person{i}", "lastAsked": 2000 - i, "corrections": [],
             "changedSinceLastAsked": [{"commitCount": 0, "prCount": 0, "commits": [], "prs": []}]}
            for i in range(9)]
    rows.append({"entity": "module:kernel", "lastAsked": 10, "corrections": [],
                 "changedSinceLastAsked": [{"commitCount": 1, "prCount": 0, "commits": [{"author": "alice"}], "prs": []}]})
    recalled = _RecallMemory(rows).recall_for_prompt("What changed in kernel?", ["module:kernel"])
    assert len(recalled) == 8
    assert recalled[0]["entity"] == "module:kernel"
    assert "corrections" not in recalled[0]
    assert "changedSinceLastAsked" not in recalled[1]
    assert recalled[0]["changedSinceLastAsked"][0]["commitCount"] == 1


def test_test_resource_components_are_not_saved_as_memory_entities():
    graph = {"nodes": [
        {"label": "Component", "key": "spark/test/(test-resources)"},
        {"label": "Component", "key": "kernel/api"},
    ]}
    assert entity_keys(graph) == ["component:kernel/api"]


def test_prompt_recall_hides_historical_test_resource_entities():
    memory = _RecallMemory([{"entity": "component:kernel/(test-resources)", "lastAsked": 10},
                            {"entity": "component:kernel/api", "lastAsked": 9}])
    recalled = memory.recall_for_prompt("kernel", ["component:kernel/(test-resources)"])
    assert [row["entity"] for row in recalled] == ["component:kernel/api"]


def test_memory_queries_filter_absent_corrections_and_team_null_rows():
    recall = (ROOT / "queries" / "14c_mem_recall.cypher").read_text(encoding="utf-8")
    team_recall = (ROOT / "queries" / "16b_team_recall.cypher").read_text(encoding="utf-8")
    assert "CASE WHEN c IS NULL THEN null" in recall
    assert "WHERE row IS NOT NULL" in team_recall
