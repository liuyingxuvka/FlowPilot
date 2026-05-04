"""PySide6 native desktop UI for the FlowPilot cockpit."""

from __future__ import annotations

import argparse
import math
import os
import sys
from pathlib import Path

from PySide6.QtCore import QFileSystemWatcher, QPointF, QRectF, QSize, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QAction, QColor, QDesktopServices, QFont, QIcon, QMouseEvent, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import (
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

from .i18n import SUPPORT_URL, Translator, available_languages
from .models import CockpitSnapshot, NodeSummary
from .state_reader import FlowPilotStateReader
from .styles import QSS


ACCENT = QColor("#0B8F9C")
TEXT = QColor("#14212B")
MUTED = QColor("#60717D")
BORDER = QColor("#D8E0E5")
DIVIDER = QColor("#E5EAEE")
SURFACE = QColor("#FFFFFF")
CANVAS = QColor("#FDFEFE")
BG = QColor("#F6F8FA")
OK = QColor("#1E8E5A")
WARN = QColor("#B7791F")
ERROR = QColor("#B42318")
PENDING = QColor("#8A99A4")


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
}

RUN_TITLE_ZH = {
    "FlowPilot Windows desktop cockpit UI clean restart": "FlowPilot Windows 桌面驾驶舱 UI 全新重启",
    "FlowPilot Windows desktop cockpit UI from-scratch design": "FlowPilot Windows 桌面驾驶舱 UI 从零设计",
}

RUN_TAB_TITLES = {
    "en": {
        "FlowPilot Windows desktop cockpit UI clean restart": "Clean restart",
        "FlowPilot Windows desktop cockpit UI from-scratch design": "From-scratch design",
    },
    "zh": {
        "FlowPilot Windows desktop cockpit UI clean restart": "全新重启",
        "FlowPilot Windows desktop cockpit UI from-scratch design": "从零设计",
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


def create_app_icon() -> QIcon:
    icon = QIcon()
    for size in (16, 24, 32, 64, 128, 256):
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        scale = size / 64.0
        pen = QPen(ACCENT, max(2, int(5 * scale)), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.drawLine(QPointF(14 * scale, 44 * scale), QPointF(32 * scale, 26 * scale))
        painter.drawLine(QPointF(32 * scale, 26 * scale), QPointF(50 * scale, 16 * scale))
        painter.setBrush(ACCENT)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(14 * scale, 44 * scale), 7 * scale, 7 * scale)
        painter.drawEllipse(QPointF(50 * scale, 16 * scale), 7 * scale, 7 * scale)
        painter.setBrush(CANVAS)
        painter.setPen(QPen(ACCENT, max(2, int(5 * scale))))
        painter.drawEllipse(QPointF(32 * scale, 26 * scale), 10 * scale, 10 * scale)
        painter.end()
        icon.addPixmap(pixmap)
    return icon


class RouteCanvas(QWidget):
    node_selected = Signal(str)

    def __init__(self, translator: Translator, parent: QWidget | None = None):
        super().__init__(parent)
        self.translator = translator
        self.snapshot: CockpitSnapshot | None = None
        self.selected_node_id: str | None = None
        self._node_rects: dict[str, QRectF] = {}
        self._pulse = 0.0
        self._wrapped_layout = False
        self.setMinimumHeight(340)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMouseTracking(True)

    def sizeHint(self) -> QSize:
        return QSize(860, 460)

    def set_snapshot(self, snapshot: CockpitSnapshot, selected_node_id: str | None) -> None:
        self.snapshot = snapshot
        self.selected_node_id = selected_node_id
        self.update()

    def set_pulse(self, value: float) -> None:
        self._pulse = value
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
        self._draw_connections(painter, nodes)
        self._draw_timeline(painter, nodes)
        for node in nodes:
            node_rect = self._node_rects[node.node_id]
            self._draw_node(painter, node, node_rect)
        painter.end()

    def _draw_grid(self, painter: QPainter) -> None:
        painter.setPen(QPen(QColor("#EAF0F3"), 1))
        step = 24
        for x in range(0, self.width(), step):
            for y in range(0, self.height(), step):
                painter.drawPoint(x, y)

    def _layout_nodes(self, nodes: tuple[NodeSummary, ...]) -> dict[str, QRectF]:
        count = max(len(nodes), 1)
        width = max(self.width(), 500)
        height = max(self.height(), 300)
        margin_x = 36
        node_h = 62
        available_width = max(width - margin_x * 2, 1)
        rects: dict[str, QRectF] = {}
        natural_width = count * 154 + max(0, count - 1) * 18
        self._wrapped_layout = natural_width > available_width
        if not self._wrapped_layout:
            node_w = max(106, min(154, available_width / count - 14))
            available = max(width - margin_x * 2 - node_w, 1)
            y_base = height * 0.5 - node_h / 2
            for index, node in enumerate(nodes):
                x = margin_x if count == 1 else margin_x + (available * index / (count - 1))
                y_offset = 0
                if node.status in {"blocked", "failed", "error", "degraded", "warning"}:
                    y_offset = 54
                rects[node.node_id] = QRectF(x, y_base + y_offset, node_w, node_h)
            return rects

        if count <= 6:
            columns = max(3, math.ceil(count / 2))
        else:
            columns = max(3, min(count, int(available_width // 150) or 3))
        gap = 18
        node_w = max(112, min(154, (available_width - gap * (columns - 1)) / columns))
        rows = math.ceil(count / columns)
        total_h = rows * node_h + (rows - 1) * 58
        y_base = max(118, height * 0.5 - total_h / 2 + 32)
        for index, node in enumerate(nodes):
            row = index // columns
            col = index % columns
            x = margin_x + col * (node_w + gap)
            y = y_base + row * (node_h + 58)
            rects[node.node_id] = QRectF(x, y, node_w, node_h)
        return rects

    def _draw_connections(self, painter: QPainter, nodes: tuple[NodeSummary, ...]) -> None:
        for left, right in zip(nodes, nodes[1:]):
            a = self._node_rects[left.node_id]
            b = self._node_rects[right.node_id]
            start = QPointF(a.right(), a.center().y())
            end = QPointF(b.left(), b.center().y())
            current_path = left.status in {"complete", "completed", "succeeded", "running", "active", "in_progress"}
            pen = QPen(ACCENT if current_path else QColor("#AEBAC2"), 2.0)
            if not current_path:
                pen.setStyle(Qt.PenStyle.DashLine)
            painter.setPen(pen)
            path = QPainterPath(start)
            dx = max(30, (end.x() - start.x()) * 0.45)
            path.cubicTo(start.x() + dx, start.y(), end.x() - dx, end.y(), end.x(), end.y())
            painter.drawPath(path)

    def _draw_timeline(self, painter: QPainter, nodes: tuple[NodeSummary, ...]) -> None:
        y = 68
        if self._wrapped_layout:
            font = QFont("Segoe UI", 8)
            font.setBold(True)
            painter.setFont(font)
            for index, node in enumerate(nodes, start=1):
                rect = self._node_rects[node.node_id]
                color = status_color(node.status)
                painter.setPen(color)
                painter.drawText(QRectF(rect.left(), rect.top() - 30, rect.width(), 18), Qt.AlignmentFlag.AlignCenter, f"{index:02d}")
            return
        painter.setPen(QPen(DIVIDER, 1))
        painter.drawLine(28, y + 28, self.width() - 28, y + 28)
        font = QFont("Segoe UI", 8)
        font.setBold(True)
        painter.setFont(font)
        for index, node in enumerate(nodes, start=1):
            rect = self._node_rects[node.node_id]
            x = rect.center().x()
            color = status_color(node.status)
            painter.setPen(QPen(color, 1.8))
            painter.setBrush(CANVAS)
            painter.drawEllipse(QPointF(x, y + 28), 4.5, 4.5)
            painter.setPen(color)
            painter.drawText(QRectF(x - 14, y, 28, 18), Qt.AlignmentFlag.AlignCenter, f"{index:02d}")

    def _draw_node(self, painter: QPainter, node: NodeSummary, rect: QRectF) -> None:
        selected = node.node_id == self.selected_node_id
        active = self.snapshot is not None and node.node_id == self.snapshot.active_node_id
        color = status_color(node.status)
        if active:
            radius = 12 + 14 * (0.5 + 0.5 * math.sin(self._pulse * math.pi * 2))
            painter.setPen(QPen(QColor(11, 143, 156, 46), 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(rect.center(), radius, radius)

        painter.setPen(QPen(color if (selected or active) else BORDER, 2 if (selected or active) else 1))
        painter.setBrush(SURFACE)
        painter.drawRoundedRect(rect, 5, 5)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        painter.drawEllipse(QPointF(rect.left() + 18, rect.center().y()), 5, 5)

        painter.setPen(TEXT)
        title_font = QFont("Segoe UI", 8)
        title_font.setBold(active or selected)
        painter.setFont(title_font)
        title = painter.fontMetrics().elidedText(display_node_title(self.translator.language, node), Qt.TextElideMode.ElideRight, int(rect.width() - 42))
        painter.drawText(QRectF(rect.left() + 32, rect.top() + 10, rect.width() - 40, 18), Qt.AlignmentFlag.AlignLeft, title)

        painter.setFont(QFont("Segoe UI", 8))
        painter.setPen(MUTED)
        status = painter.fontMetrics().elidedText(self.translator.status(node.status), Qt.TextElideMode.ElideRight, int(rect.width() - 42))
        painter.drawText(QRectF(rect.left() + 32, rect.top() + 34, rect.width() - 40, 16), Qt.AlignmentFlag.AlignLeft, status)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        for node_id, rect in self._node_rects.items():
            if rect.contains(event.position()):
                self.selected_node_id = node_id
                self.node_selected.emit(node_id)
                self.update()
                return
        super().mousePressEvent(event)


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
        self.tab_layout.setContentsMargins(0, 0, 0, 0)
        self.tab_layout.setSpacing(0)
        top.addWidget(self.tab_container, 1)
        self.live_badge = QLabel()
        self.live_badge.setObjectName("liveBadge")
        top.addWidget(self.live_badge)
        self.language_combo = QComboBox()
        for language in available_languages():
            self.language_combo.addItem("EN" if language == "en" else "中文", language)
        self.language_combo.currentIndexChanged.connect(self._combo_language_changed)
        top.addWidget(self.language_combo)
        self.settings_button = QPushButton()
        self.settings_button.clicked.connect(self.open_settings)
        top.addWidget(self.settings_button)
        self.support_button = QPushButton()
        self.support_button.clicked.connect(self.open_support)
        top.addWidget(self.support_button)
        main.addWidget(self.top_rail)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(10, 10, 0, 0)
        left_layout.setSpacing(8)
        self.route_panel = QFrame()
        self.route_panel.setObjectName("routePanel")
        route_layout = QVBoxLayout(self.route_panel)
        route_layout.setContentsMargins(12, 10, 12, 10)
        route_header = QHBoxLayout()
        self.route_title = QLabel()
        self.route_title.setObjectName("panelTitle")
        self.route_meta = QLabel()
        self.route_meta.setObjectName("muted")
        route_header.addWidget(self.route_title)
        route_header.addStretch(1)
        route_header.addWidget(self.route_meta)
        route_layout.addLayout(route_header)
        self.canvas = RouteCanvas(self.translator)
        self.canvas.node_selected.connect(self._select_node)
        route_layout.addWidget(self.canvas, 1)
        left_layout.addWidget(self.route_panel, 1)

        self.events_panel = QFrame()
        self.events_panel.setObjectName("bottomRail")
        events_layout = QVBoxLayout(self.events_panel)
        events_layout.setContentsMargins(10, 8, 10, 8)
        events_header = QHBoxLayout()
        self.events_title = QLabel()
        self.events_title.setObjectName("panelTitle")
        self.watch_status = QLabel()
        self.watch_status.setObjectName("muted")
        events_header.addWidget(self.events_title)
        events_header.addStretch(1)
        events_header.addWidget(self.watch_status)
        events_layout.addLayout(events_header)
        self.events_table = QTableWidget(0, 5)
        self.events_table.verticalHeader().setVisible(False)
        self.events_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.events_table.setMinimumHeight(150)
        events_layout.addWidget(self.events_table)
        left_layout.addWidget(self.events_panel)
        splitter.addWidget(left)

        self.inspector = QFrame()
        self.inspector.setObjectName("rightInspector")
        inspector_layout = QVBoxLayout(self.inspector)
        inspector_layout.setContentsMargins(14, 12, 14, 12)
        inspector_layout.setSpacing(8)
        self.inspector_title = QLabel()
        self.inspector_title.setObjectName("panelTitle")
        self.node_title = QLabel()
        self.node_title.setWordWrap(True)
        self.node_title.setObjectName("panelTitle")
        self.node_status = QLabel()
        self.node_status.setObjectName("muted")
        self.meta_grid = QGridLayout()
        self.run_meta_label = QLabel()
        self.route_meta_label = QLabel()
        self.active_node_label = QLabel()
        self.workspace_label = QLabel()
        self.workspace_label.setWordWrap(True)
        for row, widget in enumerate((self.run_meta_label, self.route_meta_label, self.active_node_label, self.workspace_label)):
            self.meta_grid.addWidget(widget, row, 0)
        self.gates_title = QLabel()
        self.gates_title.setObjectName("panelTitle")
        self.gates_table = QTableWidget(0, 1)
        self.gates_table.verticalHeader().setVisible(False)
        self.gates_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.gates_table.setMaximumHeight(150)
        self.evidence_title = QLabel()
        self.evidence_title.setObjectName("panelTitle")
        self.evidence_table = QTableWidget(0, 3)
        self.evidence_table.verticalHeader().setVisible(False)
        self.evidence_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.findings_title = QLabel()
        self.findings_title.setObjectName("panelTitle")
        self.findings_label = QLabel()
        self.findings_label.setObjectName("muted")
        self.findings_label.setWordWrap(True)

        inspector_layout.addWidget(self.inspector_title)
        inspector_layout.addWidget(self.node_title)
        inspector_layout.addWidget(self.node_status)
        inspector_layout.addLayout(self.meta_grid)
        inspector_layout.addSpacing(8)
        inspector_layout.addWidget(self.gates_title)
        inspector_layout.addWidget(self.gates_table)
        inspector_layout.addWidget(self.evidence_title)
        inspector_layout.addWidget(self.evidence_table, 1)
        inspector_layout.addWidget(self.findings_title)
        inspector_layout.addWidget(self.findings_label)
        splitter.addWidget(self.inspector)
        splitter.setSizes([980, 340])
        main.addWidget(splitter, 1)

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
        self.live_badge.setText(t("live"))
        self.settings_button.setText(t("settings"))
        self.support_button.setText(t("support"))
        self.route_title.setText(t("route_canvas"))
        self.events_title.setText(t("freshness_events"))
        self.inspector_title.setText(t("node_inspector"))
        self.gates_title.setText(t("required_gates"))
        self.evidence_title.setText(t("evidence"))
        self.findings_title.setText(t("source_findings"))
        self.restore_action.setText(t("tray_restore"))
        self.exit_action.setText(t("tray_exit"))
        self.events_table.setHorizontalHeaderLabels([t("event_time"), t("event_level"), t("event_source"), t("event"), t("event_detail")])
        self.gates_table.setHorizontalHeaderLabels([t("required_gates")])
        self.evidence_table.setHorizontalHeaderLabels([t("event_source"), t("event"), t("status")])

    def update_snapshot(self) -> None:
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
        self.live_badge.setText(self.translator.t("source_ok") if self.snapshot.source_health == "ok" else self.translator.t("source_degraded"))
        self.canvas.set_snapshot(self.snapshot, self.selected_node_id)
        self._render_inspector()
        self._render_events()
        self.watch_status.setText(f"{self.translator.t('watching')}: {len(self.snapshot.watched_paths)} · {self.translator.t('auto_refresh')}")

    def _render_tabs(self) -> None:
        while self.tab_layout.count():
            item = self.tab_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        if not self.snapshot:
            return
        for run in self.snapshot.runs:
            title = self._run_tab_title(run.title)
            button = QPushButton(f"{self._status_dot(run.status)} {self._short_text(title, 26)}")
            button.setObjectName("tabButton")
            button.setProperty("selected", run.run_id == self.snapshot.selected_run_id)
            button.setToolTip(run.run_id)
            button.clicked.connect(lambda checked=False, run_id=run.run_id: self._select_run(run_id))
            button.style().unpolish(button)
            button.style().polish(button)
            self.tab_layout.addWidget(button)
        self.tab_layout.addStretch(1)

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

    def _run_tab_title(self, title: str) -> str:
        return RUN_TAB_TITLES.get(self.translator.language, {}).get(title, self._run_display_title(title))

    def _node_display_title(self, node: NodeSummary) -> str:
        return display_node_title(self.translator.language, node)

    def _select_run(self, run_id: str) -> None:
        self.selected_run_id = run_id
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
        self.node_title.setText(self._node_display_title(node))
        self.node_status.setText(f"{self.translator.t('status')}: {self.translator.status(node.status)}")
        run = self.snapshot.selected_run
        run_label = self._run_display_title(run.title) if run else "-"
        self.run_meta_label.setText(f"{self.translator.t('run')}: {run_label}")
        self.route_meta_label.setText(f"{self.translator.t('route')}: {self.snapshot.selected_route_id or '-'}")
        self.active_node_label.setText(f"{self.translator.t('active_node')}: {self.snapshot.active_node_id or '-'}")
        self.workspace_label.setText(f"{self.translator.t('workspace')}: {self.snapshot.workspace_root}")
        self._fill_single_column(self.gates_table, tuple(self._display_gate(value) for value in node.required_gates))
        self._fill_evidence_table()
        findings = "\n".join(self.snapshot.source_findings) if self.snapshot.source_findings else self.translator.t("no_findings")
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

    def _humanize(self, value: str) -> str:
        words = value.replace("-", "_").split("_")
        return " ".join(word.capitalize() if word.lower() not in {"ui", "i18n"} else word.upper() for word in words if word)

    def _display_gate(self, value: str) -> str:
        if self.translator.language == "zh":
            return GATE_ZH.get(value, self._humanize(value))
        return self._humanize(value)

    def _fill_evidence_table(self) -> None:
        if not self.snapshot:
            return
        self.evidence_table.setRowCount(len(self.snapshot.evidence))
        for row, event in enumerate(self.snapshot.evidence):
            for col, value in enumerate((event.source, event.event, event.level)):
                item = QTableWidgetItem(self.translator.t(value) if value in ("evidence_loaded", "current") else value)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.evidence_table.setItem(row, col, item)

    def _render_events(self) -> None:
        if not self.snapshot:
            return
        rows = list(self.snapshot.events)
        self.events_table.setRowCount(len(rows))
        for row, event in enumerate(rows):
            translated_event = self.translator.t(event.event)
            translated_level = self.translator.status(event.level) if event.level != "info" else self.translator.t("level_info")
            for col, value in enumerate((event.time_label, translated_level, event.source, translated_event, event.detail)):
                item = QTableWidgetItem(value)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.events_table.setItem(row, col, item)

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

    def show_from_tray(self) -> None:
        self.show()
        self.raise_()
        self.activateWindow()

    def exit_from_tray(self) -> None:
        self.force_exit = True
        self.tray.hide()
        QApplication.quit()

    def _tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_from_tray()

    def closeEvent(self, event) -> None:  # noqa: ANN001
        if self.force_exit:
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
    app = QApplication.instance() or QApplication(sys.argv[:1])
    app.setStyleSheet(QSS)
    app.setWindowIcon(create_app_icon())
    window = CockpitWindow(Path(args.project_root), language=args.language, screenshot_out=args.screenshot_out)
    window.resize(args.screenshot_size)
    window.show()
    if args.screenshot_out:
        QTimer.singleShot(max(args.exit_after_ms, 450), window.save_screenshot_and_quit)
    elif args.exit_after_ms:
        QTimer.singleShot(args.exit_after_ms, app.quit)
    return int(app.exec())
