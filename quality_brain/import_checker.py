"""导入真实性检查器 — 检测 AI 幻觉 import。

AI 代码产屎的第一大来源：import 了不存在的包、废弃的 API、未声明的依赖。
"""

import ast
import os
import re
from pathlib import Path
from typing import Optional

from .core import Violation, Severity, Blocker, High, Medium, Low


# Python 标准库（3.10+）
STDLIB = {
    'abc', 'aifc', 'argparse', 'array', 'ast', 'asynchat', 'asyncio', 'asyncore',
    'atexit', 'audioop', 'base64', 'bdb', 'binascii', 'binhex', 'bisect', 'builtins',
    'bz2', 'calendar', 'cgi', 'cgitb', 'chunk', 'cmath', 'cmd', 'code', 'codecs',
    'codeop', 'collections', 'colorsys', 'compileall', 'concurrent', 'configparser',
    'contextlib', 'contextvars', 'copy', 'copyreg', 'cProfile', 'crypt', 'csv',
    'ctypes', 'curses', 'dataclasses', 'datetime', 'dbm', 'decimal', 'difflib',
    'dis', 'distutils', 'doctest', 'email', 'encodings', 'enum', 'errno', 'faulthandler',
    'fcntl', 'filecmp', 'fileinput', 'fnmatch', 'formatter', 'fractions', 'ftplib',
    'functools', 'gc', 'getopt', 'getpass', 'gettext', 'glob', 'grp', 'gzip',
    'hashlib', 'heapq', 'hmac', 'html', 'http', 'idlelib', 'imaplib', 'imghdr',
    'imp', 'importlib', 'inspect', 'io', 'ipaddress', 'itertools', 'json', 'keyword',
    'lib2to3', 'linecache', 'locale', 'logging', 'lzma', 'mailbox', 'mailcap',
    'marshal', 'math', 'mimetypes', 'mmap', 'modulefinder', 'multiprocessing',
    'netrc', 'nis', 'nntplib', 'numbers', 'operator', 'optparse', 'os', 'ossaudiodev',
    'parser', 'pathlib', 'pdb', 'pickle', 'pickletools', 'pipes', 'pkgutil',
    'platform', 'plistlib', 'poplib', 'posix', 'posixpath', 'pprint', 'profile',
    'pstats', 'pty', 'pwd', 'py_compile', 'pyclbr', 'pydoc', 'queue', 'quopri',
    'random', 're', 'readline', 'reprlib', 'resource', 'rlcompleter', 'runpy',
    'sched', 'secrets', 'select', 'selectors', 'shelve', 'shlex', 'shutil', 'signal',
    'site', 'smtpd', 'smtplib', 'sndhdr', 'socket', 'socketserver', 'sqlite3',
    'ssl', 'stat', 'statistics', 'string', 'stringprep', 'struct', 'subprocess',
    'sunau', 'symtable', 'sys', 'sysconfig', 'syslog', 'tabnanny', 'tarfile',
    'telnetlib', 'tempfile', 'termios', 'test', 'textwrap', 'threading', 'time',
    'timeit', 'tkinter', 'token', 'tokenize', 'trace', 'traceback', 'tracemalloc',
    'tty', 'turtle', 'turtledemo', 'types', 'typing', 'unicodedata', 'unittest',
    'urllib', 'uu', 'uuid', 'venv', 'warnings', 'wave', 'weakref', 'webbrowser',
    'winreg', 'winsound', 'wsgiref', 'xdrlib', 'xml', 'xmlrpc', 'zipapp', 'zipfile',
    'zipimport', 'zlib', '_thread',
}


def _get_top_level(module_name: str) -> str:
    """获取顶层包名。"""
    if not module_name:
        return ""
    return module_name.split('.')[0]


class ImportChecker:
    """导入真实性检查器。"""

    def __init__(self, stdlib: set[str] = None):
        self._stdlib = stdlib or STDLIB

    def parse_dependencies(self, dep_file: str) -> set[str]:
        """解析依赖声明文件，提取所有声明的包名。"""
        declared = set()
        path = Path(dep_file)
        if not path.exists():
            return declared

        content = path.read_text(encoding='utf-8')

        # requirements.txt 格式
        for line in content.split('\n'):
            line = line.strip()
            if line and not line.startswith('#') and not line.startswith('-'):
                # 提取包名（去除版本号）
                pkg = re.split(r'[<>=!~\[\s]', line)[0].strip()
                if pkg:
                    declared.add(pkg.lower())

        # package.json 格式
        if dep_file.endswith('.json'):
            try:
                import json
                data = json.loads(content)
                for section in ['dependencies', 'devDependencies', 'peerDependencies']:
                    if section in data:
                        for pkg in data[section]:
                            declared.add(pkg.lower())
            except Exception:
                pass

        return declared

    def check_file(self, file_path: str, declared_deps: set[str]) -> list[Violation]:
        """检查单个文件的所有 import。"""
        violations = []
        path = Path(file_path)
        if not path.exists() or path.suffix != '.py':
            return violations

        try:
            source = path.read_text(encoding='utf-8')
            tree = ast.parse(source)
        except (SyntaxError, UnicodeDecodeError):
            return violations

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    v = self._check_import(
                        alias.name, source, file_path, node.lineno, declared_deps, tree)
                    if v:
                        violations.append(v)

            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    # 跳过相对导入
                    if node.level > 0:
                        continue
                    v = self._check_import(
                        node.module, source, file_path, node.lineno, declared_deps, tree)
                    if v:
                        violations.append(v)

        return violations

    def _check_import(self, module_name: str, source: str, file_path: str,
                      lineno: int, declared_deps: set[str], tree: ast.AST) -> Optional[Violation]:
        """检查单个 import 语句。"""
        top_level = _get_top_level(module_name).lower()

        # 标准库
        if top_level in self._stdlib:
            return None

        # 本地模块（检查是否存在对应的 .py 文件）
        local_path = Path(file_path).parent / f"{module_name.replace('.', '/')}.py"
        local_init = Path(file_path).parent / module_name.replace('.', '/') / '__init__.py'
        if local_path.exists() or local_init.exists():
            return None

        # 在当前项目 src 目录中查找
        # (暂时跳过，需要项目上下文)

        # 检查是否在依赖声明中
        if top_level in declared_deps:
            return None

        # 检查是否是当前项目的内部模块
        if module_name.startswith('loop_core') or module_name.startswith('quality_brain'):
            return None

        # ── 未声明的 import → BLOCKER ──
        # 额外检查：是否在 try/except ImportError 中（AI 幻觉兜底模式）
        is_guarded = self._is_in_try_except_import(node=None, tree=tree, lineno=lineno)

        severity = Severity.HIGH if is_guarded else Severity.BLOCKER
        msg = f"import '{module_name}' 未在依赖中声明"
        if is_guarded:
            msg += " (被 try/except ImportError 包裹 — AI 幻觉兜底)"

        lines = source.split('\n')
        snippet = lines[lineno - 1].strip() if 0 <= lineno - 1 < len(lines) else ""

        return Violation(
            rule_id="IMPORT-UNDECLARED",
            severity=severity,
            message=msg,
            file_path=file_path,
            line_number=lineno,
            code_snippet=snippet,
            remediation=f"在依赖声明文件中添加 '{top_level}' 或确认该包真实存在后安装"
        )

    def _is_in_try_except_import(self, node, tree: ast.AST, lineno: int) -> bool:
        """检查 import 是否在 try/except ImportError 块中。"""
        for ancestor in ast.walk(tree):
            if isinstance(ancestor, ast.Try):
                if hasattr(ancestor, 'end_lineno') and ancestor.end_lineno:
                    if ancestor.lineno <= lineno <= ancestor.end_lineno:
                        for handler in ancestor.handlers:
                            if isinstance(handler.type, ast.Name) and handler.type.id == 'ImportError':
                                return True
        return False

    def check_directory(self, root_dir: str, dep_file: str) -> list[Violation]:
        """检查整个目录。"""
        declared = self.parse_dependencies(dep_file)
        violations = []
        for dirpath, _, filenames in os.walk(root_dir):
            if any(skip in dirpath for skip in ['__pycache__', '.venv', 'venv', 'node_modules', '.git']):
                continue
            for fname in filenames:
                if fname.endswith('.py'):
                    violations.extend(
                        self.check_file(os.path.join(dirpath, fname), declared))
        return violations


def check_imports(source_root: str, dependency_file: str) -> list[Violation]:
    """便捷函数：检查整个项目。"""
    checker = ImportChecker()
    return checker.check_directory(source_root, dependency_file)
