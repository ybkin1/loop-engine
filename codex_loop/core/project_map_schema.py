"""
PROJECT_MAP Schema and Validator — Single source of truth for project structure.

PROJECT_MAP.yaml is the complete structured description of a project. The
ProjectionEngine reads this file and generates per-role "projections" — filtered
views that show only what each role needs to see.

This module provides:
  - PROJECT_MAP_SCHEMA: JSON Schema (Draft 2020-12) for validation
  - ProjectMapValidator: structural validation + referential integrity checks
  - ProjectMapQuery: path-based data access for the ProjectionEngine
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# ============================================================================
# JSON Schema for PROJECT_MAP.yaml
# ============================================================================

PROJECT_MAP_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://loop-engine.dev/schemas/project_map.schema.json",
    "title": "Project Map",
    "description": "Complete structured description of a project for Loop's ProjectionEngine.",
    "type": "object",
    "required": ["project"],
    "additionalProperties": False,
    "properties": {
        "project": {
            "type": "object",
            "required": ["name", "type", "description"],
            "additionalProperties": False,
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Project name."
                },
                "type": {
                    "type": "string",
                    "enum": [
                        "web_app",
                        "mobile_app",
                        "cli_tool",
                        "api_service",
                        "desktop_app",
                        "embedded",
                        "library",
                        "other",
                    ],
                    "description": "Project type."
                },
                "description": {
                    "type": "string",
                    "description": "Brief description of the project."
                },
            },
        },
        "pages": {
            "type": "array",
            "description": "Frontend pages — projection source for frontend roles.",
            "items": {
                "type": "object",
                "required": ["id", "path", "title"],
                "additionalProperties": False,
                "properties": {
                    "id": {
                        "type": "string",
                        "description": "Unique page identifier, e.g. 'page-login'."
                    },
                    "path": {
                        "type": "string",
                        "description": "URL path, e.g. '/login'."
                    },
                    "title": {
                        "type": "string",
                        "description": "Human-readable page title."
                    },
                    "elements": {
                        "type": "array",
                        "description": "UI elements on this page.",
                        "items": {
                            "type": "object",
                            "required": ["id", "type", "label"],
                            "additionalProperties": False,
                            "properties": {
                                "id": {
                                    "type": "string",
                                    "description": "Unique element identifier, e.g. 'btn-submit'."
                                },
                                "type": {
                                    "type": "string",
                                    "enum": [
                                        "button",
                                        "input",
                                        "link",
                                        "table",
                                        "form",
                                        "navigation",
                                        "text",
                                        "image",
                                        "dropdown",
                                        "modal",
                                        "toast",
                                    ],
                                    "description": "Element type."
                                },
                                "label": {
                                    "type": "string",
                                    "description": "Display text of the element."
                                },
                                "properties": {
                                    "type": "object",
                                    "description": "Additional properties, e.g. {action: submit_form, target: page-next}."
                                },
                            },
                        },
                    },
                    "states": {
                        "type": "array",
                        "description": "Page states and what is displayed in each.",
                        "items": {
                            "type": "object",
                            "required": ["name", "description"],
                            "additionalProperties": False,
                            "properties": {
                                "name": {
                                    "type": "string",
                                    "enum": ["loading", "empty", "error", "success", "default"],
                                    "description": "State name."
                                },
                                "description": {
                                    "type": "string",
                                    "description": "What is shown to the user in this state."
                                },
                            },
                        },
                    },
                    "navigation_from": {
                        "type": "array",
                        "description": "Page IDs that can navigate to this page.",
                        "items": {"type": "string"},
                    },
                    "navigation_to": {
                        "type": "array",
                        "description": "Page IDs that this page can navigate to.",
                        "items": {"type": "string"},
                    },
                },
            },
        },
        "api_endpoints": {
            "type": "array",
            "description": "API endpoints — projection source for backend roles.",
            "items": {
                "type": "object",
                "required": ["id", "method", "path"],
                "additionalProperties": False,
                "properties": {
                    "id": {
                        "type": "string",
                        "description": "Unique endpoint identifier, e.g. 'api-login'."
                    },
                    "method": {
                        "type": "string",
                        "enum": ["GET", "POST", "PUT", "DELETE", "PATCH"],
                        "description": "HTTP method."
                    },
                    "path": {
                        "type": "string",
                        "description": "URL path, e.g. '/api/auth/login'."
                    },
                    "request": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "headers": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Required request headers."
                            },
                            "body_schema": {
                                "type": "object",
                                "description": "Simplified JSON Schema for the request body."
                            },
                        },
                    },
                    "response": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "success_schema": {
                                "type": "object",
                                "description": "Simplified JSON Schema for the success response body."
                            },
                            "error_codes": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Possible error codes, e.g. ['401', '403', '500']."
                            },
                        },
                    },
                    "auth_required": {
                        "type": "boolean",
                        "description": "Whether this endpoint requires authentication."
                    },
                },
            },
        },
        "modules": {
            "type": "array",
            "description": "Code modules — projection source for architect roles.",
            "items": {
                "type": "object",
                "required": ["id"],
                "additionalProperties": False,
                "properties": {
                    "id": {
                        "type": "string",
                        "description": "Unique module identifier, e.g. 'auth-module'."
                    },
                    "responsibilities": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of responsibilities this module handles."
                    },
                    "depends_on": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Module IDs this module depends on."
                    },
                    "depended_by": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Module IDs that depend on this module."
                    },
                },
            },
        },
        "database": {
            "type": "object",
            "description": "Database schema — projection source for backend testing roles.",
            "additionalProperties": False,
            "properties": {
                "tables": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["name"],
                        "additionalProperties": False,
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "Table name."
                            },
                            "columns": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "required": ["name", "type"],
                                    "additionalProperties": False,
                                    "properties": {
                                        "name": {
                                            "type": "string",
                                            "description": "Column name."
                                        },
                                        "type": {
                                            "type": "string",
                                            "description": "Column data type, e.g. 'VARCHAR(255)'."
                                        },
                                        "nullable": {
                                            "type": "boolean",
                                            "description": "Whether NULL is allowed."
                                        },
                                        "primary_key": {
                                            "type": "boolean",
                                            "description": "Whether this column is part of the primary key."
                                        },
                                        "foreign_key": {
                                            "oneOf": [
                                                {"type": "string"},
                                                {"type": "null"},
                                            ],
                                            "description": "Foreign key reference in 'table.column' format, or null."
                                        },
                                    },
                                },
                            },
                            "indexes": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Index definitions, e.g. ['idx_users_email ON users(email)']."
                            },
                        },
                    },
                },
            },
        },
    },
}


# ============================================================================
# ProjectMapValidator
# ============================================================================

class ProjectMapValidator:
    """Validates PROJECT_MAP.yaml for structural and referential integrity.

    Usage::

        validator = ProjectMapValidator()
        data = {"project": {"name": "MyApp", "type": "web_app", "description": "..."}}
        is_valid, errors = validator.validate(data)

        # Or validate a YAML file directly:
        is_valid, errors = validator.validate_file(Path("PROJECT_MAP.yaml"))

        # Check cross-references:
        ref_errors = validator.check_referential_integrity(data)
    """

    def __init__(self) -> None:
        self._validator_class = None
        self._jsonschema_available = False
        try:
            import jsonschema

            self._jsonschema_available = True
            self._validator_class = jsonschema.Draft202012Validator
        except ImportError:
            self._jsonschema_available = False

    # ── Structural Validation ────────────────────────────────────────────

    def validate(self, data: dict[str, Any]) -> tuple[bool, list[str]]:
        """Validate *data* against PROJECT_MAP_SCHEMA.

        Returns ``(is_valid, errors)`` where *errors* is a list of
        human-readable error messages.
        """
        errors: list[str] = []

        if not isinstance(data, dict):
            return False, ["Root value must be a JSON object (dict)."]

        if self._jsonschema_available:
            errors = self._validate_with_jsonschema(data)
        else:
            errors = self._validate_manually(data)

        return len(errors) == 0, errors

    def validate_file(self, path: Path) -> tuple[bool, list[str]]:
        """Read a YAML (or JSON) file at *path* and validate its contents."""
        path = Path(path)
        if not path.exists():
            return False, [f"File not found: {path}"]

        raw = path.read_text(encoding="utf-8")

        # Try YAML first, fall back to JSON
        try:
            import yaml

            data = yaml.safe_load(raw)
        except ImportError:
            data = json.loads(raw)
        except Exception:
            try:
                data = json.loads(raw)
            except json.JSONDecodeError as exc:
                return False, [f"Failed to parse file as YAML or JSON: {exc}"]

        if data is None:
            return False, ["File is empty or contains only null."]

        if not isinstance(data, dict):
            return False, ["Root value must be a JSON object (dict)."]

        return self.validate(data)

    # ── Referential Integrity ───────────────────────────────────────────

    def check_referential_integrity(self, data: dict[str, Any]) -> list[str]:
        """Check that all cross-references within *data* are valid.

        Checks performed:
        - Page navigation_from / navigation_to IDs exist in pages
        - Module depends_on / depended_by IDs exist in modules
        - Page element IDs are unique within each page
        - Page IDs are unique
        - Module IDs are unique
        - API endpoint IDs are unique
        """
        errors: list[str] = []

        seen_page_ids: set[str] = set()

        # ── Pages ────────────────────────────────────────────────────────
        pages: list[dict[str, Any]] = data.get("pages", []) or []
        for page in pages:
            pid = page.get("id", "")
            if pid and pid in seen_page_ids:
                errors.append(f"Duplicate page ID: '{pid}'")
            seen_page_ids.add(pid)

            # Check element ID uniqueness within this page
            element_ids: set[str] = set()
            for elem in page.get("elements", []) or []:
                eid = elem.get("id", "")
                if eid and eid in element_ids:
                    errors.append(f"Duplicate element ID '{eid}' in page '{pid}'")
                element_ids.add(eid)

        # Check navigation references
        for page in pages:
            pid = page.get("id", "")

            for target in page.get("navigation_from", []) or []:
                if target not in seen_page_ids:
                    errors.append(
                        f"Page '{pid}' navigation_from references unknown page '{target}'"
                    )

            for target in page.get("navigation_to", []) or []:
                if target not in seen_page_ids:
                    errors.append(
                        f"Page '{pid}' navigation_to references unknown page '{target}'"
                    )

        # ── API Endpoints ────────────────────────────────────────────────
        seen_api_ids: set[str] = set()
        for ep in data.get("api_endpoints", []) or []:
            eid = ep.get("id", "")
            if eid and eid in seen_api_ids:
                errors.append(f"Duplicate API endpoint ID: '{eid}'")
            seen_api_ids.add(eid)

        # ── Modules ──────────────────────────────────────────────────────
        seen_module_ids: set[str] = set()
        for mod in data.get("modules", []) or []:
            mid = mod.get("id", "")
            if mid and mid in seen_module_ids:
                errors.append(f"Duplicate module ID: '{mid}'")
            seen_module_ids.add(mid)

        for mod in data.get("modules", []) or []:
            mid = mod.get("id", "")
            for dep in mod.get("depends_on", []) or []:
                if dep not in seen_module_ids:
                    errors.append(
                        f"Module '{mid}' depends_on unknown module '{dep}'"
                    )
            for dep in mod.get("depended_by", []) or []:
                if dep not in seen_module_ids:
                    errors.append(
                        f"Module '{mid}' depended_by references unknown module '{dep}'"
                    )

        # ── Database tables ──────────────────────────────────────────────
        seen_table_names: set[str] = set()
        for table in data.get("database", {}).get("tables", []) or []:
            tname = table.get("name", "")
            if tname and tname in seen_table_names:
                errors.append(f"Duplicate database table name: '{tname}'")
            seen_table_names.add(tname)

            # Check column name uniqueness within table
            col_names: set[str] = set()
            for col in table.get("columns", []) or []:
                cname = col.get("name", "")
                if cname and cname in col_names:
                    errors.append(
                        f"Duplicate column name '{cname}' in table '{tname}'"
                    )
                col_names.add(cname)

        return errors

    # ── Internal: jsonschema-based validation ────────────────────────────

    def _validate_with_jsonschema(self, data: dict[str, Any]) -> list[str]:
        """Validate using the jsonschema library."""
        assert self._validator_class is not None
        validator = self._validator_class(PROJECT_MAP_SCHEMA)
        return [err.message for err in validator.iter_errors(data)]

    # ── Internal: manual validation fallback ─────────────────────────────

    def _validate_manually(self, data: dict[str, Any]) -> list[str]:
        """Manual structural validation when jsonschema is unavailable."""
        errors: list[str] = []

        # --- project ---
        if "project" not in data:
            errors.append("Missing required top-level key: 'project'")
        else:
            proj = data["project"]
            if not isinstance(proj, dict):
                errors.append("'project' must be an object.")
            else:
                for field in ("name", "type", "description"):
                    if field not in proj:
                        errors.append(f"Missing required field 'project.{field}'")
                if "type" in proj:
                    valid_types = {
                        "web_app", "mobile_app", "cli_tool", "api_service",
                        "desktop_app", "embedded", "library", "other",
                    }
                    if proj["type"] not in valid_types:
                        errors.append(
                            f"'project.type' must be one of {sorted(valid_types)}, got '{proj['type']}'"
                        )

        # --- pages ---
        if "pages" in data:
            pages = data["pages"]
            if not isinstance(pages, list):
                errors.append("'pages' must be an array.")
            else:
                for i, page in enumerate(pages):
                    if not isinstance(page, dict):
                        errors.append(f"pages[{i}] must be an object.")
                        continue
                    for field in ("id", "path", "title"):
                        if field not in page:
                            errors.append(f"pages[{i}]: missing required field '{field}'")
                    # elements
                    elements = page.get("elements", [])
                    if isinstance(elements, list):
                        valid_elm_types = {
                            "button", "input", "link", "table", "form",
                            "navigation", "text", "image", "dropdown", "modal", "toast",
                        }
                        for j, elem in enumerate(elements):
                            if not isinstance(elem, dict):
                                errors.append(f"pages[{i}].elements[{j}] must be an object.")
                                continue
                            for field in ("id", "type", "label"):
                                if field not in elem:
                                    errors.append(f"pages[{i}].elements[{j}]: missing '{field}'")
                            if "type" in elem and elem["type"] not in valid_elm_types:
                                errors.append(
                                    f"pages[{i}].elements[{j}]: invalid type '{elem['type']}'"
                                )
                    # states
                    states = page.get("states", [])
                    if isinstance(states, list):
                        valid_states = {"loading", "empty", "error", "success", "default"}
                        for j, st in enumerate(states):
                            if not isinstance(st, dict):
                                errors.append(f"pages[{i}].states[{j}] must be an object.")
                                continue
                            for field in ("name", "description"):
                                if field not in st:
                                    errors.append(f"pages[{i}].states[{j}]: missing '{field}'")
                            if "name" in st and st["name"] not in valid_states:
                                errors.append(
                                    f"pages[{i}].states[{j}]: invalid state '{st['name']}'"
                                )

        # --- api_endpoints ---
        if "api_endpoints" in data:
            eps = data["api_endpoints"]
            if not isinstance(eps, list):
                errors.append("'api_endpoints' must be an array.")
            else:
                valid_methods = {"GET", "POST", "PUT", "DELETE", "PATCH"}
                for i, ep in enumerate(eps):
                    if not isinstance(ep, dict):
                        errors.append(f"api_endpoints[{i}] must be an object.")
                        continue
                    for field in ("id", "method", "path"):
                        if field not in ep:
                            errors.append(f"api_endpoints[{i}]: missing '{field}'")
                    if ep.get("method") not in valid_methods:
                        errors.append(
                            f"api_endpoints[{i}]: invalid method '{ep.get('method')}'"
                        )

        # --- modules ---
        if "modules" in data:
            mods = data["modules"]
            if not isinstance(mods, list):
                errors.append("'modules' must be an array.")
            else:
                for i, mod in enumerate(mods):
                    if not isinstance(mod, dict):
                        errors.append(f"modules[{i}] must be an object.")
                        continue
                    if "id" not in mod:
                        errors.append(f"modules[{i}]: missing 'id'")

        # --- database ---
        if "database" in data:
            db = data["database"]
            if not isinstance(db, dict):
                errors.append("'database' must be an object.")
            elif "tables" in db:
                tables = db["tables"]
                if not isinstance(tables, list):
                    errors.append("'database.tables' must be an array.")
                else:
                    for i, table in enumerate(tables):
                        if not isinstance(table, dict):
                            errors.append(f"database.tables[{i}] must be an object.")
                            continue
                        if "name" not in table:
                            errors.append(f"database.tables[{i}]: missing 'name'")
                        columns = table.get("columns", [])
                        if isinstance(columns, list):
                            for j, col in enumerate(columns):
                                if not isinstance(col, dict):
                                    errors.append(f"database.tables[{i}].columns[{j}] must be an object.")
                                    continue
                                for field in ("name", "type"):
                                    if field not in col:
                                        errors.append(f"database.tables[{i}].columns[{j}]: missing '{field}'")

        # --- Unknown top-level keys ---
        allowed_keys = {"project", "pages", "api_endpoints", "modules", "database"}
        for key in data:
            if key not in allowed_keys:
                errors.append(f"Unknown top-level key: '{key}'")

        return errors


# ============================================================================
# ProjectMapQuery
# ============================================================================

class ProjectMapQuery:
    """Path-based query engine for PROJECT_MAP data.

    Used by the ProjectionEngine to extract role-specific projections.

    Supported path syntax::

        # Top-level keys
        query(data, "project")         -> data["project"]
        query(data, "pages")           -> data["pages"]

        # Named item in array by id
        query(data, "pages.page-login")            -> page with id="page-login"
        query(data, "modules.auth-module")         -> module with id="auth-module"

        # Sub-field of named item
        query(data, "pages.page-login.elements")   -> elements list for page-login
        query(data, "pages.page-login.title")      -> title of page-login

        # Wildcard (*) — all items in array
        query(data, "pages.*.elements")            -> list of all elements across all pages
        query(data, "pages.*.states")              -> list of all states across all pages

        # Deep wildcard
        query(data, "modules.*.depends_on")        -> list of all depends_on lists

        # Index-based access (when id doesn't matter)
        query(data, "pages.0")                     -> first page
        query(data, "pages.0.elements")            -> elements of first page

        # Top-level arrays with wildcard
        query(data, "api_endpoints.*.method")      -> list of all HTTP methods
    """

    @staticmethod
    def query(data: dict[str, Any], path: str) -> Any:
        """Query *data* using a dot-separated *path*.

        Returns ``None`` if the path does not exist.
        """
        if not path:
            return data

        parts = path.split(".")
        current: Any = data

        for part in parts:
            if current is None:
                return None

            if part == "*":
                # Wildcard: current must be a list; apply rest of path to each item
                if not isinstance(current, list):
                    return None
                remaining = ".".join(parts[parts.index(part) + 1:])
                if remaining:
                    subquery = ProjectMapQuery()
                    results = []
                    for item in current:
                        result = subquery.query(item, remaining)
                        if result is not None:
                            # If result is a list, extend (flatten once)
                            if isinstance(result, list):
                                # Only flatten if the *next* step after wildcard is
                                # another collection; we flatten all list results
                                # for consistency with the "arr_of_arrs -> flat" convention.
                                results.extend(result)
                            else:
                                results.append(result)
                    return results if results else None
                else:
                    return current

            if isinstance(current, list):
                # Try numeric index
                if part.isdigit():
                    idx = int(part)
                    if 0 <= idx < len(current):
                        current = current[idx]
                    else:
                        return None
                else:
                    # Search by id field
                    found = None
                    for item in current:
                        if isinstance(item, dict) and item.get("id") == part:
                            found = item
                            break
                    current = found
            elif isinstance(current, dict):
                current = current.get(part)
            else:
                return None

        return current


# ============================================================================
# Convenience: full validation (schema + referential integrity)
# ============================================================================

def validate_project_map(data: dict[str, Any]) -> tuple[bool, list[str]]:
    """Run full validation: structural schema + referential integrity.

    Returns ``(is_valid, all_errors)``.
    """
    validator = ProjectMapValidator()
    is_valid, errors = validator.validate(data)
    ref_errors = validator.check_referential_integrity(data)
    all_errors = errors + ref_errors
    return len(all_errors) == 0, all_errors
