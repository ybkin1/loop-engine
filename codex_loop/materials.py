from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


class MaterialError(ValueError):
    """Raised when the material catalog cannot be safely selected."""


@dataclass(frozen=True)
class Material:
    data: dict[str, Any]

    @property
    def material_id(self) -> str:
        return str(self.data["material_id"])

    @property
    def verification_status(self) -> str:
        return str(self.data.get("verification_status", "not_yet_checked"))


class MaterialCatalog:
    def __init__(self, materials: tuple[Material, ...]):
        self.materials = materials
        self._by_id = {item.material_id: item for item in materials}

    @classmethod
    def load(cls, path: Path) -> "MaterialCatalog":
        try:
            import yaml
        except ImportError as exc:
            raise MaterialError("PyYAML is required to read materials/catalog.yaml") from exc
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        raw_materials = payload.get("materials") if isinstance(payload, dict) else None
        if not isinstance(raw_materials, list):
            raise MaterialError("material catalog must contain a materials list")
        required = {"material_id", "category", "title", "problem_solved", "when_to_use", "risks", "evidence_level", "adaptation_notes"}
        materials: list[Material] = []
        for raw in raw_materials:
            missing = sorted(required - set(raw))
            if missing:
                raise MaterialError(f"{raw.get('material_id', '<unknown>')} missing: {', '.join(missing)}")
            materials.append(Material(raw))
        return cls(tuple(materials))

    def get(self, material_id: str) -> Material:
        try:
            return self._by_id[material_id]
        except KeyError as exc:
            raise MaterialError(f"unknown material: {material_id}") from exc

    def select(self, terms: tuple[str, ...], include_unverified: bool = False, limit: int = 12) -> tuple[Material, ...]:
        normalized = [term.lower() for term in terms if term.strip()]
        scored: list[tuple[int, Material]] = []
        for material in self.materials:
            if not include_unverified and material.verification_status in {"access_blocked", "not_yet_checked"}:
                continue
            haystack = " ".join(
                str(material.data.get(key, ""))
                for key in ("material_id", "category", "title", "problem_solved", "when_to_use", "adaptation_notes")
            ).lower()
            score = sum(1 for term in normalized if term in haystack)
            if score:
                scored.append((score, material))
        scored.sort(key=lambda pair: (-pair[0], pair[1].material_id))
        return tuple(material for _, material in scored[:limit])

    def selection_record(self, materials: tuple[Material, ...], terms: tuple[str, ...]) -> dict[str, Any]:
        return {
            "selection_version": "0.1.0",
            "query_terms": list(terms),
            "selected_materials": [
                {
                    "material_id": material.material_id,
                    "title": material.data["title"],
                    "verification_status": material.verification_status,
                    "evidence_level": material.data["evidence_level"],
                    "reason": material.data["problem_solved"],
                    "adaptation": material.data["adaptation_notes"],
                }
                for material in materials
            ],
            "excluded_unverified": [
                material.material_id
                for material in self.materials
                if material.verification_status in {"access_blocked", "not_yet_checked"}
            ],
            "status": "candidate",
        }
