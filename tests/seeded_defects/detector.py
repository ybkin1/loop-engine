# -*- coding: utf-8 -*-
"""
detector.py — T-0128 M1 确定性检出规则库。

对 seeded_defects/sample_code 的 6 个种子缺陷（SD-001~006）提供确定性检出规则
（正则 + AST），供 mutation_tester.py scan 子命令调用。规则只读源码、不执行，
输出每缺陷检出结果与证据行号——"规则真能抓住"的机器可复算验证（M1）。

与 defect_registry.json 一一对应：
  SD-001 SQL injection (f-string)      -> detect_sd001
  SD-002 missing input validation      -> detect_sd002
  SD-003 plaintext password storage    -> detect_sd003
  SD-004 division by zero              -> detect_sd004
  SD-005 N+1 query in loop             -> detect_sd005
  SD-006 circular module dependency    -> detect_sd006
"""

from __future__ import annotations

import ast
import re
from typing import Any


# 规则库覆盖的种子缺陷集合（与 defect_registry.json 交叉校验用）
SD_IDS = ("SD-001", "SD-002", "SD-003", "SD-004", "SD-005", "SD-006")


def _first_line(node: ast.AST) -> int:
    return getattr(node, "lineno", -1)


def detect_sd001(source: str, tree: ast.Module) -> tuple[bool, str]:
    """SD-001: f-string 拼接 SQL（常量段含 SQL 关键字且带插值）并传入 execute。

    sample_code 中 f-string 先赋给 query 变量再传入 execute，因此不能只查
    execute 的实参——直接扫描全部 JoinedStr。
    """
    for node in ast.walk(tree):
        if isinstance(node, ast.JoinedStr):
            const_text = "".join(
                seg.value for seg in node.values
                if isinstance(seg, ast.Constant) and isinstance(seg.value, str)
            )
            has_interp = any(not isinstance(seg, ast.Constant) for seg in node.values)
            if has_interp and re.search(r"(SELECT|INSERT|UPDATE|DELETE)\s", const_text, re.I):
                return True, f"interpolated SQL f-string at line {node.lineno}"
    return False, "no interpolated SQL f-string found"


def detect_sd002(source: str, tree: ast.Module) -> tuple[bool, str]:
    """SD-002: create_user 直通 db.execute，无 if/assert 校验。"""
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "create_user":
            body = [n for n in node.body if not isinstance(n, (ast.Expr, ast.Pass))]
            early_validation = any(
                isinstance(stmt, (ast.If, ast.Assert)) for stmt in body
            )
            if not early_validation:
                return True, f"create_user has no input validation at line {node.lineno}"
            return False, "create_user contains validation guards"
    return False, "create_user not found"


def detect_sd003(source: str, tree: ast.Module) -> tuple[bool, str]:
    """SD-003: set_password 直接写库，无 hash 调用（AST 节点级，排除 docstring）。"""
    hash_names = {"hashlib", "bcrypt", "argon2", "sha256", "sha1", "pbkdf2", "hash"}
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "set_password":
            # 只检查可执行节点（Call/Name/Attribute），docstring 属 Constant 被排除
            for child in ast.walk(node):
                if isinstance(child, (ast.Call, ast.Name, ast.Attribute)):
                    name = child.id if isinstance(child, ast.Name) else getattr(child, "attr", None) or ""
                    if name and name.lower() in hash_names:
                        return False, f"set_password uses hashing ({name}) at line {child.lineno}"
            return True, f"set_password stores raw password at line {node.lineno}"
    return False, "set_password not found"


def detect_sd004(source: str, tree: ast.Module) -> tuple[bool, str]:
    """SD-004: get_average_age 中 total/len 且无空列表守卫。"""
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "get_average_age":
            # 空输入守卫：if not <iterable> / if len(<iterable>) == 0
            guarded = False
            for child in ast.walk(node):
                if isinstance(child, ast.If):
                    cond = child.test
                    if (isinstance(cond, ast.UnaryOp) and isinstance(cond.op, ast.Not)
                            and isinstance(cond.operand, ast.Name)):
                        guarded = True
                    if (isinstance(cond, ast.Compare)
                            and isinstance(cond.left, ast.Call)
                            and isinstance(cond.left.func, ast.Name)
                            and cond.left.func.id == "len"):
                        guarded = True
            for child in ast.walk(node):
                if isinstance(child, ast.BinOp) and isinstance(child.op, ast.Div):
                    if isinstance(child.left, ast.Name) and child.left.id == "total":
                        if not guarded:
                            return True, f"unguarded total/len at line {child.lineno}"
                        return False, f"total/len guarded by empty check at line {child.lineno}"
    return False, "no unguarded division found"


def detect_sd005(source: str, tree: ast.Module) -> tuple[bool, str]:
    """SD-005: for 循环体内直接调用 db.execute（N+1 模式）。"""
    for node in ast.walk(tree):
        if isinstance(node, ast.For):
            for child in ast.walk(node):
                if isinstance(child, ast.Call):
                    fn = child.func
                    if isinstance(fn, ast.Attribute) and fn.attr == "execute":
                        return True, f"query inside loop at line {child.lineno}"
    return False, "no loop-contained query found"


def detect_sd006(source: str, tree: ast.Module) -> tuple[bool, str]:
    """SD-006: OrderService 引用 UserService 且 UserService 反向引用（循环依赖）。"""
    class_annotations: dict[str, list[str]] = {}
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            refs = []
            for child in ast.walk(node):
                if isinstance(child, ast.AnnAssign) and isinstance(child.annotation, ast.Name):
                    refs.append(child.annotation.id)
                if isinstance(child, ast.Name) and child.id in ("UserService", "OrderService"):
                    refs.append(child.id)
            class_annotations[node.name] = refs
    order_refs_user = any(
        n == "OrderService" and "UserService" in refs for n, refs in class_annotations.items()
    )
    user_refs_order = any(
        n == "UserService" and "OrderService" in refs for n, refs in class_annotations.items()
    )
    if order_refs_user and user_refs_order:
        return True, "UserService <-> OrderService mutual reference (circular)"
    return False, "no circular class dependency found"


def detect_all(source: str) -> dict[str, dict[str, Any]]:
    """对全部 6 个种子缺陷执行确定性检出。

    返回 {sd_id: {"detected": bool, "evidence": str}}，纯函数、无副作用、
    可复算（同一源码结果恒定）。
    """
    tree = ast.parse(source)
    rules = {
        "SD-001": detect_sd001,
        "SD-002": detect_sd002,
        "SD-003": detect_sd003,
        "SD-004": detect_sd004,
        "SD-005": detect_sd005,
        "SD-006": detect_sd006,
    }
    results: dict[str, dict[str, Any]] = {}
    for sd_id, rule in rules.items():
        detected, evidence = rule(source, tree)
        results[sd_id] = {"detected": bool(detected), "evidence": str(evidence)}
    return results
