from __future__ import annotations

import tempfile

from muninn import EvidenceRef, MemoryItem, Muninn, MuninnConfig, ProcedureSpec
from muninn.packs import FridayPack


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        config = MuninnConfig(db_path=f"{tmp}/human_memory.db", space_key="embedded-demo")
        mem = Muninn(app_pack=FridayPack(), config=config)

        card_id = mem.write(
            MemoryItem(
                app_id="friday",
                kind="constraint",
                title="Constraint",
                summary="Only use staged bundles",
                payload={"constraint": "Only use staged bundles"},
                evidence=[EvidenceRef(type="file", ref="/tmp/example.py:10")],
            )
        )
        print(f"Wrote card: {card_id}")

        procedure_id = mem.write_procedure(
            ProcedureSpec(
                procedure_name="Local startup sequence",
                intent_tags=["startup", "bootstrap"],
                preconditions=["python installed", "repo cloned"],
                steps=["uv venv .venv", "uv pip install -e .[dev]", "python -m pytest -q"],
                expected_outcomes=["tests pass"],
                failure_modes=["missing uv", "virtualenv creation failure"],
                fallbacks=["use system python with PYTHONPATH=src"],
                when_not_to_use=["when system python is locked down"],
                task_types=["startup"],
                retrieval_roles=["startup", "validation"],
                evidence_refs=[EvidenceRef(type="file", ref="/mnt/data/Muninn/RUNBOOK.md")],
                validation_status="validated",
            )
        )
        print(f"Wrote procedure: {procedure_id}")

        bundle = mem.rehydrate_bundle(query="staged bundles")
        print("Bundle stages:", [stage.stage for stage in bundle.stages])
        print("Bundle decisions:", [d.stage for d in bundle.explanation.decisions])

        procedure_bundle = mem.rehydrate_procedure_bundle(
            task_label="start the repo locally",
            context_summary="need to run tests",
            task_type="startup",
            tool_names=["uv"],
            stage_depth="working_context",
        )
        print("Procedure stages:", [stage.stage for stage in procedure_bundle.stages])


if __name__ == "__main__":
    main()
