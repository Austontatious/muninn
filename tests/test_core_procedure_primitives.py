from __future__ import annotations

from muninn import EvidenceRef, Muninn, MuninnConfig, ProcedureSpec
from muninn.packs import FridayPack


def test_procedure_write_query_and_bundle(tmp_path) -> None:
    db_path = tmp_path / "human_memory.db"
    config = MuninnConfig(db_path=str(db_path), space_key="repo:procedure-core")
    mem = Muninn(app_pack=FridayPack(), config=config)

    proc_id = mem.write_procedure(
        ProcedureSpec(
            procedure_name="Repo startup",
            intent_tags=["startup", "bootstrap"],
            preconditions=["repo cloned"],
            steps=["uv venv .venv", "uv pip install -e .[dev]"],
            expected_outcomes=["tests pass"],
            failure_modes=["uv missing"],
            fallbacks=["use system python with PYTHONPATH=src"],
            when_not_to_use=["system python locked"],
            task_types=["startup"],
            retrieval_roles=["startup", "validation"],
            tool_requirements=["uv"],
            verification_checks=["python -m pytest -q"],
            evidence_refs=[EvidenceRef(type="file", ref="/mnt/data/Muninn/RUNBOOK.md")],
            validation_status="validated",
        )
    )
    assert proc_id

    results = mem.query_procedures(
        task_label="start the repo", context_summary="need to run tests", task_type="startup", tool_names=["uv"]
    )
    assert results.procedures
    top = results.procedures[0]
    assert "uv venv .venv" in top.steps
    assert "tests pass" in top.expected_outcomes

    bundle = mem.rehydrate_procedure_bundle(
        task_label="start the repo",
        context_summary="need to run tests",
        task_type="startup",
        tool_names=["uv"],
        stage_depth="working_context",
    )
    assert [stage.stage for stage in bundle.stages] == ["orientation", "working_context"]

    deep = mem.rehydrate_procedure_bundle(
        task_label="start the repo",
        context_summary="need to run tests",
        task_type="startup",
        tool_names=["uv"],
        stage_depth="deep_evidence",
    )
    assert [stage.stage for stage in deep.stages] == ["orientation", "working_context", "deep_evidence"]
    deep_payload = deep.stages[-1].procedures[0]
    assert deep_payload["evidence"]


def test_procedure_supersede(tmp_path) -> None:
    db_path = tmp_path / "human_memory.db"
    config = MuninnConfig(db_path=str(db_path), space_key="repo:procedure-supersede")
    mem = Muninn(app_pack=FridayPack(), config=config)

    first_id = mem.write_procedure(
        ProcedureSpec(
            procedure_name="Validation order v1",
            intent_tags=["validation"],
            steps=["python -m pytest -q"],
            expected_outcomes=["tests pass"],
            validation_status="validated",
        )
    )

    new_id = mem.supersede_procedure(
        supersedes_card_id=first_id,
        spec=ProcedureSpec(
            procedure_name="Validation order v2",
            intent_tags=["validation"],
            steps=["python -m pytest -q", "python -m pytest -q tests/test_procedure_memory_endpoints.py"],
            expected_outcomes=["tests pass"],
            validation_status="validated",
        ),
    )
    assert new_id != first_id

    results = mem.query_procedures(task_label="run validation", task_type="validation")
    ids = {proc.id for proc in results.procedures}
    assert new_id in ids
    assert first_id not in ids
