"""Deterministic checks for the bounded T-0036 F-001..F-006 repair."""

from __future__ import annotations

import argparse
import re
from datetime import datetime, timezone
from pathlib import Path

import yaml


CATALOG_REQUIRED = {
    "material_id",
    "category",
    "title",
    "source_url",
    "source_type",
    "authority",
    "version_or_date",
    "problem_solved",
    "when_to_use",
    "when_not_to_use",
    "inputs",
    "outputs",
    "template_or_schema",
    "adaptation_notes",
    "risks",
    "evidence_level",
    "verification_status",
}
AUTHORITY_ENUM = {
    "international_standard",
    "government",
    "official_vendor",
    "industry_body",
    "open_source_project",
    "research_literature",
    "community_method",
    "loop_project",
}
FRESHNESS_KEYS = {
    "material_id",
    "source_locator",
    "access_method",
    "retrieved_at",
    "http_status",
    "final_url",
    "page_title",
    "failure_reason",
    "verification_status",
    "source_observation",
}


def load_yaml(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def parse_rfc3339(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def markdown_ids(path: Path) -> set[str]:
    ids = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("| ") and not line.startswith("| ---"):
            value = line.split("|", 2)[1].strip()
            if value != "ID" and re.fullmatch(r"[A-Z0-9-]+", value):
                ids.add(value)
    return ids


def coverage_ids(path: Path) -> set[str]:
    ids: set[str] = set()
    for token in re.findall(r"\b[A-Z]+(?:-[A-Z]+)*-\d{3}(?:\.\.\d{3})?\b", path.read_text(encoding="utf-8")):
        if ".." not in token:
            ids.add(token)
            continue
        prefix, bounds = token.rsplit("-", 1)
        start, end = (int(part) for part in bounds.split(".."))
        ids.update(f"{prefix}-{number:03d}" for number in range(start, end + 1))
    return ids


def main(root: Path) -> int:
    catalog_data = load_yaml(root / "materials/catalog.yaml")
    catalog = catalog_data["materials"]
    catalog_ids = [item["material_id"] for item in catalog]
    catalog_set = set(catalog_ids)
    register_data = load_yaml(root / "materials/source-register.yaml")
    records = register_data["records"]
    register_ids = [record["material_id"] for record in records]
    register_set = set(register_ids)
    phase = load_yaml(root / ".ai/evidence/T-0036/simulation/phase-profile.v0.1.yaml")
    project = load_yaml(root / ".ai/evidence/T-0036/simulation/project-profile.v0.1.yaml")
    selection = load_yaml(root / ".ai/evidence/T-0036/simulation/material-selection.v0.1.yaml")

    errors: list[str] = []
    if len(catalog) != 46:
        errors.append(f"catalog_count={len(catalog)}")
    if len(catalog_set) != len(catalog_ids):
        errors.append("catalog_duplicate_ids")
    for item in catalog:
        missing = CATALOG_REQUIRED - set(item)
        if missing:
            errors.append(f"{item.get('material_id')}:missing_catalog_fields={sorted(missing)}")
    authority_errors = [item["material_id"] for item in catalog if item["authority"] not in AUTHORITY_ENUM]
    if authority_errors:
        errors.append(f"authority_enum_violations={authority_errors}")

    if len(records) != 46 or len(register_set) != 46:
        errors.append(f"register_count={len(records)} unique={len(register_set)}")
    if catalog_set != register_set:
        errors.append(f"register_id_delta={sorted(catalog_set ^ register_set)}")
    md_ids = markdown_ids(root / "materials/source-register.md")
    if md_ids != catalog_set:
        errors.append(f"markdown_id_delta={sorted(catalog_set ^ md_ids)}")

    catalog_by_id = {item["material_id"]: item for item in catalog}
    status_conflicts = []
    freshness_errors = []
    run = register_data["retrieval_run"]
    started = parse_rfc3339(run["started_at"])
    completed = parse_rfc3339(run["completed_at"])
    for record in records:
        missing = FRESHNESS_KEYS - set(record)
        if missing:
            freshness_errors.append(f"{record.get('material_id')}:missing={sorted(missing)}")
            continue
        item = catalog_by_id[record["material_id"]]
        if item["verification_status"] != record["verification_status"]:
            status_conflicts.append(record["material_id"])
        try:
            retrieved = parse_rfc3339(record["retrieved_at"])
            if not started <= retrieved <= completed:
                freshness_errors.append(f"{record['material_id']}:retrieved_at_outside_run")
        except (TypeError, ValueError):
            freshness_errors.append(f"{record['material_id']}:bad_retrieved_at")
        if record["access_method"] == "http_get":
            if record["http_status"] is None and not record["failure_reason"]:
                freshness_errors.append(f"{record['material_id']}:missing_http_failure")
            if record["verification_status"] == "content_read" and (
                not record["final_url"] or record["page_title"] == "not_observed" or record["failure_reason"] != "none"
            ):
                freshness_errors.append(f"{record['material_id']}:invalid_content_read_invariants")
        elif record["access_method"] == "local_file":
            if record["http_status"] is not None or record["final_url"] != "not_applicable":
                freshness_errors.append(f"{record['material_id']}:invalid_local_sentinels")
        else:
            freshness_errors.append(f"{record['material_id']}:unknown_access_method")
    if status_conflicts:
        errors.append(f"status_conflicts={status_conflicts}")
    if freshness_errors:
        errors.extend(freshness_errors)
    if run["http_count"] != 44 or run["local_count"] != 2:
        errors.append(f"access_counts=http:{run['http_count']} local:{run['local_count']}")

    covered = coverage_ids(root / "materials/coverage-matrix.md")
    if covered != catalog_set:
        errors.append(f"coverage_delta={sorted(catalog_set ^ covered)}")

    if project["project_selection_id"] != "MSEL-T0036-SIM-PROJECT-V0.1":
        errors.append("project_selection_id_invalid")
    if selection["parent_selection_id"] != project["project_selection_id"]:
        errors.append("selection_parent_mismatch")
    project_materials = set(project["selected_materials"])
    phase_materials = {item["material_id"] for item in selection["selected_materials"]}
    if not phase_materials < project_materials:
        errors.append("phase_materials_not_strict_subset")
    project_templates = set(project["selected_templates"])
    phase_templates = set(selection["selected_templates"])
    if not phase_templates < project_templates:
        errors.append("phase_templates_not_strict_subset")
    if project["phase_profile"] != phase["phase_profile_id"] or selection["phase_profile_id"] != phase["phase_profile_id"]:
        errors.append("phase_profile_reference_mismatch")
    if phase["project_profile_id"] != project["project_profile_id"]:
        errors.append("phase_project_back_reference_mismatch")
    if phase.get("simulation_only") is not True or phase.get("planned_not_executed") is not True:
        errors.append("simulation_boundary_markers_missing")

    print(f"catalog={len(catalog)}")
    print(f"authority_violations={len(authority_errors)}")
    print(f"register={len(register_set)}/{len(catalog_set)}")
    print(f"status_conflicts={len(status_conflicts)}")
    print(f"markdown_ids={len(md_ids)}")
    print(f"coverage={len(covered)}/{len(catalog_set)}")
    print(f"freshness={len(records) - len(freshness_errors)}/{len(records)}")
    print(f"phase_profile_ref={'1/1' if not any('phase_profile' in error for error in errors) else '0/1'}")
    print(f"selection_materials={len(phase_materials)}/{len(project_materials)}")
    print(f"selection_templates={len(phase_templates)}/{len(project_templates)}")
    if errors:
        print("FAIL")
        for error in errors:
            print(f"- {error}")
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("project_root", type=Path)
    args = parser.parse_args()
    raise SystemExit(main(args.project_root))
