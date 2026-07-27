"""
Tests for PROJECT_MAP schema, validator, and query engine.

Covers:
  - Valid PROJECT_MAP passes structural validation
  - Missing required fields cause validation failure
  - Invalid enum values are rejected
  - Referential integrity: navigation references, module dependencies
  - Referential integrity: duplicate IDs
  - ProjectMapQuery: exact path, named-item lookup, wildcard queries
  - Full validate_project_map() convenience function
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

# Ensure the parent directory is on sys.path so we can import loop_core
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loop_core.project_map_schema import (
    PROJECT_MAP_SCHEMA,
    ProjectMapValidator,
    ProjectMapQuery,
    validate_project_map,
)


# ============================================================================
# Test fixture: a fully valid PROJECT_MAP
# ============================================================================

def make_valid_project_map() -> dict:
    """Return a minimal but complete valid PROJECT_MAP covering all dimensions."""
    return {
        "project": {
            "name": "TestApp",
            "type": "web_app",
            "description": "A test web application.",
        },
        "pages": [
            {
                "id": "page-login",
                "path": "/login",
                "title": "Login",
                "elements": [
                    {
                        "id": "btn-submit",
                        "type": "button",
                        "label": "Sign In",
                        "properties": {"action": "submit_form"},
                    },
                    {
                        "id": "input-email",
                        "type": "input",
                        "label": "Email",
                        "properties": {"validation": ["required", "email"]},
                    },
                ],
                "states": [
                    {"name": "default", "description": "Login form visible."},
                    {"name": "loading", "description": "Spinner shown after submit."},
                    {"name": "error", "description": "Error message displayed."},
                ],
                "navigation_from": ["page-home"],
                "navigation_to": ["page-dashboard"],
            },
            {
                "id": "page-dashboard",
                "path": "/dashboard",
                "title": "Dashboard",
                "elements": [
                    {
                        "id": "link-logout",
                        "type": "link",
                        "label": "Logout",
                        "properties": {"action": "navigate", "target": "page-login"},
                    },
                ],
                "states": [
                    {"name": "default", "description": "Dashboard content."},
                    {"name": "empty", "description": "No data message."},
                ],
                "navigation_from": ["page-login"],
                "navigation_to": ["page-login"],
            },
            {
                "id": "page-home",
                "path": "/",
                "title": "Home",
                "elements": [],
                "states": [
                    {"name": "default", "description": "Welcome page."},
                ],
                "navigation_from": [],
                "navigation_to": ["page-login"],
            },
        ],
        "api_endpoints": [
            {
                "id": "api-login",
                "method": "POST",
                "path": "/api/auth/login",
                "request": {
                    "headers": ["Content-Type: application/json"],
                    "body_schema": {
                        "type": "object",
                        "properties": {
                            "email": {"type": "string"},
                            "password": {"type": "string"},
                        },
                    },
                },
                "response": {
                    "success_schema": {
                        "type": "object",
                        "properties": {"token": {"type": "string"}},
                    },
                    "error_codes": ["401", "429"],
                },
                "auth_required": False,
            },
            {
                "id": "api-profile",
                "method": "GET",
                "path": "/api/user/profile",
                "request": {
                    "headers": ["Authorization: Bearer <token>"],
                },
                "response": {
                    "success_schema": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "email": {"type": "string"},
                        },
                    },
                    "error_codes": ["401", "404"],
                },
                "auth_required": True,
            },
        ],
        "modules": [
            {
                "id": "auth-module",
                "responsibilities": ["User authentication", "Token management"],
                "depends_on": ["db-module"],
                "depended_by": ["api-module"],
            },
            {
                "id": "db-module",
                "responsibilities": ["Database access", "Query building"],
                "depends_on": [],
                "depended_by": ["auth-module", "api-module"],
            },
            {
                "id": "api-module",
                "responsibilities": ["Request routing", "Response serialization"],
                "depends_on": ["auth-module", "db-module"],
                "depended_by": [],
            },
        ],
        "database": {
            "tables": [
                {
                    "name": "users",
                    "columns": [
                        {"name": "id", "type": "INTEGER", "nullable": False,
                         "primary_key": True, "foreign_key": None},
                        {"name": "email", "type": "VARCHAR(255)", "nullable": False,
                         "primary_key": False, "foreign_key": None},
                        {"name": "password_hash", "type": "VARCHAR(255)", "nullable": False,
                         "primary_key": False, "foreign_key": None},
                    ],
                    "indexes": ["idx_users_email ON users(email)"],
                },
                {
                    "name": "sessions",
                    "columns": [
                        {"name": "id", "type": "INTEGER", "nullable": False,
                         "primary_key": True, "foreign_key": None},
                        {"name": "user_id", "type": "INTEGER", "nullable": False,
                         "primary_key": False, "foreign_key": "users.id"},
                        {"name": "token", "type": "VARCHAR(512)", "nullable": False,
                         "primary_key": False, "foreign_key": None},
                    ],
                    "indexes": [],
                },
            ],
        },
    }


# ============================================================================
# Schema Structure Tests
# ============================================================================

class TestSchemaStructure:
    """Tests for the PROJECT_MAP_SCHEMA constant itself."""

    def test_schema_is_valid_json_schema(self):
        """The schema dict should have required JSON Schema meta-fields."""
        assert PROJECT_MAP_SCHEMA["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert "$id" in PROJECT_MAP_SCHEMA
        assert PROJECT_MAP_SCHEMA["type"] == "object"
        assert "properties" in PROJECT_MAP_SCHEMA

    def test_schema_requires_project(self):
        """'project' must be in the required list at the top level."""
        assert "project" in PROJECT_MAP_SCHEMA["required"]

    def test_project_type_enum_has_all_values(self):
        """The project.type enum should include all 8 types from the spec."""
        type_enum = PROJECT_MAP_SCHEMA["properties"]["project"]["properties"]["type"]["enum"]
        expected = ["web_app", "mobile_app", "cli_tool", "api_service",
                    "desktop_app", "embedded", "library", "other"]
        assert sorted(type_enum) == sorted(expected)

    def test_element_type_enum_has_all_values(self):
        """The element.type enum should include all 11 element types."""
        elem_items = PROJECT_MAP_SCHEMA["properties"]["pages"]["items"]["properties"]["elements"]["items"]
        type_enum = elem_items["properties"]["type"]["enum"]
        expected = ["button", "input", "link", "table", "form",
                    "navigation", "text", "image", "dropdown", "modal", "toast"]
        assert sorted(type_enum) == sorted(expected)

    def test_page_state_enum_has_all_values(self):
        """The page state.name enum should include all 5 states."""
        state_items = PROJECT_MAP_SCHEMA["properties"]["pages"]["items"]["properties"]["states"]["items"]
        state_enum = state_items["properties"]["name"]["enum"]
        expected = ["loading", "empty", "error", "success", "default"]
        assert sorted(state_enum) == sorted(expected)

    def test_http_method_enum_has_all_values(self):
        """The API endpoint method enum should include all 5 HTTP methods."""
        method_enum = PROJECT_MAP_SCHEMA["properties"]["api_endpoints"]["items"]["properties"]["method"]["enum"]
        expected = ["GET", "POST", "PUT", "DELETE", "PATCH"]
        assert sorted(method_enum) == sorted(expected)

    def test_all_top_level_sections_defined(self):
        """Schema properties should include all 5 top-level sections."""
        props = set(PROJECT_MAP_SCHEMA["properties"].keys())
        expected = {"project", "pages", "api_endpoints", "modules", "database"}
        assert props == expected


# ============================================================================
# Structural Validation Tests
# ============================================================================

class TestStructuralValidation:
    """Tests for ProjectMapValidator.validate() — schema conformance."""

    def test_valid_project_map_passes(self):
        """A complete valid PROJECT_MAP should pass validation."""
        validator = ProjectMapValidator()
        data = make_valid_project_map()
        is_valid, errors = validator.validate(data)
        assert is_valid is True, f"Expected valid, got errors: {errors}"
        assert len(errors) == 0

    def test_minimal_project_only_passes(self):
        """A project with only the required 'project' key should pass."""
        validator = ProjectMapValidator()
        data = {
            "project": {
                "name": "Minimal",
                "type": "library",
                "description": "Bare minimum.",
            }
        }
        is_valid, errors = validator.validate(data)
        assert is_valid is True, f"Expected valid, got errors: {errors}"

    def test_missing_project_fails(self):
        """Missing the required 'project' key should fail validation."""
        validator = ProjectMapValidator()
        data = {"pages": []}
        is_valid, errors = validator.validate(data)
        assert is_valid is False
        assert any("project" in err.lower() for err in errors)

    def test_missing_project_name_fails(self):
        """Missing project.name should fail."""
        validator = ProjectMapValidator()
        data = {
            "project": {
                "type": "web_app",
                "description": "No name.",
            }
        }
        is_valid, errors = validator.validate(data)
        assert is_valid is False
        assert any("name" in err.lower() for err in errors)

    def test_invalid_project_type_fails(self):
        """An invalid project.type should fail validation."""
        validator = ProjectMapValidator()
        data = {
            "project": {
                "name": "Bad Type",
                "type": "quantum_computer",
                "description": "Invalid type.",
            }
        }
        is_valid, errors = validator.validate(data)
        assert is_valid is False
        assert any("quantum_computer" in err for err in errors)

    def test_page_missing_id_fails(self):
        """A page missing its 'id' field should fail."""
        validator = ProjectMapValidator()
        data = {
            "project": {"name": "T", "type": "web_app", "description": "D"},
            "pages": [
                {"path": "/p", "title": "No ID Page"},
            ],
        }
        is_valid, errors = validator.validate(data)
        assert is_valid is False
        assert any("id" in err.lower() for err in errors)

    def test_element_invalid_type_fails(self):
        """An element with an invalid type should fail."""
        validator = ProjectMapValidator()
        data = {
            "project": {"name": "T", "type": "web_app", "description": "D"},
            "pages": [
                {
                    "id": "p1", "path": "/p1", "title": "P1",
                    "elements": [
                        {"id": "e1", "type": "rocket_launcher", "label": "Bad"},
                    ],
                },
            ],
        }
        is_valid, errors = validator.validate(data)
        assert is_valid is False
        assert any("rocket_launcher" in err for err in errors)

    def test_api_endpoint_invalid_method_fails(self):
        """An API endpoint with an invalid HTTP method should fail."""
        validator = ProjectMapValidator()
        data = {
            "project": {"name": "T", "type": "api_service", "description": "D"},
            "api_endpoints": [
                {"id": "ep1", "method": "BREW", "path": "/coffee"},
            ],
        }
        is_valid, errors = validator.validate(data)
        assert is_valid is False
        assert any("method" in err.lower() or "BREW" in err for err in errors)

    def test_unknown_top_level_key_fails(self):
        """An unknown top-level key should fail (strict schema)."""
        validator = ProjectMapValidator()
        data = {
            "project": {"name": "T", "type": "web_app", "description": "D"},
            "random_field": "unexpected",
        }
        is_valid, errors = validator.validate(data)
        assert is_valid is False
        assert any("additional" in err.lower() or "unknown" in err.lower() or "random_field" in err.lower() for err in errors)

    def test_page_with_extra_properties_fails(self):
        """A page object with extra/additional properties should fail."""
        validator = ProjectMapValidator()
        data = {
            "project": {"name": "T", "type": "web_app", "description": "D"},
            "pages": [
                {"id": "p1", "path": "/p1", "title": "P1", "unexpected_extra": 42},
            ],
        }
        is_valid, errors = validator.validate(data)
        assert is_valid is False


# ============================================================================
# Referential Integrity Tests
# ============================================================================

class TestReferentialIntegrity:
    """Tests for ProjectMapValidator.check_referential_integrity()."""

    def test_valid_references_pass(self):
        """A valid PROJECT_MAP with correct cross-references should pass."""
        validator = ProjectMapValidator()
        data = make_valid_project_map()
        errors = validator.check_referential_integrity(data)
        assert len(errors) == 0, f"Expected no ref errors, got: {errors}"

    def test_navigation_from_unknown_page(self):
        """navigation_from referencing a non-existent page should error."""
        validator = ProjectMapValidator()
        data = make_valid_project_map()
        # page-login references page-home which exists — this is fine.
        # But if we add a non-existent reference:
        data["pages"][0]["navigation_from"].append("page-nonexistent")
        errors = validator.check_referential_integrity(data)
        assert len(errors) >= 1
        assert any("page-nonexistent" in err for err in errors)

    def test_navigation_to_unknown_page(self):
        """navigation_to referencing a non-existent page should error."""
        validator = ProjectMapValidator()
        data = make_valid_project_map()
        data["pages"][1]["navigation_to"].append("page-ghost")
        errors = validator.check_referential_integrity(data)
        assert len(errors) >= 1
        assert any("page-ghost" in err for err in errors)

    def test_depends_on_unknown_module(self):
        """depends_on referencing a non-existent module should error."""
        validator = ProjectMapValidator()
        data = make_valid_project_map()
        data["modules"][0]["depends_on"].append("missing-module")
        errors = validator.check_referential_integrity(data)
        assert len(errors) >= 1
        assert any("missing-module" in err for err in errors)

    def test_depended_by_unknown_module(self):
        """depended_by referencing a non-existent module should error."""
        validator = ProjectMapValidator()
        data = make_valid_project_map()
        data["modules"][1]["depended_by"].append("zombie-module")
        errors = validator.check_referential_integrity(data)
        assert len(errors) >= 1
        assert any("zombie-module" in err for err in errors)

    def test_duplicate_page_id(self):
        """Two pages with the same ID should be flagged."""
        validator = ProjectMapValidator()
        data = make_valid_project_map()
        data["pages"].append({
            "id": "page-login",  # Duplicate!
            "path": "/login2",
            "title": "Login Clone",
        })
        errors = validator.check_referential_integrity(data)
        assert len(errors) >= 1
        assert any("duplicate" in err.lower() and "page-login" in err for err in errors)

    def test_duplicate_module_id(self):
        """Two modules with the same ID should be flagged."""
        validator = ProjectMapValidator()
        data = make_valid_project_map()
        data["modules"].append({
            "id": "auth-module",  # Duplicate!
            "responsibilities": ["Clone"],
        })
        errors = validator.check_referential_integrity(data)
        assert len(errors) >= 1
        assert any("duplicate" in err.lower() and "auth-module" in err for err in errors)

    def test_duplicate_api_endpoint_id(self):
        """Two API endpoints with the same ID should be flagged."""
        validator = ProjectMapValidator()
        data = make_valid_project_map()
        data["api_endpoints"].append({
            "id": "api-login",  # Duplicate!
            "method": "GET",
            "path": "/api/auth/login-dupe",
        })
        errors = validator.check_referential_integrity(data)
        assert len(errors) >= 1
        assert any("duplicate" in err.lower() and "api-login" in err for err in errors)

    def test_duplicate_element_id_in_same_page(self):
        """Two elements with the same ID in one page should be flagged."""
        validator = ProjectMapValidator()
        data = make_valid_project_map()
        data["pages"][0]["elements"].append({
            "id": "btn-submit",  # Duplicate in page-login
            "type": "button",
            "label": "Also Submit",
        })
        errors = validator.check_referential_integrity(data)
        assert len(errors) >= 1
        assert any("btn-submit" in err for err in errors)

    def test_duplicate_table_name(self):
        """Two database tables with the same name should be flagged."""
        validator = ProjectMapValidator()
        data = make_valid_project_map()
        data["database"]["tables"].append({
            "name": "users",  # Duplicate!
            "columns": [],
        })
        errors = validator.check_referential_integrity(data)
        assert len(errors) >= 1
        assert any("duplicate" in err.lower() and "users" in err for err in errors)

    def test_duplicate_column_name_in_table(self):
        """Two columns with the same name in one table should be flagged."""
        validator = ProjectMapValidator()
        data = make_valid_project_map()
        data["database"]["tables"][0]["columns"].append({
            "name": "email",  # Duplicate in users table
            "type": "VARCHAR(255)",
        })
        errors = validator.check_referential_integrity(data)
        assert len(errors) >= 1
        assert any("email" in err and "users" in err for err in errors)


# ============================================================================
# ProjectMapQuery Tests
# ============================================================================

class TestProjectMapQuery:
    """Tests for ProjectMapQuery.query() — path-based data access."""

    def setup_method(self):
        self.data = make_valid_project_map()
        self.query = ProjectMapQuery()

    def test_query_top_level_key(self):
        """Querying a top-level key returns its value."""
        result = self.query.query(self.data, "project")
        assert result == self.data["project"]

    def test_query_nested_key(self):
        """Querying a nested key inside a dict returns the value."""
        result = self.query.query(self.data, "project.name")
        assert result == "TestApp"

    def test_query_nonexistent_key(self):
        """Querying a key that does not exist returns None."""
        result = self.query.query(self.data, "project.nonexistent")
        assert result is None

    def test_query_named_page(self):
        """Querying by ID in a pages array returns the matching page."""
        result = self.query.query(self.data, "pages.page-login")
        assert result is not None
        assert result["id"] == "page-login"
        assert result["title"] == "Login"

    def test_query_nonexistent_page_id(self):
        """Querying a page ID that doesn't exist returns None."""
        result = self.query.query(self.data, "pages.page-nope")
        assert result is None

    def test_query_named_page_field(self):
        """Querying a field of a named page works."""
        result = self.query.query(self.data, "pages.page-login.title")
        assert result == "Login"

    def test_query_named_module(self):
        """Querying by ID in a modules array returns the matching module."""
        result = self.query.query(self.data, "modules.auth-module")
        assert result is not None
        assert result["id"] == "auth-module"

    def test_query_named_api_endpoint(self):
        """Querying by ID in api_endpoints array returns the matching endpoint."""
        result = self.query.query(self.data, "api_endpoints.api-profile")
        assert result is not None
        assert result["method"] == "GET"

    def test_query_numeric_index(self):
        """Querying by numeric index in an array returns the item."""
        result = self.query.query(self.data, "pages.0")
        assert result is not None
        assert result["id"] == "page-login"

    def test_query_numeric_index_out_of_range(self):
        """Querying an out-of-range numeric index returns None."""
        result = self.query.query(self.data, "pages.99")
        assert result is None

    def test_query_wildcard_pages_elements(self):
        """Querying pages.*.elements returns all elements across all pages."""
        result = self.query.query(self.data, "pages.*.elements")
        assert result is not None
        assert isinstance(result, list)
        # Elements from all pages: btn-submit, input-email, link-logout
        assert len(result) >= 3
        element_ids = {e["id"] for e in result if isinstance(e, dict)}
        assert "btn-submit" in element_ids
        assert "input-email" in element_ids
        assert "link-logout" in element_ids

    def test_query_wildcard_modules_depends_on(self):
        """Querying modules.*.depends_on returns all depends_on lists."""
        result = self.query.query(self.data, "modules.*.depends_on")
        assert result is not None
        assert isinstance(result, list)
        # auth-module depends_on [db-module], db-module depends_on [],
        # api-module depends_on [auth-module, db-module]
        assert "db-module" in result  # from auth-module
        assert "auth-module" in result  # from api-module
        # Should include all depends_on values (flat list)

    def test_query_wildcard_top_level_array_field(self):
        """Querying api_endpoints.*.method returns all HTTP methods."""
        result = self.query.query(self.data, "api_endpoints.*.method")
        assert result is not None
        assert isinstance(result, list)
        assert "POST" in result
        assert "GET" in result

    def test_query_wildcard_alone(self):
        """Querying just 'pages.*' returns all pages."""
        result = self.query.query(self.data, "pages.*")
        assert result is not None
        assert isinstance(result, list)
        assert len(result) == 3

    def test_query_wildcard_nonexistent_field(self):
        """Wildcard with non-existent sub-field returns None."""
        result = self.query.query(self.data, "pages.*.frobnicator")
        assert result is None

    def test_query_wildcard_on_non_array(self):
        """Wildcard on a non-array returns None."""
        result = self.query.query(self.data, "project.*")
        assert result is None

    def test_query_empty_path(self):
        """Empty path returns the entire data dict."""
        result = self.query.query(self.data, "")
        assert result is self.data

    def test_query_module_depends_on(self):
        """Specific module's depends_on list is correctly retrieved."""
        result = self.query.query(self.data, "modules.auth-module.depends_on")
        assert result == ["db-module"]

    def test_query_page_elements_by_index(self):
        """Elements of a specific page accessed by index."""
        result = self.query.query(self.data, "pages.0.elements")
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["id"] == "btn-submit"


# ============================================================================
# Full Validation (structural + referential integrity)
# ============================================================================

class TestValidateProjectMap:
    """Tests for the convenience function validate_project_map()."""

    def test_valid_data_passes_full_validation(self):
        """A valid PROJECT_MAP passes both schema and referential checks."""
        data = make_valid_project_map()
        is_valid, errors = validate_project_map(data)
        assert is_valid is True, f"Expected valid, got errors: {errors}"
        assert len(errors) == 0

    def test_schema_error_bubbles_up(self):
        """Schema validation errors are included in the result."""
        data = {"random_key": "garbage"}
        is_valid, errors = validate_project_map(data)
        assert is_valid is False
        assert len(errors) >= 1

    def test_ref_error_bubbles_up(self):
        """Referential integrity errors are included in the result."""
        data = make_valid_project_map()
        data["pages"][0]["navigation_to"].append("page-nowhere")
        is_valid, errors = validate_project_map(data)
        assert is_valid is False
        assert len(errors) >= 1
        assert any("page-nowhere" in e for e in errors)

    def test_both_error_types_combined(self):
        """When both schema and ref errors exist, both are returned."""
        data = make_valid_project_map()
        # Add a ref error
        data["pages"][0]["navigation_to"].append("page-nowhere")
        # Add a schema error — remove project.name
        del data["project"]["name"]
        is_valid, errors = validate_project_map(data)
        assert is_valid is False
        has_schema_error = any("name" in e.lower() for e in errors)
        has_ref_error = any("page-nowhere" in e for e in errors)
        assert has_schema_error, f"Expected schema error, got: {errors}"
        assert has_ref_error, f"Expected ref error, got: {errors}"


# ============================================================================
# File-based Validation Tests
# ============================================================================

class TestValidateFile:
    """Tests for ProjectMapValidator.validate_file()."""

    def test_valid_json_file_passes(self):
        """A valid JSON file should pass validation."""
        import json
        validator = ProjectMapValidator()
        data = make_valid_project_map()

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump(data, f)
            tmp_path = f.name

        try:
            is_valid, errors = validator.validate_file(Path(tmp_path))
            assert is_valid is True, f"Expected valid, got errors: {errors}"
        finally:
            Path(tmp_path).unlink()

    def test_file_not_found(self):
        """A non-existent file path should fail."""
        validator = ProjectMapValidator()
        is_valid, errors = validator.validate_file(Path("/nonexistent/path.yaml"))
        assert is_valid is False
        assert any("not found" in err.lower() for err in errors)

    def test_invalid_json_file(self):
        """An invalid JSON file should fail."""
        validator = ProjectMapValidator()

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            f.write("{invalid json content")
            tmp_path = f.name

        try:
            is_valid, errors = validator.validate_file(Path(tmp_path))
            assert is_valid is False
        finally:
            Path(tmp_path).unlink()


# ============================================================================
# Edge Cases
# ============================================================================

class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_empty_data_dict(self):
        """An empty dict should fail validation."""
        validator = ProjectMapValidator()
        is_valid, errors = validator.validate({})
        assert is_valid is False
        assert len(errors) >= 1

    def test_none_data(self):
        """None (not a dict) should fail."""
        validator = ProjectMapValidator()
        is_valid, errors = validator.validate(None)  # type: ignore[arg-type]
        assert is_valid is False

    def test_string_data(self):
        """A string (not a dict) should fail."""
        validator = ProjectMapValidator()
        is_valid, errors = validator.validate("not a dict")  # type: ignore[arg-type]
        assert is_valid is False

    def test_empty_pages_ok(self):
        """An empty pages array is valid."""
        validator = ProjectMapValidator()
        data = {
            "project": {"name": "No Pages", "type": "cli_tool", "description": "T"},
            "pages": [],
        }
        is_valid, errors = validator.validate(data)
        assert is_valid is True, f"Expected valid, got: {errors}"

    def test_empty_modules_referential_integrity_ok(self):
        """No modules means no referential errors."""
        validator = ProjectMapValidator()
        data = make_valid_project_map()
        data["modules"] = []
        errors = validator.check_referential_integrity(data)
        assert len(errors) == 0

    def test_pages_with_null_fields(self):
        """Pages where arrays are explicitly null should not crash validator."""
        validator = ProjectMapValidator()
        data = {
            "project": {"name": "T", "type": "web_app", "description": "D"},
            "pages": [
                {"id": "p1", "path": "/p1", "title": "P1",
                 "elements": None, "states": None,
                 "navigation_from": None, "navigation_to": None},
            ],
        }
        # This should not raise an exception; may or may not be valid
        # depending on whether jsonschema treats null as non-array
        is_valid, errors = validator.validate(data)
        # At minimum, it should not crash
        assert isinstance(is_valid, bool)

    def test_database_with_no_tables(self):
        """A database section with no tables is valid."""
        validator = ProjectMapValidator()
        data = {
            "project": {"name": "T", "type": "api_service", "description": "D"},
            "database": {"tables": []},
        }
        is_valid, errors = validator.validate(data)
        assert is_valid is True, f"Expected valid, got: {errors}"
