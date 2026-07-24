"""
Seeded Defect Suite for Loop role validation.

This package contains intentionally defective code samples (sample_code/),
a registry of known defects (defect_registry.json), and a test framework
(test_defect_detection.py) that verifies the detection infrastructure
is properly configured.

Purpose:
    Validate that Loop's AI-powered review roles (security-engineer,
    quality-engineer, test-engineer, architect, independent-reviewer)
    can actually detect known defects rather than merely appearing to
    perform reviews.

Usage:
    python -m pytest tests/seeded_defects/ -v

Structure:
    sample_code/              — Deliberately buggy code with DEFECT-SD-XXX markers
    defect_registry.json      — Structured catalog of all seeded defects
    test_defect_detection.py  — Tests verifying detection infrastructure
"""
