"""Qt style sheet for the native FlowPilot cockpit."""

from __future__ import annotations


QSS = """
* {
  font-family: "Segoe UI";
  font-size: 12px;
  color: #14212B;
}
QMainWindow, QDialog {
  background: #F6F8FA;
}
QFrame#topRail, QFrame#bottomRail {
  background: #FFFFFF;
  border: 1px solid #D8E0E5;
}
QFrame#rightInspector {
  background: #FFFFFF;
  border-left: 1px solid #D8E0E5;
}
QFrame#routePanel {
  background: #FDFEFE;
  border: 1px solid #D8E0E5;
}
QLabel#appTitle {
  font-size: 14px;
  font-weight: 600;
}
QLabel#panelTitle {
  font-size: 14px;
  font-weight: 600;
}
QLabel#muted {
  color: #60717D;
}
QLabel#liveBadge {
  color: #067987;
  font-weight: 600;
  padding: 4px 9px;
  border: 1px solid #A9DDE3;
  border-radius: 4px;
  background: #EAFBFD;
}
QPushButton {
  border: 1px solid #C9D4DA;
  border-radius: 5px;
  padding: 6px 10px;
  background: #FFFFFF;
}
QPushButton:hover {
  border-color: #0B8F9C;
  background: #F3FCFD;
}
QPushButton:pressed {
  background: #DDF5F7;
}
QPushButton#tabButton {
  border-radius: 0;
  border-top: none;
  border-left: none;
  border-right: 1px solid #D8E0E5;
  border-bottom: 2px solid transparent;
  min-height: 36px;
  padding-left: 14px;
  padding-right: 14px;
  text-align: left;
}
QPushButton#tabButton[selected="true"] {
  border-bottom: 3px solid #0B8F9C;
  background: #F7FEFF;
  font-weight: 600;
}
QPushButton#iconButton {
  min-width: 30px;
  padding: 6px;
}
QComboBox {
  border: 1px solid #C9D4DA;
  border-radius: 5px;
  padding: 5px 8px;
  background: #FFFFFF;
}
QTableWidget {
  background: #FFFFFF;
  border: none;
  gridline-color: #E5EAEE;
  selection-background-color: #EAFBFD;
  selection-color: #14212B;
}
QHeaderView::section {
  background: #F6F8FA;
  color: #60717D;
  border: none;
  border-bottom: 1px solid #D8E0E5;
  padding: 6px;
  font-weight: 600;
}
QScrollBar:vertical {
  background: #F6F8FA;
  width: 10px;
}
QScrollBar::handle:vertical {
  background: #B9C6CD;
  min-height: 24px;
  border-radius: 5px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
  height: 0px;
}
QDialog {
  border: 1px solid #D8E0E5;
}
"""
