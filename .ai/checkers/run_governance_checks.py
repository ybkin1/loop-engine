import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate_gate_register import validate_gate_register


def run_checks(gates_path, project_root=None, output_path=None):
    project_root = Path(project_root or Path(gates_path).parents[2])
    result = validate_gate_register(gates_path, project_root=project_root)
    result["checker_id"] = "run_governance_checks"

    if output_path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, indent=2), encoding="utf-8")

    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--gates", required=True)
    parser.add_argument("--project-root", default=None)
    parser.add_argument("--output", default=None)
    args = parser.parse_args()
    result = run_checks(args.gates, project_root=args.project_root, output_path=args.output)
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
