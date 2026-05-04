"""PySide6 native desktop UI for the FlowPilot cockpit."""

from __future__ import annotations

import argparse
import math
import os
import sys
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QFileSystemWatcher, QPointF, QRectF, QSize, QSettings, Qt, QThread, QTimer, QUrl, Signal
from PySide6.QtGui import QAction, QBrush, QColor, QDesktopServices, QFont, QMouseEvent, QPainter, QPen
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QComboBox,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMenu,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QSystemTrayIcon,
)

from . import __version__
from .icon import apply_windows_app_id, create_app_icon
from .i18n import SUPPORT_URL, Translator, available_languages
from .models import CockpitSnapshot, NodeSummary
from .state_reader import FlowPilotStateReader
from .styles import QSS
from .update import RELEASES_URL, UpdateInfo, check_latest_release


ACCENT = QColor("#0FA37F")
ACCENT_DARK = QColor("#08785E")
SELECTED_BLUE = QColor("#2563EB")
TEXT = QColor("#14212B")
MUTED = QColor("#60717D")
BORDER = QColor("#D8E0E5")
DIVIDER = QColor("#E5EAEE")
SURFACE = QColor("#FFFFFF")
CANVAS = QColor("#FDFEFE")
BG = QColor("#F6F8FA")
OK = QColor("#0FA37F")
WARN = QColor("#B7791F")
ERROR = QColor("#B42318")
PENDING = QColor("#8A99A4")

ACTIVE_RUN_STATUSES = {"active", "running", "in_progress"}
COMPLETION_STATUSES = {"complete", "completed", "succeeded", "delivered"}


STATUS_COLORS = {
    "complete": OK,
    "completed": OK,
    "succeeded": OK,
    "running": ACCENT,
    "active": ACCENT,
    "in_progress": ACCENT,
    "pending": PENDING,
    "new": PENDING,
    "blocked": ERROR,
    "failed": ERROR,
    "error": ERROR,
    "degraded": WARN,
    "warning": WARN,
}


NODE_TITLE_ZH = {
    "node-001-startup-intake": "启动、材料理解和验收底线",
    "node-002-product-strategy-and-models": "功能展示策略与 FlowGuard 模型",
    "node-003-design-language-and-fresh-concepts": "设计语言、全新概念图和图标方向",
    "node-004-native-desktop-implementation": "原生 Windows 桌面驾驶舱实现",
    "node-005-rendered-qa-and-iteration": "截图、交互检查、审查和迭代",
    "node-006-terminal-closure": "最终路线台账与完成",
    "node-001-startup-and-scope": "启动、材料和范围",
    "node-002-flowguard-and-architecture": "FlowGuard 与架构",
    "node-003-topbar-tabs-status-settings": "顶部、标签和状态",
    "node-004-route-map-and-layout": "路线图和布局",
    "node-005-icon-visual-polish-and-i18n": "图标、视觉和双语",
    "node-006-qa-review-and-closure": "检查、截图和收尾",
}

RUN_TITLE_ZH = {
    "FlowPilot Windows desktop cockpit UI clean restart": "FlowPilot Windows 桌面驾驶舱 UI 全新重启",
    "FlowPilot Windows desktop cockpit UI from-scratch design": "FlowPilot Windows 桌面驾驶舱 UI 从零设计",
    "FlowPilot Cockpit medium UI optimization": "FlowPilot 驾驶舱 UI 优化",
}

RUN_TAB_TITLES = {
    "en": {
        "FlowPilot Windows desktop cockpit UI clean restart": "Clean restart",
        "FlowPilot Windows desktop cockpit UI from-scratch design": "From-scratch design",
        "FlowPilot Cockpit medium UI optimization": "UI optimization",
    },
    "zh": {
        "FlowPilot Windows desktop cockpit UI clean restart": "全新重启",
        "FlowPilot Windows desktop cockpit UI from-scratch design": "从零设计",
        "FlowPilot Cockpit medium UI optimization": "UI 优化",
    },
}

GATE_ZH = {
    "live_route_state_mapping": "实时路线状态映射",
    "multi_task_tabs": "多任务标签页",
    "full_i18n_switch": "完整中英文切换",
    "settings_support_entry": "设置与支持入口",
    "tray_lifecycle": "托盘生命周期",
    "restrained_motion": "克制动画反馈",
    "desktop_implementation": "桌面实现",
    "rendered_interaction_qa": "渲染与交互检查",
    "terminal_ledger": "最终台账",
    "startup_review": "启动审查",
    "pm_start_gate": "PM 启动门",
    "material_intake": "材料理解",
    "pm_material_understanding": "PM 材料理解",
    "product_function_architecture": "产品功能架构",
    "root_acceptance_contract": "验收底线",
    "process_flowguard_model": "流程 FlowGuard 模型",
    "product_flowguard_model": "产品 FlowGuard 模型",
    "task_visibility_model": "任务可见性模型",
    "route_map_interaction_model": "路线图交互模型",
    "version_capsule_model": "版本胶囊模型",
    "remove_main_support_button": "移除主界面支持按钮",
    "remove_source_ok_badge": "移除来源 OK 徽标",
    "active_task_tabs_only": "只显示当前任务",
    "closeable_tabs": "可关闭标签页",
    "settings_only_support": "支持只在设置里",
    "version_capsule": "版本胶囊",
    "expanded_route_map": "展开路线图",
    "checklist_columns": "检查项列",
    "pan_zoom_fit": "拖拽缩放适配",
    "current_node_centering": "定位当前节点",
    "splitter_layout": "可调面板",
    "layout_persistence": "记住布局",
    "single_icon_source": "统一图标来源",
    "taskbar_tray_window_icon_consistency": "任务栏托盘图标一致",
    "accent_hierarchy": "重点色层级",
    "full_i18n_update": "完整双语",
    "compact_window_text_fit": "紧凑文字适配",
    "desktop_screenshots": "桌面截图",
    "interaction_smoke": "交互冒烟检查",
    "tray_and_taskbar_check": "托盘和任务栏检查",
    "human_like_review": "人工视角审查",
    "final_route_wide_gate_ledger": "最终路线台账",
    "kb_postflight": "KB 收尾检查",
}


def status_color(status: str) -> QColor:
    return QColor(STATUS_COLORS.get(status, PENDING))


def display_run_title(language: str, title: str) -> str:
    if language == "zh":
        return RUN_TITLE_ZH.get(title, title)
    return title


def display_node_title(language: str, node: NodeSummary) -> str:
    if language == "zh":
        return NODE_TITLE_ZH.get(node.node_id, node.title)
    return node.title


class UpdateCheckThread(QThread):
    checked = Signal(object)

    def run(self) -> None:
        self.checked.emit(check_latest_release())


class RouteCanvas(QWidget):
    node_selected = Signal(str)

    def __init__(self, translator: Translator, parent: QWidget | None = None):
        super().__init__(parent)
        self.translator = translator
        self.snapshot: CockpitSnapshot | None = None
        self.selected_node_id: str | None = None
        self._node_rects: dict[str, QRectF] = {}
        self._content_rect = QRectF(0, 0, 900, 420)
        self._zoom = 1.0
        self._pan = QPointF(0, 0)
        self._drag_start: QPointF | None = None
        self._drag_pan = QPointF(0, 0)
        self._pulse = 0.0
        self._fit_pending = True
        self._user_moved = False
        self.setMinimumHeight(340)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.OpenHandCursor)

    def sizeHint(self) -> QSize:
        return QSize(860, 460)

    def set_snapshot(self, snapshot: CockpitSnapshot, selected_node_id: str | None) -> None:
        self.snapshot = snapshot
        self.selected_node_id = selected_node_id
        if not self._user_moved:
            self._fit_pending = True
        self.update()

    def set_pulse(self, value: float) -> None:
        self._pulse = value
        self.update()

    def fit_to_view(self) -> None:
        self._fit_pending = True
        self._user_moved = False
        self.update()

    def reset_view(self) -> None:
        self._zoom = 1.0
        self._pan = QPointF(0, 0)
        self._user_moved = True
        self.update()

    def center_current(self) -> None:
        if not self.snapshot:
            return
        node_id = self.selected_node_id or self.snapshot.active_node_id
        rect = self._node_rects.get(str(node_id))
        if rect is None:
            return
        target = rect.center()
        center = QPointF(self.width() / 2, self.height() / 2)
        content_center = self._content_rect.center()
        self._pan = QPointF(
            center.x() - (target.x() - content_center.x()) * self._zoom - self.width() / 2,
            center.y() - (target.y() - content_center.y()) * self._zoom - self.height() / 2,
        )
        self._user_moved = True
        self.update()

    def paintEvent(self, event) -> None:  # noqa: ANN001
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect()
        painter.fillRect(rect, CANVAS)
        self._draw_grid(painter)

        if not self.snapshot or not self.snapshot.nodes:
            painter.setPen(MUTED)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self.translator.t("no_nodes"))
            painter.end()
            return

        nodes = self.snapshot.nodes
        self._node_rects = self._layout_nodes(nodes)
        if self._fit_pending:
            self._apply_fit()
            self._fit_pending = False

        painter.save()
        self._apply_transform(painter)
        self._draw_connections(painter, nodes)
        for node in nodes:
            node_rect = self._node_rects[node.node_id]
            self._draw_node(painter, node, node_rect)
            self._draw_checklist_column(painter, node, node_rect)
        painter.restore()
        self._draw_view_badge(painter)
        painter.end()

    def _draw_grid(self, painter: QPainter) -> None:
        painter.setPen(QPen(QColor("#EAF0F3"), 1))
        step = 24
        for x in range(0, self.width(), step):
            for y in range(0, self.height(), step):
                painter.drawPoint(x, y)

    def _layout_nodes(self, nodes: tuple[NodeSummary, ...]) -> dict[str, QRectF]:
        count = max(len(nodes), 1)
        margin_x = 48
        margin_y = 42
        node_w = 210
        node_h = 76
        gap = 58
        main_y = 112
        rects: dict[str, QRectF] = {}
        max_gates = max((len(node.required_gates) for node in nodes), default=0)
        content_w = margin_x * 2 + count * node_w + max(0, count - 1) * gap
        content_h = margin_y + main_y + node_h + 44 + max(max_gates, 1) * 34 + 42
        self._content_rect = QRectF(0, 0, content_w, content_h)
        for index, node in enumerate(nodes):
            x = margin_x + index * (node_w + gap)
            rects[node.node_id] = QRectF(x, main_y, node_w, node_h)
        return rects

    def _draw_connections(self, painter: QPainter, nodes: tuple[NodeSummary, ...]) -> None:
        if not nodes:
            return
        y = next(iter(self._node_rects.values())).center().y()
        start_x = self._node_rects[nodes[0].node_id].left() - 26
        end_x = self._node_rects[nodes[-1].node_id].right() + 26
        painter.setPen(QPen(QColor("#C9D4DA"), 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(QPointF(start_x, y), QPointF(end_x, y))
        for left, right in zip(nodes, nodes[1:]):
            a = self._node_rects[left.node_id]
            b = self._node_rects[right.node_id]
            start = QPointF(a.right(), y)
            end = QPointF(b.left(), y)
            current_path = left.status in {"complete", "completed", "succeeded", "running", "active", "in_progress"}
            pen = QPen(ACCENT if current_path else QColor("#AEBAC2"), 4.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
            if not current_path:
                pen.setStyle(Qt.PenStyle.DashLine)
            painter.setPen(pen)
            painter.drawLine(start, end)

    def _draw_node(self, painter: QPainter, node: NodeSummary, rect: QRectF) -> None:
        selected = node.node_id == self.selected_node_id
        active = self.snapshot is not None and node.node_id == self.snapshot.active_node_id
        color = status_color(node.status)
        if active:
            radius = 12 + 14 * (0.5 + 0.5 * math.sin(self._pulse * math.pi * 2))
            painter.setPen(QPen(QColor(11, 143, 156, 46), 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(rect.center(), radius, radius)

        status_has_border = node.status in {
            "complete",
            "completed",
            "succeeded",
            "running",
            "active",
            "in_progress",
            "blocked",
            "failed",
            "error",
            "degraded",
            "warning",
        }
        border_color = color if status_has_border else BORDER
        painter.setPen(QPen(border_color, 2.0 if status_has_border else 1.2))
        fill = QColor("#F1FFFB") if active else SURFACE
        painter.setBrush(fill)
        painter.drawRoundedRect(rect, 5, 5)

        if selected:
            selected_rect = rect.adjusted(-5, -5, 5, 5)
            painter.setPen(QPen(SELECTED_BLUE, 2.2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(selected_rect, 7, 7)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        painter.drawEllipse(QPointF(rect.left() + 20, rect.top() + 22), 6, 6)

        painter.setPen(TEXT)
        title_font = QFont("Segoe UI", 10)
        title_font.setBold(active or selected)
        painter.setFont(title_font)
        title = painter.fontMetrics().elidedText(display_node_title(self.translator.language, node), Qt.TextElideMode.ElideRight, int(rect.width() - 48))
        painter.drawText(QRectF(rect.left() + 38, rect.top() + 12, rect.width() - 46, 22), Qt.AlignmentFlag.AlignLeft, title)

        painter.setFont(QFont("Segoe UI", 8))
        painter.setPen(MUTED)
        status = painter.fontMetrics().elidedText(self.translator.status(node.status), Qt.TextElideMode.ElideRight, int(rect.width() - 42))
        painter.drawText(QRectF(rect.left() + 38, rect.top() + 42, rect.width() - 46, 18), Qt.AlignmentFlag.AlignLeft, status)

    def _draw_checklist_column(self, painter: QPainter, node: NodeSummary, rect: QRectF) -> None:
        gates = node.required_gates or (self.translator.t("no_checklist_items"),)
        x = rect.left()
        top = rect.bottom() + 24
        painter.setPen(QPen(QColor("#AFC9C1"), 1.4))
        painter.drawLine(QPointF(rect.center().x(), rect.bottom()), QPointF(rect.center().x(), top - 8))
        painter.setFont(QFont("Segoe UI", 8))
        for index, gate in enumerate(gates):
            item_rect = QRectF(x, top + index * 34, rect.width(), 26)
            state = self._check_state(node, index, len(gates))
            color = status_color(state)
            painter.setPen(QPen(color if state != "pending" else BORDER, 1.2))
            painter.setBrush(QColor("#F8FFFC") if state in {"running", "active", "in_progress"} else SURFACE)
            painter.drawRoundedRect(item_rect, 4, 4)
            self._draw_check_mark(painter, QPointF(item_rect.left() + 13, item_rect.center().y()), state, color)
            painter.setPen(TEXT if state != "pending" else MUTED)
            text = painter.fontMetrics().elidedText(self._display_gate(gate), Qt.TextElideMode.ElideRight, int(item_rect.width() - 36))
            painter.drawText(QRectF(item_rect.left() + 28, item_rect.top() + 5, item_rect.width() - 34, 16), Qt.AlignmentFlag.AlignLeft, text)

    def _check_state(self, node: NodeSummary, index: int, total: int) -> str:
        if node.status in {"complete", "completed", "succeeded"}:
            return "complete"
        if node.status in {"blocked", "failed", "error"}:
            return "blocked"
        if node.status in {"degraded", "warning"}:
            return "degraded"
        if node.status in {"running", "active", "in_progress"}:
            return "running" if index == 0 else "pending"
        if total == 1 and not node.required_gates:
            return "pending"
        return "pending"

    def _draw_check_mark(self, painter: QPainter, center: QPointF, state: str, color: QColor) -> None:
        painter.setPen(QPen(color, 1.5))
        painter.setBrush(QColor("#FDFEFE"))
        painter.drawEllipse(center, 7, 7)
        if state in {"complete", "completed", "succeeded"}:
            painter.setPen(QPen(color, 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            painter.drawLine(QPointF(center.x() - 3.4, center.y()), QPointF(center.x() - 0.8, center.y() + 3.0))
            painter.drawLine(QPointF(center.x() - 0.8, center.y() + 3.0), QPointF(center.x() + 4.2, center.y() - 4.0))
        elif state in {"running", "active", "in_progress"}:
            painter.setBrush(color)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(center, 3.5, 3.5)
        elif state in {"blocked", "failed", "error"}:
            painter.setPen(QPen(color, 1.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            painter.drawLine(QPointF(center.x() - 3.5, center.y() - 3.5), QPointF(center.x() + 3.5, center.y() + 3.5))
            painter.drawLine(QPointF(center.x() + 3.5, center.y() - 3.5), QPointF(center.x() - 3.5, center.y() + 3.5))

    def _draw_view_badge(self, painter: QPainter) -> None:
        painter.setFont(QFont("Segoe UI", 8))
        painter.setPen(MUTED)
        text = f"{int(self._zoom * 100)}% · {self.translator.t('drag_zoom_hint')}"
        painter.drawText(QRectF(12, self.height() - 30, self.width() - 24, 20), Qt.AlignmentFlag.AlignRight, text)

    def _display_gate(self, value: str) -> str:
        if self.translator.language == "zh":
            return GATE_ZH.get(value, self._humanize(value))
        return self._humanize(value)

    def _humanize(self, value: str) -> str:
        words = value.replace("-", "_").split("_")
        return " ".join(word.capitalize() if word.lower() not in {"ui", "i18n", "pm", "kb"} else word.upper() for word in words if word)

    def _apply_transform(self, painter: QPainter) -> None:
        center = self._content_rect.center()
        painter.translate(self.width() / 2 + self._pan.x(), self.height() / 2 + self._pan.y())
        painter.scale(self._zoom, self._zoom)
        painter.translate(-center.x(), -center.y())

    def _apply_fit(self) -> None:
        if self._content_rect.width() <= 0 or self._content_rect.height() <= 0:
            return
        usable_w = max(120, self.width() - 42)
        usable_h = max(120, self.height() - 48)
        self._zoom = max(0.38, min(1.35, usable_w / self._content_rect.width(), usable_h / self._content_rect.height()))
        self._pan = QPointF(0, 0)

    def _scene_pos(self, point: QPointF) -> QPointF:
        center = self._content_rect.center()
        return QPointF(
            (point.x() - self.width() / 2 - self._pan.x()) / self._zoom + center.x(),
            (point.y() - self.height() / 2 - self._pan.y()) / self._zoom + center.y(),
        )

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            scene_point = self._scene_pos(event.position())
            for node_id, rect in self._node_rects.items():
                if rect.contains(scene_point):
                    self.selected_node_id = node_id
                    self.node_selected.emit(node_id)
                    self.update()
                    return
            self._drag_start = event.position()
            self._drag_pan = QPointF(self._pan)
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drag_start is not None:
            delta = event.position() - self._drag_start
            self._pan = self._drag_pan + delta
            self._user_moved = True
            self.update()
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._drag_start is not None:
            self._drag_start = None
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event) -> None:  # noqa: ANN001
        before = self._scene_pos(event.position())
        factor = 1.12 if event.angleDelta().y() > 0 else 1 / 1.12
        self._zoom = max(0.38, min(2.4, self._zoom * factor))
        after = self._scene_pos(event.position())
        self._pan += QPointF((after.x() - before.x()) * self._zoom, (after.y() - before.y()) * self._zoom)
        self._user_moved = True
        self.update()

    def resizeEvent(self, event) -> None:  # noqa: ANN001
        if not self._user_moved:
            self._fit_pending = True
        super().resizeEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        del event
        self.fit_to_view()

class SettingsDialog(QDialog):
    def __init__(self, window: "CockpitWindow"):
        super().__init__(window)
        self.window = window
        self.setModal(True)
        self.setMinimumWidth(420)
        self.setWindowIcon(create_app_icon())
        self.layout = QVBoxLayout(self)
        self.title = QLabel()
        self.title.setObjectName("panelTitle")
        self.intro = QLabel()
        self.intro.setObjectName("muted")
        self.intro.setWordWrap(True)
        self.language_label = QLabel()
        self.language_combo = QComboBox()
        for language in available_languages():
            self.language_combo.addItem("English" if language == "en" else "中文", language)
        self.language_combo.currentIndexChanged.connect(self._language_changed)
        self.support_title = QLabel()
        self.support_title.setObjectName("panelTitle")
        self.support_body = QLabel()
        self.support_body.setObjectName("muted")
        self.support_body.setWordWrap(True)
        self.support_button = QPushButton()
        self.support_button.clicked.connect(window.open_support)
        self.reset_layout_button = QPushButton()
        self.reset_layout_button.clicked.connect(window.reset_layout)
        self.close_button = QPushButton()
        self.close_button.clicked.connect(self.accept)

        grid = QGridLayout()
        grid.addWidget(self.language_label, 0, 0)
        grid.addWidget(self.language_combo, 0, 1)
        self.layout.addWidget(self.title)
        self.layout.addWidget(self.intro)
        self.layout.addSpacing(8)
        self.layout.addLayout(grid)
        self.layout.addSpacing(18)
        self.layout.addWidget(self.support_title)
        self.layout.addWidget(self.support_body)
        self.layout.addWidget(self.support_button)
        self.layout.addSpacing(14)
        self.layout.addWidget(self.reset_layout_button)
        self.layout.addStretch(1)
        self.layout.addWidget(self.close_button, alignment=Qt.AlignmentFlag.AlignRight)
        self.retranslate()

    def _language_changed(self) -> None:
        language = self.language_combo.currentData()
        if language != self.window.translator.language:
            self.window.set_language(str(language))
        self.retranslate()

    def retranslate(self) -> None:
        t = self.window.translator.t
        self.setWindowTitle(t("settings_title"))
        self.title.setText(t("settings_title"))
        self.intro.setText(t("settings_intro"))
        self.language_label.setText(t("language"))
        self.support_title.setText(t("support_title"))
        self.support_body.setText(t("support_body"))
        self.support_button.setText(t("open_support"))
        self.reset_layout_button.setText(t("reset_layout"))
        self.close_button.setText(t("close"))
        index = self.language_combo.findData(self.window.translator.language)
        if index >= 0:
            self.language_combo.blockSignals(True)
            self.language_combo.setCurrentIndex(index)
            self.language_combo.blockSignals(False)


class CockpitWindow(QMainWindow):
    def __init__(self, project_root: Path, language: str = "en", screenshot_out: Path | None = None):
        super().__init__()
        self.project_root = project_root.resolve()
        self.reader = FlowPilotStateReader(self.project_root)
        self.translator = Translator(language)
        self.snapshot: CockpitSnapshot | None = None
        self.selected_run_id: str | None = None
        self.selected_node_id: str | None = None
        self.force_exit = False
        self.screenshot_out = screenshot_out
        self.settings = QSettings("FlowPilot", "Cockpit")
        self.hidden_run_ids = self._load_hidden_run_ids()
        self.update_info = UpdateInfo(current_version=__version__)
        self.update_thread: UpdateCheckThread | None = None
        self.icon = create_app_icon()
        self.setWindowIcon(self.icon)
        self.setMinimumSize(900, 620)

        self.watcher = QFileSystemWatcher(self)
        self.watcher.fileChanged.connect(self._source_changed)
        self.watcher.directoryChanged.connect(self._source_changed)
        self.refresh_timer = QTimer(self)
        self.refresh_timer.setSingleShot(True)
        self.refresh_timer.timeout.connect(self.update_snapshot)
        self.poll_timer = QTimer(self)
        self.poll_timer.setInterval(1500)
        self.poll_timer.timeout.connect(self.update_snapshot)
        self.pulse_timer = QTimer(self)
        self.pulse_timer.setInterval(70)
        self._pulse_tick = 0
        self.pulse_timer.timeout.connect(self._pulse)

        self._build_ui()
        self._build_tray()
        self.set_language(language)
        self.update_snapshot()
        self.poll_timer.start()
        self.pulse_timer.start()
        QTimer.singleShot(1200, self._start_update_check)

    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        main = QVBoxLayout(root)
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(0)

        self.top_rail = QFrame()
        self.top_rail.setObjectName("topRail")
        top = QHBoxLayout(self.top_rail)
        top.setContentsMargins(12, 0, 12, 0)
        top.setSpacing(10)
        self.app_title = QLabel()
        self.app_title.setObjectName("appTitle")
        top.addWidget(self.app_title)
        self.tab_container = QWidget()
        self.tab_layout = QHBoxLayout(self.tab_container)
        self.tab_layout.setContentsMargins(8, 0, 0, 0)
        self.tab_layout.setSpacing(8)
        top.addWidget(self.tab_container, 1)
        self.source_alert = QLabel()
        self.source_alert.setObjectName("sourceAlert")
        self.source_alert.setVisible(False)
        top.addWidget(self.source_alert)
        self.language_combo = QComboBox()
        for language in available_languages():
            self.language_combo.addItem("EN" if language == "en" else "中文", language)
        self.language_combo.currentIndexChanged.connect(self._combo_language_changed)
        top.addWidget(self.language_combo)
        self.settings_button = QPushButton()
        self.settings_button.clicked.connect(self.open_settings)
        top.addWidget(self.settings_button)
        self.version_capsule = QPushButton()
        self.version_capsule.setObjectName("versionCapsule")
        self.version_capsule.clicked.connect(self.open_release_page)
        top.addWidget(self.version_capsule)
        main.addWidget(self.top_rail)

        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_splitter.setObjectName("mainSplitter")
        self.main_splitter.setChildrenCollapsible(False)
        self.main_splitter.splitterMoved.connect(self._save_layout_state)
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(10, 10, 0, 0)
        left_layout.setSpacing(8)
        self.left_splitter = QSplitter(Qt.Orientation.Vertical)
        self.left_splitter.setObjectName("leftSplitter")
        self.left_splitter.setChildrenCollapsible(False)
        self.left_splitter.splitterMoved.connect(self._save_layout_state)
        self.route_panel = QFrame()
        self.route_panel.setObjectName("routePanel")
        route_layout = QVBoxLayout(self.route_panel)
        route_layout.setContentsMargins(12, 10, 12, 10)
        route_header = QHBoxLayout()
        self.route_title = QLabel()
        self.route_title.setObjectName("sectionTitle")
        self.route_meta = QLabel()
        self.route_meta.setObjectName("muted")
        route_header.addWidget(self.route_title)
        route_header.addStretch(1)
        route_header.addWidget(self.route_meta)
        self.fit_button = QPushButton()
        self.fit_button.setObjectName("toolButton")
        self.center_button = QPushButton()
        self.center_button.setObjectName("toolButton")
        self.reset_zoom_button = QPushButton()
        self.reset_zoom_button.setObjectName("toolButton")
        route_header.addWidget(self.fit_button)
        route_header.addWidget(self.center_button)
        route_header.addWidget(self.reset_zoom_button)
        route_layout.addLayout(route_header)
        self.canvas = RouteCanvas(self.translator)
        self.canvas.node_selected.connect(self._select_node)
        self.fit_button.clicked.connect(self.canvas.fit_to_view)
        self.center_button.clicked.connect(self.canvas.center_current)
        self.reset_zoom_button.clicked.connect(self.canvas.reset_view)
        route_layout.addWidget(self.canvas, 1)
        self.left_splitter.addWidget(self.route_panel)

        self.events_panel = QFrame()
        self.events_panel.setObjectName("bottomRail")
        events_layout = QVBoxLayout(self.events_panel)
        events_layout.setContentsMargins(10, 8, 10, 8)
        events_header = QHBoxLayout()
        self.events_title = QLabel()
        self.events_title.setObjectName("sectionTitle")
        self.watch_status = QLabel()
        self.watch_status.setObjectName("muted")
        events_header.addWidget(self.events_title)
        events_header.addStretch(1)
        events_header.addWidget(self.watch_status)
        events_layout.addLayout(events_header)
        self.status_sentence = QLabel()
        self.status_sentence.setObjectName("statusSentence")
        self.status_sentence.setWordWrap(True)
        self.status_sentence.setMinimumHeight(52)
        events_layout.addWidget(self.status_sentence)
        self.left_splitter.addWidget(self.events_panel)
        left_layout.addWidget(self.left_splitter, 1)
        self.main_splitter.addWidget(left)

        self.inspector = QFrame()
        self.inspector.setObjectName("rightInspector")
        inspector_layout = QVBoxLayout(self.inspector)
        inspector_layout.setContentsMargins(14, 12, 14, 12)
        inspector_layout.setSpacing(8)
        self.inspector_title = QLabel()
        self.inspector_title.setObjectName("sectionTitle")
        self.node_title = QLabel()
        self.node_title.setWordWrap(True)
        self.node_title.setObjectName("nodeSummary")
        self.node_status = QLabel()
        self.node_status.setObjectName("nodeStatus")
        self.meta_grid = QGridLayout()
        self.meta_grid.setVerticalSpacing(5)
        self.run_meta_label = QLabel()
        self.route_meta_label = QLabel()
        self.active_node_label = QLabel()
        self.workspace_label = QLabel()
        self.workspace_label.setWordWrap(True)
        for row, widget in enumerate((self.run_meta_label, self.route_meta_label, self.active_node_label, self.workspace_label)):
            widget.setObjectName("metaLine")
            self.meta_grid.addWidget(widget, row, 0)
        self.gates_title = QLabel()
        self.gates_title.setObjectName("sectionTitle")
        self.gates_table = QTableWidget(0, 1)
        self.gates_table.verticalHeader().setVisible(False)
        self.gates_table.horizontalHeader().setVisible(False)
        self.gates_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.gates_table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.gates_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.gates_table.setShowGrid(False)
        self.gates_table.setMaximumHeight(260)
        self.findings_title = QLabel()
        self.findings_title.setObjectName("panelTitle")
        self.findings_label = QLabel()
        self.findings_label.setObjectName("muted")
        self.findings_label.setWordWrap(True)

        inspector_layout.addWidget(self.inspector_title)
        inspector_layout.addWidget(self.node_title)
        inspector_layout.addWidget(self.node_status)
        inspector_layout.addLayout(self.meta_grid)
        inspector_layout.addSpacing(12)
        inspector_layout.addWidget(self.gates_title)
        inspector_layout.addWidget(self.gates_table)
        inspector_layout.addStretch(1)
        inspector_layout.addWidget(self.findings_title)
        inspector_layout.addWidget(self.findings_label)
        self.main_splitter.addWidget(self.inspector)
        self._restore_layout_state()
        main.addWidget(self.main_splitter, 1)

    def _load_hidden_run_ids(self) -> set[str]:
        raw = self.settings.value("hiddenRunIds", [])
        if raw is None:
            return set()
        if isinstance(raw, str):
            return {item for item in raw.split("|") if item}
        return {str(item) for item in raw if str(item)}

    def _save_hidden_run_ids(self) -> None:
        self.settings.setValue("hiddenRunIds", "|".join(sorted(self.hidden_run_ids)))

    def _restore_layout_state(self) -> None:
        main_sizes = self.settings.value("mainSplitterSizes")
        left_sizes = self.settings.value("leftSplitterSizes")
        if isinstance(main_sizes, list) and len(main_sizes) == 2:
            self.main_splitter.setSizes([int(value) for value in main_sizes])
        else:
            self.main_splitter.setSizes([1040, 350])
        if isinstance(left_sizes, list) and len(left_sizes) == 2:
            self.left_splitter.setSizes([int(value) for value in left_sizes])
        else:
            self.left_splitter.setSizes([680, 120])

    def _save_layout_state(self) -> None:
        self.settings.setValue("mainSplitterSizes", self.main_splitter.sizes())
        self.settings.setValue("leftSplitterSizes", self.left_splitter.sizes())

    def reset_layout(self) -> None:
        self.main_splitter.setSizes([1040, 350])
        self.left_splitter.setSizes([680, 120])
        self.canvas.fit_to_view()
        self._save_layout_state()

    def _build_tray(self) -> None:
        self.tray = QSystemTrayIcon(self.icon, self)
        self.tray_menu = QMenu()
        self.restore_action = QAction()
        self.exit_action = QAction()
        self.restore_action.triggered.connect(self.show_from_tray)
        self.exit_action.triggered.connect(self.exit_from_tray)
        self.tray_menu.addAction(self.restore_action)
        self.tray_menu.addSeparator()
        self.tray_menu.addAction(self.exit_action)
        self.tray.setContextMenu(self.tray_menu)
        self.tray.activated.connect(self._tray_activated)
        self.tray.show()

    def set_language(self, language: str) -> None:
        self.translator.set_language(language)
        index = self.language_combo.findData(language)
        if index >= 0:
            self.language_combo.blockSignals(True)
            self.language_combo.setCurrentIndex(index)
            self.language_combo.blockSignals(False)
        self._retranslate()
        if self.snapshot:
            self._render_snapshot()

    def _combo_language_changed(self) -> None:
        language = self.language_combo.currentData()
        if language:
            self.set_language(str(language))

    def _retranslate(self) -> None:
        t = self.translator.t
        self.setWindowTitle(t("app_title"))
        self.app_title.setText(t("app_title"))
        self.settings_button.setText(t("settings"))
        self.route_title.setText(t("route_canvas"))
        self.events_title.setText(t("realtime_status"))
        self.inspector_title.setText(t("node_inspector"))
        self.gates_title.setText(t("checklist"))
        self.findings_title.setText(t("source_findings"))
        self.fit_button.setText(t("fit"))
        self.center_button.setText(t("center_current"))
        self.reset_zoom_button.setText(t("reset_zoom"))
        self.restore_action.setText(t("tray_restore"))
        self.exit_action.setText(t("tray_exit"))
        self.gates_table.setHorizontalHeaderLabels([t("checklist")])
        self._render_version_capsule()

    def update_snapshot(self) -> None:
        try:
            self.snapshot = self.reader.read_project(self.selected_run_id, hidden_run_ids=self.hidden_run_ids)
        except TypeError:
            self.snapshot = self.reader.read_project(self.selected_run_id)
        if self.snapshot.selected_run_id:
            self.selected_run_id = self.snapshot.selected_run_id
        node_ids = {node.node_id for node in self.snapshot.nodes}
        if self.selected_node_id not in node_ids:
            self.selected_node_id = self.snapshot.active_node_id
        self._render_snapshot()
        self._update_watcher()

    def _render_snapshot(self) -> None:
        if not self.snapshot:
            return
        self._render_tabs()
        route_label = self.snapshot.selected_route_id or "-"
        version = self.snapshot.route_version if self.snapshot.route_version is not None else "-"
        self.route_meta.setText(f"{self.translator.t('route')}: {route_label} · v{version}")
        unhealthy = self.snapshot.source_health != "ok"
        self.source_alert.setVisible(unhealthy)
        self.source_alert.setText(self.translator.t("source_degraded") if unhealthy else "")
        self.canvas.set_snapshot(self.snapshot, self.selected_node_id)
        self._render_inspector()
        self._render_events()
        self.watch_status.setText(f"{self.translator.t('auto_refresh')} · {len(self.snapshot.watched_paths)}")

    def _render_tabs(self) -> None:
        while self.tab_layout.count():
            item = self.tab_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        if not self.snapshot:
            return
        for run in self.snapshot.runs:
            if not self._run_visible(run):
                continue
            selected = run.run_id == self.snapshot.selected_run_id
            tab = QFrame()
            tab.setObjectName("tabPill")
            tab.setProperty("selected", selected)
            tab.setMaximumHeight(42)
            tab_layout = QHBoxLayout(tab)
            tab_layout.setContentsMargins(4, 0, 2, 0)
            tab_layout.setSpacing(2)
            title = self._run_tab_title(run)
            button = QPushButton(f"{self._status_dot(run.status)} {self._short_text(title, 24)}")
            button.setObjectName("tabButton")
            button.setToolTip(run.run_id)
            button.clicked.connect(lambda checked=False, run_id=run.run_id: self._select_run(run_id))
            close = QPushButton("×")
            close.setObjectName("tabCloseButton")
            close.setToolTip(self.translator.t("close_tab"))
            close.clicked.connect(lambda checked=False, run_id=run.run_id: self._close_run_tab(run_id))
            tab_layout.addWidget(button)
            tab_layout.addWidget(close)
            for widget in (tab, button, close):
                widget.style().unpolish(widget)
                widget.style().polish(widget)
            self.tab_layout.addWidget(tab)
        self.tab_layout.addStretch(1)

    def _run_visible(self, run) -> bool:  # noqa: ANN001
        return bool(run.visible) and run.run_id not in self.hidden_run_ids

    def _status_dot(self, status: str) -> str:
        if status in {"complete", "completed", "succeeded"}:
            return "●"
        if status in {"blocked", "failed", "error"}:
            return "●"
        if status in {"degraded", "warning"}:
            return "●"
        return "●"

    def _short_text(self, text: str, limit: int) -> str:
        if len(text) <= limit:
            return text
        return text[: max(1, limit - 1)].rstrip() + "…"

    def _run_display_title(self, title: str) -> str:
        return display_run_title(self.translator.language, title)

    def _run_tab_title(self, run) -> str:  # noqa: ANN001
        short = RUN_TAB_TITLES.get(self.translator.language, {}).get(run.title, self._run_display_title(run.title))
        date = self._tab_date(run.created_at)
        return f"{date} {short}" if date else short

    def _tab_date(self, raw: str | None) -> str:
        if not raw:
            return ""
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return raw[:10]
        return parsed.strftime("%m/%d")

    def _node_display_title(self, node: NodeSummary) -> str:
        return display_node_title(self.translator.language, node)

    def _select_run(self, run_id: str) -> None:
        self.selected_run_id = run_id
        self.selected_node_id = None
        self.update_snapshot()

    def _close_run_tab(self, run_id: str) -> None:
        self.hidden_run_ids.add(run_id)
        self._save_hidden_run_ids()
        if self.selected_run_id == run_id:
            self.selected_run_id = None
            self.selected_node_id = None
        self.update_snapshot()

    def _select_node(self, node_id: str) -> None:
        self.selected_node_id = node_id
        self._render_inspector()
        if self.snapshot:
            self.canvas.set_snapshot(self.snapshot, self.selected_node_id)

    def _render_inspector(self) -> None:
        if not self.snapshot:
            return
        node = self._selected_node()
        if node is None:
            self.node_title.setText(self.translator.t("no_nodes"))
            self.node_status.setText("")
            return
        self.node_title.setText(f"{self.translator.t('viewing_node')}: {self._node_display_title(node)}")
        self.node_status.setText(f"{self.translator.t('status')}: {self.translator.status(node.status)}")
        run = self.snapshot.selected_run
        run_label = self._run_display_title(run.title) if run else "-"
        self.run_meta_label.setText(f"{self.translator.t('run')}: {run_label}")
        self.route_meta_label.setText(f"{self.translator.t('route')}: {self.snapshot.selected_route_id or '-'}")
        if self._snapshot_complete():
            self.active_node_label.setText(f"{self.translator.t('run_complete')}: {self.translator.t('complete')}")
        else:
            active_node = self.snapshot.active_node
            active_label = self._node_display_title(active_node) if active_node else self.snapshot.active_node_id or "-"
            self.active_node_label.setText(f"{self.translator.t('active_node')}: {active_label}")
        self.workspace_label.setText(f"{self.translator.t('workspace')}: {self.snapshot.workspace_root}")
        self._fill_checklist_table(node)
        has_findings = bool(self.snapshot.source_findings)
        self.findings_title.setVisible(has_findings)
        self.findings_label.setVisible(has_findings)
        findings = "\n".join(self.snapshot.source_findings) if has_findings else ""
        self.findings_label.setText(findings)

    def _selected_node(self) -> NodeSummary | None:
        if not self.snapshot:
            return None
        for node in self.snapshot.nodes:
            if node.node_id == self.selected_node_id:
                return node
        return self.snapshot.active_node

    def _fill_single_column(self, table: QTableWidget, values: tuple[str, ...]) -> None:
        table.setRowCount(len(values))
        for row, value in enumerate(values):
            item = QTableWidgetItem(value)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            table.setItem(row, 0, item)

    def _fill_checklist_table(self, node: NodeSummary) -> None:
        gates = node.required_gates or (self.translator.t("no_checklist_items"),)
        self.gates_table.setRowCount(len(gates))
        for row, value in enumerate(gates):
            state = self.canvas._check_state(node, row, len(gates))
            label = self._display_gate(value)
            if state in {"complete", "completed", "succeeded"}:
                text = f"{self.translator.t('done')}: {label}"
            elif state in {"running", "active", "in_progress"}:
                text = f"{self.translator.t('doing')}: {label}"
            elif state in {"blocked", "failed", "error"}:
                text = f"{self.translator.t('blocked')}: {label}"
            else:
                text = f"{self.translator.t('pending')}: {label}"
            item = QTableWidgetItem(text)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            item.setForeground(QBrush(status_color(state)))
            self.gates_table.setItem(row, 0, item)

    def _humanize(self, value: str) -> str:
        words = value.replace("-", "_").split("_")
        return " ".join(word.capitalize() if word.lower() not in {"ui", "i18n"} else word.upper() for word in words if word)

    def _display_gate(self, value: str) -> str:
        if self.translator.language == "zh":
            return GATE_ZH.get(value, self._humanize(value))
        return self._humanize(value)

    def _render_events(self) -> None:
        if not self.snapshot:
            return
        if self._snapshot_complete():
            self.status_sentence.setText(self.translator.t("completion_status_sentence"))
            return
        node = self.snapshot.active_node
        if node is None:
            self.status_sentence.setText(self.translator.t("no_nodes"))
            return
        run = self.snapshot.selected_run
        run_title = self._run_display_title(run.title) if run else self.translator.t("current_task")
        node_title = self._node_display_title(node)
        status = self.translator.status(node.status)
        self.status_sentence.setText(
            self.translator.t("status_sentence").format(run=run_title, node=node_title, status=status)
        )

    def _snapshot_complete(self) -> bool:
        if not self.snapshot or not self.snapshot.nodes:
            return False
        if self.snapshot.route_status not in COMPLETION_STATUSES:
            return False
        return all(node.status in COMPLETION_STATUSES for node in self.snapshot.nodes)

    def _update_watcher(self) -> None:
        if not self.snapshot:
            return
        current_files = self.watcher.files()
        if current_files:
            self.watcher.removePaths(current_files)
        current_dirs = self.watcher.directories()
        if current_dirs:
            self.watcher.removePaths(current_dirs)
        paths = [str(path) for path in self.snapshot.watched_paths if path.exists()]
        dirs = {str(path.parent) for path in self.snapshot.watched_paths if path.parent.exists()}
        if paths:
            self.watcher.addPaths(paths)
        if dirs:
            self.watcher.addPaths(sorted(dirs))

    def _source_changed(self, path: str) -> None:
        del path
        self.refresh_timer.start(160)

    def _pulse(self) -> None:
        self._pulse_tick = (self._pulse_tick + 1) % 120
        self.canvas.set_pulse(self._pulse_tick / 120.0)

    def open_settings(self) -> None:
        dialog = SettingsDialog(self)
        dialog.exec()

    def open_support(self) -> None:
        QDesktopServices.openUrl(QUrl(SUPPORT_URL))

    def open_release_page(self) -> None:
        QDesktopServices.openUrl(QUrl(self.update_info.release_url or RELEASES_URL))

    def _render_version_capsule(self) -> None:
        if self.update_info.has_update:
            self.version_capsule.setText(
                self.translator.t("version_update_available").format(version=self.update_info.latest_version)
            )
            self.version_capsule.setProperty("update", True)
        else:
            self.version_capsule.setText(self.translator.t("version_current").format(version=__version__))
            self.version_capsule.setProperty("update", False)
        self.version_capsule.style().unpolish(self.version_capsule)
        self.version_capsule.style().polish(self.version_capsule)

    def _start_update_check(self) -> None:
        if self.update_thread is not None and self.update_thread.isRunning():
            return
        self.version_capsule.setText(self.translator.t("version_checking").format(version=__version__))
        self.update_thread = UpdateCheckThread(self)
        self.update_thread.checked.connect(self._update_checked)
        self.update_thread.finished.connect(self._update_thread_finished)
        self.update_thread.start()

    def _update_checked(self, info: object) -> None:
        if isinstance(info, UpdateInfo):
            self.update_info = info
        self._render_version_capsule()

    def _update_thread_finished(self) -> None:
        self.update_thread = None

    def _shutdown_update_thread(self) -> None:
        try:
            if self.update_thread is not None and self.update_thread.isRunning():
                self.update_thread.wait(3500)
        except RuntimeError:
            self.update_thread = None

    def show_from_tray(self) -> None:
        self.show()
        self.raise_()
        self.activateWindow()

    def exit_from_tray(self) -> None:
        self.force_exit = True
        self.tray.hide()
        self._shutdown_update_thread()
        QApplication.quit()

    def _tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_from_tray()

    def closeEvent(self, event) -> None:  # noqa: ANN001
        if self.force_exit:
            self._shutdown_update_thread()
            event.accept()
            return
        event.ignore()
        self.hide()
        if self.tray.isVisible():
            self.tray.showMessage(
                self.translator.t("app_title"),
                self.translator.t("tray_minimized"),
                self.icon,
                2500,
            )

    def save_screenshot_and_quit(self) -> None:
        if self.screenshot_out is None:
            return
        self.screenshot_out.parent.mkdir(parents=True, exist_ok=True)
        self.grab().save(str(self.screenshot_out))
        self._shutdown_update_thread()
        QApplication.quit()


def parse_size(raw: str) -> QSize:
    try:
        width, height = raw.lower().split("x", 1)
        return QSize(int(width), int(height))
    except Exception as exc:  # noqa: BLE001
        raise argparse.ArgumentTypeError("size must look like 1440x900") from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Launch the native FlowPilot cockpit.")
    parser.add_argument("--project-root", default=".", help="Repository root that contains .flowpilot")
    parser.add_argument("--language", choices=available_languages(), default="en")
    parser.add_argument("--screenshot-out", type=Path)
    parser.add_argument("--screenshot-size", type=parse_size, default=QSize(1440, 900))
    parser.add_argument("--exit-after-ms", type=int, default=0)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
    apply_windows_app_id()
    app = QApplication.instance() or QApplication(sys.argv[:1])
    app.setStyleSheet(QSS)
    app.setWindowIcon(create_app_icon())
    window = CockpitWindow(Path(args.project_root), language=args.language, screenshot_out=args.screenshot_out)
    app.aboutToQuit.connect(window._shutdown_update_thread)
    window.resize(args.screenshot_size)
    window.show()
    if args.screenshot_out:
        QTimer.singleShot(max(args.exit_after_ms, 450), window.save_screenshot_and_quit)
    elif args.exit_after_ms:
        QTimer.singleShot(args.exit_after_ms, app.quit)
    return int(app.exec())
