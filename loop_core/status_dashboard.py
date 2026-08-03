"""
status_dashboard — 兼容 shim（T-0109 F5 dashboard 四层合并）。

T-0109 将 Status Dashboard（ProjectStatus / Dashboard）收敛至
``loop_core.dashboard_views`` 单一实现（逻辑零改动迁移）；本模块保留
模块路径与导出符号，供既有消费方（hooks/scripts/session_brief.py、
tools/tool_dashboard.py、tests/test_status_dashboard.py）无感兼容。

行为等价：``status_dashboard.Dashboard is dashboard_views.Dashboard``；
全部语义（只读、fail-closed 默认值、健康指示）由 dashboard_views 承载，
test_status_dashboard.py 全绿为等价实证。
"""
from __future__ import annotations

from loop_core.dashboard_views import Dashboard, ProjectStatus  # noqa: F401

__all__ = ["Dashboard", "ProjectStatus"]
