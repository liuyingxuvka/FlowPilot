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
QLabel#sectionTitle {
  color: #08785E;
  font-size: 12px;
  font-weight: 700;
  padding: 2px 0 2px 8px;
  border-left: 3px solid #0FA37F;
}
QLabel#nodeSummary {
  color: #14212B;
  font-size: 13px;
  font-weight: 600;
  background: #F6F8FA;
  border: 1px solid #E5EAEE;
  border-left: 3px solid #0FA37F;
  border-radius: 5px;
  padding: 8px 10px;
}
QLabel#metaLine {
  color: #60717D;
  font-size: 11px;
}
QLabel#nodeStatus {
  color: #08785E;
  font-size: 11px;
  font-weight: 600;
}
QLabel#muted {
  color: #60717D;
}
QLabel#sourceAlert {
  color: #8A4B00;
  font-weight: 600;
  padding: 4px 9px;
  border: 1px solid #E8C982;
  border-radius: 4px;
  background: #FFF7E6;
}
QLabel#statusSentence {
  color: #14212B;
  font-size: 13px;
  font-weight: 500;
  padding: 4px 2px;
}
QPushButton {
  border: 1px solid #C9D4DA;
  border-radius: 5px;
  padding: 6px 10px;
  background: #FFFFFF;
}
QPushButton:hover {
  border-color: #0FA37F;
  background: #F4FFFB;
}
QPushButton:pressed {
  background: #DDF8EE;
}
QFrame#tabPill {
  background: #FFFFFF;
  border: 1px solid #C9D4DA;
  border-radius: 8px;
}
QPushButton#tabButton {
  border-radius: 7px;
  border: none;
  min-height: 34px;
  padding-left: 10px;
  padding-right: 8px;
  text-align: left;
  background: transparent;
}
QFrame#tabPill[selected="true"] {
  border: 1px solid #0FA37F;
  background: #ECFFF8;
}
QFrame#tabPill[selected="true"] QPushButton#tabButton {
  font-weight: 600;
  background: transparent;
  color: #08785E;
}
QPushButton#tabCloseButton {
  border: none;
  border-radius: 10px;
  min-width: 22px;
  max-width: 22px;
  min-height: 22px;
  max-height: 22px;
  padding: 0;
  color: #60717D;
  background: transparent;
  font-weight: 600;
}
QPushButton#tabCloseButton:hover {
  color: #08785E;
  background: #DDF8EE;
}
QPushButton#iconButton, QPushButton#toolButton {
  min-width: 30px;
  padding: 5px 8px;
}
QPushButton#versionCapsule {
  color: #08785E;
  font-weight: 700;
  border: 1px solid #9EDBC8;
  border-radius: 10px;
  background: #ECFFF8;
  padding: 5px 10px;
}
QPushButton#versionCapsule[update="true"] {
  color: #7A2E0E;
  border-color: #F0A66C;
  background: #FFF0E6;
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
QSplitter::handle {
  background: #E5EAEE;
}
QSplitter::handle:hover {
  background: #9EDBC8;
}
QSplitter::handle:horizontal {
  width: 7px;
}
QSplitter::handle:vertical {
  height: 7px;
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
