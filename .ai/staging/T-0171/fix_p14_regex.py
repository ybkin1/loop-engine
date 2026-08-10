#!/usr/bin/env python3
"""fix_p14_regex.py — 修复 P1-4：中文提取正则补新增高频词"""
from pathlib import Path

SRC = Path(r"C:\Users\Administrator\ZCodeProject\loop-engine\.ai\staging\T-0171\oqa_patterns.ts")

def main() -> int:
    t = SRC.read_text(encoding="utf-8")
    old = "/(登录|校验|验证|保存|加载|创建|删除|更新|查询|搜索|过滤|排序|发送|接收|解析|转换|计算|检查|格式化|渲染|提交|取消|批准|拒绝|导出|导入|合并|拆分|加密|解密)/g"
    new = "/(登录|校验|验证|保存|加载|创建|删除|更新|查询|搜索|查找|获取|添加|移除|写入|读取|认证|登出|权限|过滤|排序|发送|接收|解析|转换|计算|检查|格式化|渲染|提交|取消|批准|拒绝|导出|导入|合并|拆分|加密|解密)/g"
    assert t.count(old) == 1, f"regex anchor={t.count(old)}"
    t = t.replace(old, new)
    SRC.write_text(t, encoding="utf-8")
    print("[fix] P1-4: CN regex synced with CN_EN_MAP")

    # 同步到 lab
    (Path(r"C:\Users\Administrator\.qoder-cn\loop-engine-lab\src\core\oqa_patterns.ts")).write_text(t, encoding="utf-8")
    print("[sync] lab deployed")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
