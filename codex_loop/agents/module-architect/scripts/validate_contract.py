"""
validate_contract.py — 接口契约验证工具（模块架构师使用）。

确定性代码，不依赖 LLM。验证 interface-contract.json 的 schema 完整性，
并可对比代码实际导出与契约声明的一致性。

用法：
    python validate_contract.py --contract <file> [--check-schema-only] [--check-actual]
    python validate_contract.py --contract contract.json
    python validate_contract.py --contract contract.json --check-schema-only
    python validate_contract.py --contract contract.json --check-actual --project-root . --module-path src/mymodule

输出：JSON 到 stdout（overall / missing_exports / extra_exports / mismatches / schema_issues）
退出码：0 = 一致 / 通过；2 = 不一致 / schema 不合法。

interface-contract.json 顶层结构（12 个必填字段）：
    module          — 模块名称
    version         — 语义化版本号
    description     — 模块职责描述
    exports[]       — 导出接口列表
      name          — 函数名
      description   — 函数用途说明
      parameters[]  — 参数列表
      returns       — 返回值类型
      errors[]      — 错误类型列表
      idempotency   — 幂等性声明
      side_effects  — 副作用列表
      dependencies  — 依赖列表，格式 "函数名 (模块名)"
"""

import argparse
import ast
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

sys.dont_write_bytecode = True

EXIT_PASS = 0
EXIT_BLOCK = 2

# ──────────────────────────────────────────────
# 1. Schema 验证
# ──────────────────────────────────────────────

# 12 个必填字段
REQUIRED_TOP_FIELDS = ["module", "version", "description", "exports"]

REQUIRED_EXPORT_FIELDS = [
    "name",           # 1
    "description",    # 2
    "parameters",     # 3
    "returns",        # 4
    "errors",         # 5
    "idempotency",    # 6
    "side_effects",   # 7
    "dependencies",   # 8
]

# 禁止出现在 type 字段中的模糊类型
FORBIDDEN_TYPES = {"any", "unknown", "object", "Function"}

# 幂等性允许的值
IDEMPOTENCY_PATTERN = re.compile(r"^(是|否|[条件].+)$")

# 依赖格式：应遵循 "函数名 (模块名)" 格式
DEPENDENCY_PATTERN = re.compile(r"^.+\(.+\)$")


def _check_type_string(type_str: str, path: str) -> List[Dict[str, str]]:
    """检查类型字符串是否使用禁止的模糊类型。"""
    issues = []
    # 直接匹配
    if type_str.strip().lower() in FORBIDDEN_TYPES:
        issues.append({
            "field": path,
            "issue": f"禁用类型 '{type_str}'",
            "severity": "BLOCKED",
        })
    # 检查 Record<string, any> 模式
    if re.search(r"Record\s*<\s*string\s*,\s*any\s*>", type_str, re.IGNORECASE):
        issues.append({
            "field": path,
            "issue": f"模糊类型模式 'Record<string, any>' 在 '{type_str}'",
            "severity": "BLOCKED",
        })
    # 检查 object 作为类型引用的一部分
    if re.search(r"\bobject\b", type_str) and "object" not in type_str.split("|"):
        # 允许 "创单object" 这类中文，但纯 object 不行
        if type_str.strip().lower() == "object":
            issues.append({
                "field": path,
                "issue": "禁止类型 'object'",
                "severity": "BLOCKED",
            })
    return issues


def validate_contract_schema(contract: Dict[str, Any]) -> List[Dict[str, str]]:
    """验证 JSON schema 完整性，返回问题列表。"""
    issues: List[Dict[str, str]] = []

    if not isinstance(contract, dict):
        return [{"field": "$", "issue": "contract 必须是 JSON 对象", "severity": "BLOCKED"}]

    # 顶层必填字段
    for field in REQUIRED_TOP_FIELDS:
        if field not in contract:
            issues.append({
                "field": f"$.{field}",
                "issue": f"缺少顶层必填字段 '{field}'",
                "severity": "BLOCKED",
            })

    exports = contract.get("exports", [])
    if not isinstance(exports, list):
        issues.append({
            "field": "$.exports",
            "issue": "exports 必须是数组",
            "severity": "BLOCKED",
        })
        return issues

    if len(exports) == 0:
        issues.append({
            "field": "$.exports",
            "issue": "exports 不能为空",
            "severity": "WARNING",
        })

    # 逐 export 检查
    for i, exp in enumerate(exports):
        if not isinstance(exp, dict):
            issues.append({
                "field": f"$.exports[{i}]",
                "issue": "每个 export 必须是 JSON 对象",
                "severity": "BLOCKED",
            })
            continue

        # 8 个 export 必填字段
        for field in REQUIRED_EXPORT_FIELDS:
            if field not in exp:
                issues.append({
                    "field": f"$.exports[{i}].{field}",
                    "issue": f"export '{exp.get('name', f'#{i}')}' 缺少必填字段 '{field}'",
                    "severity": "BLOCKED",
                })

        exp.get("name", f"#{i}")

        # 检查 returns 类型
        returns = exp.get("returns", {})
        if isinstance(returns, dict):
            ret_type = returns.get("type", "")
            if ret_type:
                issues.extend(_check_type_string(str(ret_type), f"$.exports[{i}].returns.type"))
        elif isinstance(returns, str):
            issues.extend(_check_type_string(returns, f"$.exports[{i}].returns"))

        # 检查 parameters 中的类型
        params = exp.get("parameters", [])
        if isinstance(params, list):
            for pi, param in enumerate(params):
                if isinstance(param, dict):
                    ptype = param.get("type", "")
                    if ptype:
                        issues.extend(_check_type_string(
                            str(ptype), f"$.exports[{i}].parameters[{pi}].type"
                        ))

        # 检查 errors 中的类型
        errors = exp.get("errors", [])
        if isinstance(errors, list):
            for ei, err in enumerate(errors):
                if isinstance(err, dict):
                    etype = err.get("type", "")
                    if etype and etype.lower() in ("error",):
                        issues.append({
                            "field": f"$.exports[{i}].errors[{ei}].type",
                            "issue": "错误类型不能为泛型 'Error'，必须具体（如 ValidationError）",
                            "severity": "BLOCKED",
                        })

        # 检查 idempotency
        ide = exp.get("idempotency", "")
        if ide and not IDEMPOTENCY_PATTERN.match(str(ide)):
            issues.append({
                "field": f"$.exports[{i}].idempotency",
                "issue": f"幂等性声明格式不正确: '{ide}'（应为 '是'/'否'/'条件+说明'）",
                "severity": "WARNING",
            })

        # 检查 side_effects
        se = exp.get("side_effects", None)
        if se is None:
            issues.append({
                "field": f"$.exports[{i}].side_effects",
                "issue": "side_effects 必须声明（无副作用时标注 []）",
                "severity": "BLOCKED",
            })

        # 检查 dependencies 格式
        deps = exp.get("dependencies", [])
        if isinstance(deps, list):
            for di, dep in enumerate(deps):
                if isinstance(dep, str):
                    if not DEPENDENCY_PATTERN.match(dep.strip()):
                        issues.append({
                            "field": f"$.exports[{i}].dependencies[{di}]",
                            "issue": f"依赖格式不正确: '{dep}'，应为 '函数名 (模块名)'",
                            "severity": "WARNING",
                        })
                elif isinstance(dep, dict):
                    dep_name = dep.get("function", dep.get("name", ""))
                    dep_mod = dep.get("module", "")
                    if dep_name and dep_mod:
                        # 字典格式也符合规范
                        pass
                    else:
                        issues.append({
                            "field": f"$.exports[{i}].dependencies[{di}]",
                            "issue": "依赖对象缺少 function 或 module 字段",
                            "severity": "WARNING",
                        })

    # 检查 data_structures（如果存在）
    ds_list = contract.get("data_structures", [])
    if isinstance(ds_list, list):
        for di, ds in enumerate(ds_list):
            if not isinstance(ds, dict):
                continue
            for field in ["name", "description", "fields"]:
                if field not in ds:
                    issues.append({
                        "field": f"$.data_structures[{di}].{field}",
                        "issue": f"数据结构缺少必填字段 '{field}'",
                        "severity": "BLOCKED",
                    })
            fields = ds.get("fields", [])
            if isinstance(fields, list):
                for fi, fld in enumerate(fields):
                    if isinstance(fld, dict):
                        for ff in ["name", "type", "mutable", "constraints"]:
                            if ff not in fld:
                                issues.append({
                                    "field": f"$.data_structures[{di}].fields[{fi}].{ff}",
                                    "issue": f"字段缺少必填属性 '{ff}'",
                                    "severity": "BLOCKED",
                                })
                        ftype = fld.get("type", "")
                        if ftype:
                            issues.extend(_check_type_string(
                                str(ftype), f"$.data_structures[{di}].fields[{fi}].type"
                            ))

    return issues


# ──────────────────────────────────────────────
# 2. 代码实际导出解析
# ──────────────────────────────────────────────

def parse_python_exports(filepath: Path) -> Dict[str, Dict[str, Any]]:
    """
    解析 Python 模块的公共导出。

    提取顶级函数定义和 __all__ 声明。
    返回 {name: {params, has_return, has_decorator}}。
    """
    exports: Dict[str, Dict[str, Any]] = {}
    try:
        source = filepath.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(source, filename=str(filepath))
    except (SyntaxError, Exception):
        return exports

    # 查找 __all__
    all_names: Optional[Set[str]] = None
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__all__":
                    if isinstance(node.value, (ast.List, ast.Tuple)):
                        all_names = set()
                        for elt in node.value.elts:
                            if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                all_names.add(elt.value)

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.FunctionDef):
            # 跳过私有函数
            if node.name.startswith("_"):
                continue
            if all_names is not None and node.name not in all_names:
                continue

            params = []
            for arg in node.args.args:
                p = {"name": arg.arg}
                if arg.annotation:
                    p["type"] = ast.unparse(arg.annotation) if hasattr(ast, "unparse") else str(arg.annotation)
                params.append(p)

            has_return = any(isinstance(n, ast.Return) and n.value is not None for n in ast.walk(node))

            exports[node.name] = {
                "name": node.name,
                "parameters": params,
                "has_return": has_return,
            }

        elif isinstance(node, ast.ClassDef):
            if node.name.startswith("_"):
                continue
            if all_names is not None and node.name not in all_names:
                continue
            exports[node.name] = {
                "name": node.name,
                "parameters": [],
                "has_return": False,
                "is_class": True,
            }

    return exports


def parse_typescript_exports(filepath: Path) -> Dict[str, Dict[str, Any]]:
    """
    解析 TypeScript 模块的导出声明。

    使用正则匹配 export function / export const / export class / export default。
    返回 {name: {params, has_return}}。
    """
    exports: Dict[str, Dict[str, Any]] = {}
    try:
        source = filepath.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return exports

    # 匹配 export function name(params): returnType
    func_pattern = re.compile(
        r"export\s+(?:async\s+)?function\s+(\w+)\s*\(([^)]*)\)\s*(?::\s*(\S+(?:\s*\|?\s*\S+)*))?\s*\{",
        re.MULTILINE,
    )
    for m in func_pattern.finditer(source):
        name = m.group(1)
        if name.startswith("_"):
            continue
        params_str = m.group(2).strip()
        params = []
        if params_str:
            for p in params_str.split(","):
                p = p.strip()
                if p:
                    parts = p.split(":")
                    params.append({"name": parts[0].strip(), "type": parts[1].strip() if len(parts) > 1 else "any"})
        exports[name] = {"name": name, "parameters": params, "has_return": m.group(3) is not None}

    # 匹配 export const name = (...) => { }
    const_arrow = re.compile(
        r"export\s+const\s+(\w+)\s*=\s*(?:\(([^)]*)\))\s*(?::\s*(\S+(?:\s*\|?\s*\S+)*))?\s*=>",
        re.MULTILINE,
    )
    for m in const_arrow.finditer(source):
        name = m.group(1)
        if name.startswith("_"):
            continue
        exports[name] = {"name": name, "parameters": [], "has_return": True}

    # 匹配 export class name
    class_pattern = re.compile(r"export\s+class\s+(\w+)", re.MULTILINE)
    for m in class_pattern.finditer(source):
        name = m.group(1)
        if name.startswith("_"):
            continue
        exports[name] = {"name": name, "parameters": [], "has_return": False, "is_class": True}

    # 匹配 export { name } / export default
    named_export = re.compile(r"export\s*\{\s*([^}]+)\s*\}", re.MULTILINE)
    for m in named_export.finditer(source):
        names_str = m.group(1)
        for n in names_str.split(","):
            n = n.strip()
            if n and not n.startswith("_"):
                if n not in exports:
                    exports[n] = {"name": n, "parameters": [], "has_return": False}

    return exports


def parse_actual_exports(module_path: Path) -> Dict[str, Dict[str, Any]]:
    """根据文件扩展名选择合适的解析器。"""
    suffix = module_path.suffix.lower()
    if suffix == ".py":
        return parse_python_exports(module_path)
    elif suffix in (".ts", ".tsx", ".js", ".jsx", ".mjs", ".mts"):
        return parse_typescript_exports(module_path)
    else:
        # 如果是目录，尝试查找 __init__.py 或 index.ts
        if module_path.is_dir():
            py_init = module_path / "__init__.py"
            if py_init.exists():
                return parse_python_exports(py_init)
            for idx_name in ("index.ts", "index.tsx", "index.js", "index.jsx"):
                idx_path = module_path / idx_name
                if idx_path.exists():
                    return parse_typescript_exports(idx_path)
        return {}


# ──────────────────────────────────────────────
# 3. 契约与代码对比
# ──────────────────────────────────────────────

def compare_contract_to_actual(
    contract: Dict[str, Any],
    actual_exports: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """对比契约声明与实际导出的一致性。"""
    declared = set()
    for exp in contract.get("exports", []):
        if isinstance(exp, dict):
            name = exp.get("name", "")
            if name:
                declared.add(name)

    actual = set(actual_exports.keys())

    missing_in_code = declared - actual   # 契约声明了但代码没有
    missing_in_contract = actual - declared  # 代码有但契约没声明

    mismatches = []
    for name in declared & actual:
        ce = next((e for e in contract.get("exports", []) if isinstance(e, dict) and e.get("name") == name), None)
        ae = actual_exports.get(name, {})

        if ce:
            ce_params = ce.get("parameters", [])
            ce_pcount = len(ce_params) if isinstance(ce_params, list) else 0
            ae_pcount = len(ae.get("parameters", []))
            if ce_pcount != ae_pcount:
                mismatches.append({
                    "export": name,
                    "field": "parameters",
                    "contract": f"{ce_pcount} 个参数",
                    "actual": f"{ae_pcount} 个参数",
                })

            # 检查契约中的参数是否在实际代码中
            if isinstance(ce_params, list):
                ce_pnames = {p.get("name", "") for p in ce_params if isinstance(p, dict)}
                ae_pnames = {p.get("name", "") for p in ae.get("parameters", [])}
                missing_params = ce_pnames - ae_pnames
                extra_params = ae_pnames - ce_pnames
                if missing_params:
                    mismatches.append({
                        "export": name,
                        "field": "parameters",
                        "contract": f"声明参数: {sorted(ce_pnames)}",
                        "actual": f"缺失参数: {sorted(missing_params)}",
                    })
                if extra_params:
                    mismatches.append({
                        "export": name,
                        "field": "parameters",
                        "contract": f"声明参数: {sorted(ce_pnames)}",
                        "actual": f"额外参数: {sorted(extra_params)}",
                    })

            # 检查 returns
            ce_returns = ce.get("returns", {})
            has_return_declared = bool(ce_returns and (ce_returns.get("type") or (isinstance(ce_returns, str) and ce_returns)))
            has_return_actual = ae.get("has_return", True)
            if has_return_declared != has_return_actual and not ae.get("is_class"):
                mismatches.append({
                    "export": name,
                    "field": "returns",
                    "contract": f"声明返回值={'是' if has_return_declared else '否'}",
                    "actual": f"实际返回值={'是' if has_return_actual else '否'}",
                })

    return {
        "missing_in_code": sorted(missing_in_code),
        "missing_in_contract": sorted(missing_in_contract),
        "mismatches": mismatches,
    }


# ──────────────────────────────────────────────
# 4. CLI
# ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="接口契约验证工具")
    parser.add_argument("--contract", required=True, help="interface-contract.json 文件路径")
    parser.add_argument("--check-schema-only", action="store_true", help="仅检查 schema，不对比代码")
    parser.add_argument("--check-actual", action="store_true", help="对比代码实际导出与契约声明")
    parser.add_argument("--project-root", default=".", help="项目根目录")
    parser.add_argument("--module-path", default=None, help="要检查的模块文件或目录路径")
    args = parser.parse_args()

    contract_path = Path(args.contract)
    if not contract_path.is_file():
        print(json.dumps({"error": f"契约文件不存在: {contract_path}"}, ensure_ascii=False))
        sys.exit(EXIT_BLOCK)

    # 加载契约
    try:
        with open(contract_path, "r", encoding="utf-8") as f:
            contract = json.load(f)
    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"契约文件 JSON 格式错误: {e}", "overall": "BLOCKED"}, ensure_ascii=False))
        sys.exit(EXIT_BLOCK)

    # Schema 验证
    schema_issues = validate_contract_schema(contract)

    # 类型检查结果
    blocked_count = 0
    for issue in schema_issues:
        if issue.get("severity") == "BLOCKED":
            blocked_count += 1
    schema_pass = blocked_count == 0

    # 代码对比（如果请求）
    compare_result = None
    if args.check_actual:
        module_path = Path(args.module_path) if args.module_path else Path(args.project_root)
        if not module_path.exists():
            compare_result = {"error": f"模块路径不存在: {module_path}"}
        else:
            actual_exports = parse_actual_exports(module_path)
            compare_result = compare_contract_to_actual(contract, actual_exports)
            compare_result["actual_exports"] = sorted(actual_exports.keys())

    # 构建输出
    output = {
        "schema": "contract_validation/v1",
        "contract": str(contract_path.resolve()),
        "schema_issues": schema_issues,
        "schema_pass": schema_pass,
    }

    if compare_result:
        output["compare"] = compare_result

    # 判定 overall
    has_comparison_issues = False
    if compare_result and isinstance(compare_result, dict):
        if (compare_result.get("missing_in_code") or
                compare_result.get("missing_in_contract") or
                compare_result.get("mismatches")):
            has_comparison_issues = True

    if not schema_pass or has_comparison_issues:
        output["overall"] = "BLOCKED"
        print(json.dumps(output, ensure_ascii=False, indent=2))
        sys.exit(EXIT_BLOCK)
    else:
        output["overall"] = "PASS"
        print(json.dumps(output, ensure_ascii=False, indent=2))
        sys.exit(EXIT_PASS)


if __name__ == "__main__":
    main()
