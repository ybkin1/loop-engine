"""T-0100 (F-06): 安全扫描误报白名单。

- AC-05a: 规则表自指（扫描器自身文件）不再误报。
- AC-05b: 测试夹具（tests/ 下）与 seeded_defects 故意缺陷样本不再误报。
- AC-05c: 文档示例（docs/、agents/references/）不再误报。
- AC-05d: SafeLoader 子类 Loader 的 yaml.load（如 UniqueKeyLoader）不再误报。
- AC-05e: 白名单只豁免已验证类别 —— 真实代码路径（eval/yaml.load 无安全
  Loader/os.system）照常报告；跳过清单（skipped_files）透明可见。
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCAN_SCRIPT = PROJECT_ROOT / "agents" / "security-engineer" / "scripts" / "run_security_scan.py"


def _load_scan_module():
    spec = importlib.util.spec_from_file_location("run_security_scan_t0100f6", SCAN_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


scan = _load_scan_module()


@pytest.fixture
def fp_project(tmp_path: Path) -> Path:
    """误报样例项目：每类白名单各一个文件 + 一个真实代码文件。"""
    root = tmp_path / "project"

    # 1) 规则表自指 —— 扫描器自身文件的模式定义行
    # T-0117：已删工具路径（scripts/security_scan.py）从 SCANNER_SELF_FILES 清除，
    # fixture 改用现存白名单文件（run_security_scan.py）保持豁免语义。
    p = root / "agents" / "security-engineer" / "scripts" / "run_security_scan.py"
    p.parent.mkdir(parents=True)
    p.write_text(
        'SECURITY_ANTI_PATTERNS = [\n'
        "    (r'os\\.system\\s*\\(', \"P1\", \"Unsafe os.system() call\"),\n"
        "    (r'eval\\s*\\(', \"P0\", \"Dangerous eval() call\"),\n"
        "    (r'exec\\s*\\(', \"P0\", \"Dangerous exec() call\"),\n"
        ']\n',
        encoding="utf-8",
    )

    # 2) 测试夹具 + seeded_defects
    t = root / "tests" / "seeded_defects" / "sample_code"
    t.mkdir(parents=True)
    (t / "user_service.py").write_text(
        'password = "supersecret123"\n'
        'os.system("echo seeded")\n'
        'result = eval(user_input)\n',
        encoding="utf-8",
    )
    (root / "tests" / "test_fixture_case.py").write_text(
        'api_key = "abcdef1234567890"\n'
        'os.system("echo test fixture")\n',
        encoding="utf-8",
    )

    # 3) 文档示例（docs/ + agents/references/）
    d = root / "docs"
    d.mkdir(parents=True)
    (d / "example.md").write_text(
        '示例：`password = "changeme"` 只是文档占位符。\n'
        '`auth_token = "sk-your-token-here"` 亦为示例。\n',
        encoding="utf-8",
    )
    ref = root / "agents" / "references"
    ref.mkdir(parents=True)
    (ref / "role-capability-profiles.md").write_text(
        '```\nconst password = "changeme"\n```\n',
        encoding="utf-8",
    )

    # 4) SafeLoader 子类 yaml.load（同文件类定义）
    g = root / "tools"
    g.mkdir(parents=True)
    (g / "governor_lib.py").write_text(
        "import yaml\n"
        "class UniqueKeyLoader(yaml.SafeLoader):\n"
        "    pass\n"
        "def load(path):\n"
        "    return yaml.load(path.read_text(encoding='utf-8'), Loader=UniqueKeyLoader)\n",
        encoding="utf-8",
    )

    # 5) 真实代码路径（必须照常报告）
    s = root / "src"
    s.mkdir(parents=True)
    (s / "app.py").write_text(
        'import yaml\n'
        'secret = "AKIAIOSFODNN7EXAMPLE1234"\n'  # 排除模式 example → 不报
        'def run(cmd):\n'
        '    os.system(cmd)          # 真实 os.system\n'
        '    eval(user_input)        # 真实 eval\n'
        'def bad(path):\n'
        '    return yaml.load(path)  # 无安全 Loader → 真实 yaml.load\n',
        encoding="utf-8",
    )
    return root


class TestInjectionWhitelist:
    def test_scanner_self_rules_not_reported(self, fp_project: Path):
        result = scan.run_injection_scan(fp_project)
        hits = [f for f in result["high_findings"]
                if "run_security_scan.py" in f["file"]]
        assert hits == [], "扫描器自身规则表不得误报"
        assert any("scanner_self" in s for s in result["skipped_files"])

    def test_test_fixtures_and_seeded_defects_not_reported(self, fp_project: Path):
        result = scan.run_injection_scan(fp_project)
        hits = [f for f in result["high_findings"]
                if "/tests/" in f["file"].replace("\\", "/") or "seeded_defects" in f["file"]]
        assert hits == [], f"测试夹具/seeded_defects 不得误报: {hits}"

    def test_safe_loader_subclass_not_reported(self, fp_project: Path):
        result = scan.run_injection_scan(fp_project)
        hits = [f for f in result["high_findings"]
                if f["rule"] == "yaml.load() unsafe" and "governor_lib.py" in f["file"]]
        assert hits == [], "SafeLoader 子类 Loader 的 yaml.load 不得误报"

    def test_real_code_paths_still_reported(self, fp_project: Path):
        """AC-07：白名单不豁免真实代码路径。"""
        result = scan.run_injection_scan(fp_project)
        src_hits = [f for f in result["high_findings"] if "app.py" in f["file"]]
        rules = {f["rule"] for f in src_hits}
        assert "os.system()" in rules, "真实 os.system 必须报告"
        assert "eval()" in rules, "真实 eval 必须报告"
        assert "yaml.load() unsafe" in rules, "无安全 Loader 的 yaml.load 必须报告"
        assert result["status"] == "blocked", "真实高危必须维持 blocked"

    def test_skipped_files_transparent(self, fp_project: Path):
        result = scan.run_injection_scan(fp_project)
        assert result["skipped_files"], "跳过清单必须透明返回"
        joined = " ".join(result["skipped_files"])
        assert "run_security_scan.py" in joined
        assert "tests/" in joined


class TestInjectionPrecision:
    """F-06 精度修正：SQL/HTML 规则的字符串字面量误报清零，真实 SQL 仍命中。"""

    def test_ui_label_update_not_reported(self, fp_project: Path):
        """tools/loop_onboard.py:147-148 现场：`f"[loop-update] ✅ Updated ..."`
        是 UI 标签不是 SQL —— 修复前 \bUPDATE\b 误报，现清零。"""
        p = fp_project / "src" / "onboard.py"
        p.write_text(
            'print(f"[loop-update] ✅ Updated {updated} agent roles")\n'
            'print(f"[loop-update] ✅ Agents synced from source")\n',
            encoding="utf-8",
        )
        result = scan.run_injection_scan(fp_project)
        hits = [f for f in result["high_findings"]
                if "onboard.py" in f["file"] and "SQL" in f["rule"]]
        assert hits == [], f"UI 标签不得误报 SQL: {hits}"

    def test_real_sql_fstring_still_reported(self, fp_project: Path):
        """真实 SQL f-string 拼接仍命中（白名单/精度修正不掩盖真实注入面）。"""
        p = fp_project / "src" / "db.py"
        p.write_text(
            'query = f"SELECT * FROM users WHERE name=\'{kw}\'"\n'
            'db.execute(f"UPDATE users SET name=\'{kw}\' WHERE id=1")\n',
            encoding="utf-8",
        )
        result = scan.run_injection_scan(fp_project)
        hits = [f for f in result["high_findings"]
                if "db.py" in f["file"] and "SQL" in f["rule"]]
        rules = {f["rule"] for f in hits}
        assert "SQL concatenation (f-string)" in rules
        assert "raw SQL execute" in rules
        assert result["status"] == "blocked", "真实 SQL 注入面必须维持 blocked"

    def test_html_keyword_in_string_literal_not_reported(self, fp_project: Path):
        """loop_core/role_capability.py:134 现场：seeded defect 描述文本
        `"description": "innerHTML XSS"` 不再触发 MEDIUM unsafe HTML binding。"""
        p = fp_project / "src" / "capabilities.py"
        p.write_text(
            '{"id": "SD-006", "type": "xss_unencoded", "description": "innerHTML XSS"},\n',
            encoding="utf-8",
        )
        result = scan.run_injection_scan(fp_project)
        hits = [f for f in result["medium_findings"]
                if "capabilities.py" in f["file"]
                and f["rule"] == "unsafe HTML binding"]
        assert hits == [], f"字符串字面量内的 HTML 关键词不得误报: {hits}"

    def test_real_innerhtml_assignment_still_reported(self, fp_project: Path):
        p = fp_project / "src" / "app.js"
        p.write_text('el.innerHTML = userInput;\n', encoding="utf-8")
        result = scan.run_injection_scan(fp_project)
        rules = {f["rule"] for f in result["medium_findings"]
                 if "app.js" in f["file"]}
        assert "unsafe HTML binding" in rules, "真实 innerHTML 赋值必须报告"


class TestSplitLiteralSqlDetection:
    """T-0100 P2-1（独立审查条件修复）：split-literal SQL 拼接恢复 HIGH 检出。

    审查报告 3.3：`"SELECT " + cols + " FROM " + tbl + " WHERE id=" + uid`
    旧 `+` 规则（HIGH 阻断级）可检出，新 `_SQL_STMT` 语句上下文规则漏检。
    追加"字面量起始即 SQL 关键词 + 拼接/格式化运算符"分支（审查者已验证
    正则，零误报于 UI 标签）；该形态必须恢复 HIGH 阻断级。
    """

    def test_split_literal_sql_concatenation_high(self, fp_project: Path):
        """审查现场形态 + 单字面量完整语句拼接 → HIGH。"""
        p = fp_project / "src" / "legacy_db.py"
        p.write_text(
            'query = "SELECT " + cols + " FROM " + tbl + " WHERE id=" + uid\n'
            'full = "SELECT * FROM users WHERE name=" + name\n',
            encoding="utf-8",
        )
        result = scan.run_injection_scan(fp_project)
        hits = [f for f in result["high_findings"]
                if "legacy_db.py" in f["file"] and "SQL" in f["rule"]]
        rules = {f["rule"] for f in hits}
        assert "SQL concatenation (split literal)" in rules, \
            f"split-literal SQL 拼接必须 HIGH 检出: {rules}"
        assert result["status"] == "blocked", "split-literal SQL 拼接必须维持 blocked"

    def test_split_literal_sql_update_delete_drop_insert_variants(self, fp_project: Path):
        """UPDATE/DELETE/DROP/INSERT 变体 + % 格式化 → 全部 HIGH 检出。"""
        p = fp_project / "src" / "legacy_db2.py"
        p.write_text(
            'q1 = "UPDATE " + tbl + " SET x=1" + " WHERE id=" + uid\n'
            'q2 = "DELETE FROM " + tbl + " WHERE id=" + uid\n'
            'q3 = "DROP TABLE " + tname\n'
            'q4 = "INSERT INTO " + tbl + " VALUES (" + vals + ")"\n'
            'q5 = "SELECT %s FROM users" % (uid,)\n',
            encoding="utf-8",
        )
        result = scan.run_injection_scan(fp_project)
        hits = [f for f in result["high_findings"]
                if "legacy_db2.py" in f["file"]
                and f["rule"] == "SQL concatenation (split literal)"]
        assert len(hits) == 5, \
            f"SELECT/UPDATE/DELETE/DROP/INSERT/% 变体应全部 HIGH 检出: {hits}"
        assert result["status"] == "blocked"

    def test_ui_label_select_string_not_reported(self, fp_project: Path):
        """UI 标签文本（"SELECT color" 类，无拼接/格式化运算符）不得误报。"""
        p = fp_project / "src" / "labels.py"
        p.write_text(
            'print("SELECT color")\n'
            'label = "SELECT color from palette"\n'
            'print("UPDATE profile")\n'
            'print("DELETE entry")\n'
            'print("DROP menu")\n',
            encoding="utf-8",
        )
        result = scan.run_injection_scan(fp_project)
        hits = [f for f in result["high_findings"] + result["medium_findings"]
                if "labels.py" in f["file"]]
        assert hits == [], f"UI 标签文本不得误报 SQL/HTML: {hits}"


class TestBracketAccessHtmlSink:
    """T-0100 P2-2（独立审查条件修复）：bracket-access HTML sink 恢复 MEDIUM 检出。

    审查报告 3.3：`obj["innerHTML"] = userInput` 旧 MEDIUM 规则可检出，
    新 `(?<!["'])…(?!["'])` lookaround 将其排除。追加分支仅命中"赋值"形态
    （方括号闭合后紧跟等号）—— 只读索引访问与描述文本不误报。
    """

    def test_bracket_access_html_sinks_medium(self, fp_project: Path):
        """三种关键词的 bracket-access 赋值 → MEDIUM unsafe HTML binding。"""
        p = fp_project / "src" / "view.js"
        p.write_text(
            'obj["innerHTML"] = userInput;\n'
            "el['outerHTML'] = userHtml;\n"
            'target["insertAdjacentHTML"] = html;\n',
            encoding="utf-8",
        )
        result = scan.run_injection_scan(fp_project)
        hits = [f for f in result["medium_findings"]
                if "view.js" in f["file"] and f["rule"] == "unsafe HTML binding"]
        assert len(hits) == 3, \
            f"bracket-access HTML sink 三种关键词都应 MEDIUM 检出: {hits}"

    def test_read_only_bracket_access_not_reported(self, fp_project: Path):
        """只读索引访问（x = obj["innerHTML"] 读取而非赋值）不得误报。"""
        p = fp_project / "src" / "readonly.js"
        p.write_text(
            'x = obj["innerHTML"];\n'
            'const y = el["outerHTML"];\n'
            'return target["insertAdjacentHTML"];\n',
            encoding="utf-8",
        )
        result = scan.run_injection_scan(fp_project)
        hits = [f for f in result["medium_findings"]
                if "readonly.js" in f["file"]]
        assert hits == [], f"只读索引访问不得误报: {hits}"


class TestSecretWhitelist:
    def test_fixture_secret_not_reported(self, fp_project: Path):
        result = scan.run_secret_scan(fp_project)
        hits = [f for f in result["findings"]
                if "/tests/" in f["file"].replace("\\", "/") or "seeded_defects" in f["file"]]
        assert hits == [], f"测试夹具密钥不得误报: {hits}"

    def test_docs_and_references_not_reported(self, fp_project: Path):
        result = scan.run_secret_scan(fp_project)
        hits = [f for f in result["findings"]
                if f["file"].startswith("docs") or "references" in f["file"]]
        assert hits == [], f"文档示例不得误报: {hits}"
        assert any("docs" in s or "文档示例" in s for s in result["skipped_files"])

    def test_placeholder_secret_on_real_path_not_reported(self, fp_project: Path):
        """占位符（{password} / changeme）排除 —— 修复前
        scripts/certification_runner.py:686 `pwd='{password}'` 类误报清零。"""
        content = """CODE_SNIPPET = "query = f\\"SELECT * FROM users WHERE pwd='{password}'\\""\n"""
        (fp_project / "src" / "templates.py").write_text(content, encoding="utf-8")
        result = scan.run_secret_scan(fp_project)
        hits = [f for f in result["findings"] if "templates.py" in f["file"]]
        assert hits == [], f"占位符模板不得误报: {hits}"

    def test_real_secret_on_real_path_still_reported(self, fp_project: Path):
        (fp_project / "src" / "creds.py").write_text(
            'api_key = "AKIAQWERTYUIOPASDFGHJKLK"\n',
            encoding="utf-8",
        )
        result = scan.run_secret_scan(fp_project)
        hits = [f for f in result["findings"] if "creds.py" in f["file"]]
        assert hits, "真实硬编码密钥必须报告"
