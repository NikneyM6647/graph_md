import sys
from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QListWidgetItem, QPushButton, QLineEdit, QLabel,
    QDockWidget, QComboBox, QMessageBox, QTableWidget, QTableWidgetItem,
    QHeaderView,
)
from PySide6.QtWebEngineWidgets import QWebEngineView

import core


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Notes Graph")
        self.resize(1400, 900)

        self.records = []
        self.manual_links = {}
        self.current_name = None

        # ----- Центр: граф -----
        self.web = QWebEngineView()
        self.setCentralWidget(self.web)

        # ----- Левая панель: файлы -----
        self.files_dock = QDockWidget("Файлы", self)
        self.files_dock.setAllowedAreas(
            Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea
        )
        files_widget = QWidget()
        files_layout = QVBoxLayout(files_widget)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Поиск...")
        self.search.textChanged.connect(self.filter_files)

        self.file_list = QListWidget()
        self.file_list.itemSelectionChanged.connect(self.on_file_selected)

        files_layout.addWidget(self.search)
        files_layout.addWidget(self.file_list)
        self.files_dock.setWidget(files_widget)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.files_dock)

        # ----- Правая панель: детали и связи -----
        self.details_dock = QDockWidget("Детали и связи", self)
        details_widget = QWidget()
        details_layout = QVBoxLayout(details_widget)

        self.details_label = QLabel("Файл не выбран")
        self.details_label.setWordWrap(True)
        details_layout.addWidget(self.details_label)

        details_layout.addWidget(QLabel("Существующие связи:"))
        self.links_table = QTableWidget(0, 4)
        self.links_table.setHorizontalHeaderLabels(
            ["Куда", "Тип", "Заметка", ""]
        )
        self.links_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch
        )
        details_layout.addWidget(self.links_table)

        details_layout.addWidget(QLabel("Добавить связь:"))
        self.target_combo = QComboBox()
        self.type_combo = QComboBox()
        self.type_combo.addItems(
            ["related", "parent", "answer", "contradicts"]
        )
        self.note_edit = QLineEdit()
        self.note_edit.setPlaceholderText("Комментарий (необязательно)")

        add_btn = QPushButton("➕ Добавить связь")
        add_btn.clicked.connect(self.add_link)

        details_layout.addWidget(self.target_combo)
        details_layout.addWidget(self.type_combo)
        details_layout.addWidget(self.note_edit)
        details_layout.addWidget(add_btn)

        self.details_dock.setWidget(details_widget)
        self.addDockWidget(Qt.RightDockWidgetArea, self.details_dock)

        # ----- Меню -----
        self.build_menu()

        # ----- Статус-бар -----
        self.status = self.statusBar()

        # ----- Стартовая загрузка -----
        self.refresh()

    # ----- Меню -----
    def build_menu(self):
        menu = self.menuBar()

        file_menu = menu.addMenu("Файл")
        act_refresh = QAction("🔄 Пересканировать", self)
        act_refresh.setShortcut("F5")
        act_refresh.triggered.connect(self.refresh)
        file_menu.addAction(act_refresh)
        file_menu.addSeparator()
        act_exit = QAction("Выход", self)
        act_exit.setShortcut("Ctrl+Q")
        act_exit.triggered.connect(self.close)
        file_menu.addAction(act_exit)

        view_menu = menu.addMenu("Вид")
        view_menu.addAction(self.files_dock.toggleViewAction())
        view_menu.addAction(self.details_dock.toggleViewAction())

        links_menu = menu.addMenu("Связи")
        act_rebuild = QAction("Перестроить граф", self)
        act_rebuild.triggered.connect(self.rebuild_graph)
        links_menu.addAction(act_rebuild)

        help_menu = menu.addMenu("Помощь")
        act_about = QAction("О программе", self)
        act_about.triggered.connect(self.show_about)
        help_menu.addAction(act_about)

    def show_about(self):
        QMessageBox.information(
            self,
            "О программе",
            "Notes Graph\n\n"
            "Аналог графа Obsidian.\n"
            "Связи: [[wiki-ссылки]] и links.yaml",
        )

    # ----- Загрузка -----
    def refresh(self):
        self.records = core.scan_vault()
        self.manual_links = core.load_links_yaml()
        self.populate_files()
        self.populate_target_combo()
        self.rebuild_graph()
        total_links = sum(len(v) for v in self.manual_links.values())
        self.status.showMessage(
            f"Файлов: {len(self.records)}  ·  ручных связей: {total_links}"
        )

    def populate_files(self):
        self.file_list.clear()
        for r in self.records:
            item = QListWidgetItem(f"📄 {r['title']}")
            item.setData(Qt.UserRole, r["name"])
            item.setToolTip(r["name"])
            self.file_list.addItem(item)

    def filter_files(self, text):
        text = text.lower()
        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            item.setHidden(text not in item.text().lower())

    def populate_target_combo(self):
        self.target_combo.clear()
        for r in self.records:
            self.target_combo.addItem(r["name"], r["name"])

    # ----- Выбор файла -----
    def on_file_selected(self):
        items = self.file_list.selectedItems()
        if not items:
            return
        name = items[0].data(Qt.UserRole)
        record = next((r for r in self.records if r["name"] == name), None)
        if not record:
            return

        self.current_name = name
        wiki = ", ".join(record["links"]) or "—"
        self.details_label.setText(
            f"<b>{record['title']}</b><br>"
            f"<small>{record['name']}</small><br><br>"
            f"<b>Wiki-ссылки в тексте:</b> {wiki}"
        )
        self.refresh_links_table()

    def refresh_links_table(self):
        self.links_table.setRowCount(0)
        if not self.current_name:
            return

        links = self.manual_links.get(self.current_name, [])
        for i, t in enumerate(links):
            self.links_table.insertRow(i)
            self.links_table.setItem(i, 0, QTableWidgetItem(t["target"]))
            self.links_table.setItem(
                i, 1, QTableWidgetItem(t.get("type", "related"))
            )
            self.links_table.setItem(
                i, 2, QTableWidgetItem(t.get("note", ""))
            )
            btn = QPushButton("×")
            btn.setFixedWidth(30)
            btn.clicked.connect(lambda _, idx=i: self.delete_link(idx))
            self.links_table.setCellWidget(i, 3, btn)

    # ----- Связи -----
    def add_link(self):
        if not self.current_name:
            QMessageBox.warning(self, "Ошибка", "Сначала выбери файл слева")
            return

        target = self.target_combo.currentData()
        if target == self.current_name:
            QMessageBox.warning(self, "Ошибка", "Нельзя связать файл с самим собой")
            return

        ltype = self.type_combo.currentText()
        note = self.note_edit.text().strip()

        self.manual_links.setdefault(self.current_name, [])
        if any(t["target"] == target for t in self.manual_links[self.current_name]):
            QMessageBox.warning(self, "Ошибка", "Такая связь уже есть")
            return

        self.manual_links[self.current_name].append({
            "target": target,
            "type": ltype,
            "note": note,
        })
        core.save_links_yaml(self.manual_links)
        self.note_edit.clear()
        self.refresh_links_table()
        self.rebuild_graph()
        self.refresh_status()

    def delete_link(self, idx):
        if not self.current_name or self.current_name not in self.manual_links:
            return
        self.manual_links[self.current_name].pop(idx)
        if not self.manual_links[self.current_name]:
            del self.manual_links[self.current_name]
        core.save_links_yaml(self.manual_links)
        self.refresh_links_table()
        self.rebuild_graph()
        self.refresh_status()

    def refresh_status(self):
        total_links = sum(len(v) for v in self.manual_links.values())
        self.status.showMessage(
            f"Файлов: {len(self.records)}  ·  ручных связей: {total_links}"
        )

    # ----- Граф -----
    def rebuild_graph(self):
        G = core.build_graph(self.records, self.manual_links)
        html = core.render_graph_html(G)
        html_path = core.BASE / "_graph.html"
        html_path.write_text(html, encoding="utf-8")
        self.web.setUrl(QUrl.fromLocalFile(str(html_path)))


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()