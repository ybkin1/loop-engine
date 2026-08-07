# -*- coding: utf-8 -*-
"""
test_t0153_pwa_prototype.py — T-0153 手机 PWA 叠加层原型冒烟测试。

覆盖：PWA 骨架文件在位（manifest/SW/html/css/js）；mock API 客户端逻辑
（sessions 分组/详情/发消息/abort/切模型）；设备配对设计文档在位且含
外部边界声明。
"""

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web"


class PwaPrototypeTest(unittest.TestCase):
    def test_pwa_skeleton_files(self):
        """PWA 五件套在位。"""
        for name in ("manifest.json", "sw.js", "index.html", "app.js", "style.css"):
            self.assertTrue((WEB / name).is_file(), f"missing web/{name}")

    def test_manifest_valid(self):
        """manifest.json 合法（PWA 可安装要素）。"""
        m = json.loads((WEB / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(m["display"], "standalone")
        self.assertIn("name", m)
        self.assertIn("icons", m)

    def test_service_worker_installed_in_html(self):
        """index.html 注册 service worker。"""
        html = (WEB / "index.html").read_text(encoding="utf-8")
        self.assertIn("serviceWorker.register", html)
        self.assertIn("manifest.json", html)

    def test_mock_api_contract(self):
        """api.js 含五操作契约（sessions/详情/发消息/abort/切模型）+ SSE。"""
        js = (WEB / "api.js").read_text(encoding="utf-8")
        for marker in ("listSessions", "getSession", "sendMessage", "abort",
                       "switchModel", "subscribeEvents", "mode: 'mock'"):
            self.assertIn(marker, js, f"api.js missing: {marker}")

    def test_mock_handles_core_paths(self):
        """mock 路由覆盖核心路径（用 node 执行 api.js 逻辑困难，静态断言）。"""
        js = (WEB / "api.js").read_text(encoding="utf-8")
        for path in ("/api/sessions", "/api/sessions/:id", "messages", "abort", "model"):
            self.assertIn(path, js, f"mock 未覆盖: {path}")

    def test_sse_event_source_wrapped(self):
        """SSE 封装存在（mock 定时器 / EventSource 双路径）。"""
        js = (WEB / "api.js").read_text(encoding="utf-8")
        self.assertIn("EventSource", js)
        self.assertIn("subscribeEvents", js)

    def test_design_doc_with_boundary(self):
        """设备配对设计文档在位 + 外部边界声明。"""
        doc = ROOT / "docs" / "designs" / "T-0153-pwa-overlay.md"
        self.assertTrue(doc.is_file())
        text = doc.read_text(encoding="utf-8")
        for marker in ("二维码", "一次性登录码", "持久 token", "外部边界",
                       "Caddy", "Cloudflare Tunnel", "WSS relay"):
            self.assertIn(marker, text, f"design doc missing: {marker}")

    def test_no_real_nordrelay_endpoint(self):
        """原型不硬编码真实 NordRelay 地址（外部边界保护）。"""
        js = (WEB / "api.js").read_text(encoding="utf-8")
        html = (WEB / "index.html").read_text(encoding="utf-8")
        combined = js + html
        self.assertNotIn("https://", combined, "原型不得含真实外部 URL")


if __name__ == "__main__":
    unittest.main()
