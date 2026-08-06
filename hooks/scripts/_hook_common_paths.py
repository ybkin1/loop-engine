#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
_hook_common_paths.py — Bash 命令目标路径提取（从 hook_common.py 拆分，T-0125）。

承载 hook_common._extract_paths_from_bash_command 的权威实现（高置信度
写入/修改目标模式，8 类）；hook_common.py 中保留同名委托 stub 以维持
公开符号面与行为零变更。注意：本模块是 *v1* 行为（8 类写入模式），与
_hook_path.py 中简化版（扩展名匹配）语义不同，互不替代。
"""

import re
import shlex


def _extract_paths_from_bash_command(command: str):
    """从 Bash 命令字符串中提取可能的目标文件路径列表。

    只识别高置信度的写入/修改目标模式：
    - 输出重定向: > file, >> file, 2> file, &> file
    - 创建/修改命令: touch file..., mkdir dir..., cp ... dst, mv ... dst
    - 追加写入: tee file, tee -a file, cat > file
    - 不能解析时返回空列表（不臆断）。
    """
    if not command or not isinstance(command, str):
        return []

    paths = []

    # 1. 重定向运算符：cmd > file, cmd >> file, cmd 2> file, cmd &> file
    # 匹配模式：(>>|>|2>|&>|1>) 后跟可选空格，再跟路径
    redirect_pattern = re.compile(
        r'(?:^|\s|[;|&])(?:>>|[12]?>|&>)\s*([^\s;|&<]+)'
    )
    for m in redirect_pattern.finditer(command):
        p = m.group(1).strip('"\'')
        if p and not p.startswith('/dev/'):
            paths.append(p)

    # 2. touch 命令: touch file1 file2 ...
    touch_pattern = re.compile(
        r'(?:^|\s|[;|&])touch\s+(.*?)(?:$|[;|&]{2}|[;|&](?!>))'
    )
    for m in touch_pattern.finditer(command):
        rest = m.group(1).strip()
        if rest:
            # 拆分参数，过滤掉选项（以 - 开头）
            try:
                tokens = shlex.split(rest)
            except ValueError:
                tokens = rest.split()
            for tok in tokens:
                if not tok.startswith('-') and not tok.startswith('/dev/'):
                    paths.append(tok.strip('"\''))

    # 3. mkdir 命令: mkdir dir1 dir2 ...
    mkdir_pattern = re.compile(
        r'(?:^|\s|[;|&])mkdir\s+(?:-p\s+)?(.*?)(?:$|[;|&]{2}|[;|&](?!>))'
    )
    for m in mkdir_pattern.finditer(command):
        rest = m.group(1).strip()
        if rest:
            try:
                tokens = shlex.split(rest)
            except ValueError:
                tokens = rest.split()
            for tok in tokens:
                if not tok.startswith('-') and not tok.startswith('/dev/'):
                    paths.append(tok.strip('"\''))

    # 4. cp 命令: cp src... dst (最后一个参数是目标)
    cp_pattern = re.compile(
        r'(?:^|\s|[;|&])cp\s+(?:-[a-zA-Z]+\s+)?(.*?)(?:$|[;|&]{2}|[;|&](?!>))'
    )
    for m in cp_pattern.finditer(command):
        rest = m.group(1).strip()
        if rest:
            try:
                tokens = shlex.split(rest)
            except ValueError:
                tokens = rest.split()
            # 过滤选项，最后一个是目标
            args = [t for t in tokens if not t.startswith('-')]
            if len(args) >= 2:
                dst = args[-1].strip('"\'')
                if not dst.startswith('/dev/'):
                    paths.append(dst)

    # 5. mv 命令: mv src... dst (最后一个参数是目标)
    mv_pattern = re.compile(
        r'(?:^|\s|[;|&])mv\s+(?:-[a-zA-Z]+\s+)?(.*?)(?:$|[;|&]{2}|[;|&](?!>))'
    )
    for m in mv_pattern.finditer(command):
        rest = m.group(1).strip()
        if rest:
            try:
                tokens = shlex.split(rest)
            except ValueError:
                tokens = rest.split()
            args = [t for t in tokens if not t.startswith('-')]
            if len(args) >= 2:
                dst = args[-1].strip('"\'')
                if not dst.startswith('/dev/'):
                    paths.append(dst)

    # 6. tee 命令: tee file, tee -a file
    tee_pattern = re.compile(
        r'(?:^|\s|[;|&])tee\s+(?:-a\s+)?([^\s;|&<]+)'
    )
    for m in tee_pattern.finditer(command):
        p = m.group(1).strip('"\'')
        if p and not p.startswith('-') and not p.startswith('/dev/'):
            paths.append(p)

    # 7. cat > file (重定向写入)
    cat_redirect_pattern = re.compile(
        r'(?:^|\s|[;|&])cat\s+.*?>\s*([^\s;|&]+)'
    )
    for m in cat_redirect_pattern.finditer(command):
        p = m.group(1).strip('"\'')
        if p and not p.startswith('/dev/'):
            paths.append(p)

    # 8. 写入类: echo "..." > file, printf "..." > file
    write_redirect_pattern = re.compile(
        r'(?:^|\s|[;|&])(?:echo|printf)\s+.*?>>?\s*([^\s;|&]+)'
    )
    for m in write_redirect_pattern.finditer(command):
        p = m.group(1).strip('"\'')
        if p and not p.startswith('/dev/'):
            paths.append(p)

    return paths
