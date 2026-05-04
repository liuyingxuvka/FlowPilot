"""Shared icon helpers for the FlowPilot cockpit."""

from __future__ import annotations

import ctypes
import sys

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap


ACCENT = QColor("#0FA37F")
CANVAS = QColor("#FDFEFE")


def apply_windows_app_id() -> None:
    """Give Windows one stable identity for taskbar and tray grouping."""
    if sys.platform != "win32":
        return
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("FlowPilot.Cockpit")
    except Exception:
        return


def create_app_icon() -> QIcon:
    """Create the single source icon used by window, taskbar, tray, and dialogs."""
    icon = QIcon()
    for size in (16, 24, 32, 64, 128, 256):
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        scale = size / 64.0
        pen = QPen(
            ACCENT,
            max(2, int(5 * scale)),
            Qt.PenStyle.SolidLine,
            Qt.PenCapStyle.RoundCap,
            Qt.PenJoinStyle.RoundJoin,
        )
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
