import os
import sys
import json
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QLineEdit, QPushButton, QFileDialog, 
                            QTextEdit, QLabel, QDialog, QFormLayout, 
                            QMessageBox, QScrollArea, QGridLayout, QSizePolicy, QSpacerItem)
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QGuiApplication
import string

class CopyableLineEdit(QLineEdit):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)  # Отключаем контекстное меню

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            text = self.text()
            if text:
                QApplication.clipboard().setText(text)
                event.accept()  # Предотвращаем дальнейшую обработку
        super().mousePressEvent(event)

class EditValuesWindow(QDialog):
    def __init__(self, parent, edit_data, base_folder):
        super().__init__(parent)
        self.setWindowTitle("Edit Values")
        self.resize(800, 600)
        self.move(QGuiApplication.primaryScreen().geometry().center() - self.rect().center())
        self.edit_data = edit_data
        self.modified_files = set()  # Множество для отслеживания изменённых файлов
        self.base_folder = base_folder

        # Основной grid layout
        self.grid_layout = QGridLayout(self)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)

        # Scroll area
        scroll = QScrollArea()
        scroll_content = QWidget()
        self.content_layout = QGridLayout(scroll_content)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        scroll.setWidget(scroll_content)
        scroll.setWidgetResizable(True)
        self.grid_layout.addWidget(scroll, 0, 0)

        # Создание динамических блоков для каждого результата
        self.file_blocks = {}
        row = 0
        for file_path, index, item, modified_item in edit_data:
            # Относительный путь файла как CopyableLineEdit с ReadOnly
            relative_path = os.path.relpath(file_path, self.base_folder).replace('\\', '/')
            file_edit = CopyableLineEdit(f"File: {relative_path}")
            file_edit.setReadOnly(True)
            self.content_layout.addWidget(file_edit, row, 0, 1, 1)
            row += 1

            # VBox для динамических строк
            vbox = QVBoxLayout()
            item_to_edit = modified_item if modified_item else item
            for key, value in item_to_edit.items():
                row_widget = self.create_row_widget(file_path, key, value, index)
                vbox.addWidget(row_widget)
            add_button = QPushButton("Add Element")
            add_button.clicked.connect(lambda checked, fp=file_path, idx=index, v=vbox: self.add_new_row_to_vbox(fp, idx, v))
            vbox.addWidget(add_button)
            vbox.addStretch()

            # Добавление VBox в контейнер
            container = QWidget()
            container.setLayout(vbox)
            self.content_layout.addWidget(container, row, 0, 1, 1)
            self.file_blocks[(file_path, index)] = vbox
            row += 1

        # Vertical spacer для прижатия к верху
        spacer = QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        self.content_layout.addItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding), row, 0, 1, 1)

        # Кнопка Save Changes
        self.save_button = QPushButton("Save Changes")
        self.save_button.clicked.connect(self.save_changes)
        self.grid_layout.addWidget(self.save_button, 1, 0)

        self.exec()

    def create_row_widget(self, file_path, key, value, index):
        row_widget = QWidget()
        grid_layout = QGridLayout(row_widget)
        grid_layout.setContentsMargins(0, 0, 0, 0)

        key_edit = CopyableLineEdit("en_voice" if not key else str(key))
        value_edit = CopyableLineEdit(str(value))
        delete_button = QPushButton("X")

        # Установка политик и растяжения
        size_policy_key = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        size_policy_key.setHorizontalStretch(2)
        key_edit.setSizePolicy(size_policy_key)

        size_policy_value = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        size_policy_value.setHorizontalStretch(8)
        value_edit.setSizePolicy(size_policy_value)

        delete_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        delete_button.setMaximumWidth(40)

        grid_layout.addWidget(key_edit, 0, 0)
        grid_layout.addWidget(value_edit, 0, 1)
        grid_layout.addWidget(delete_button, 0, 2)

        grid_layout.setColumnStretch(0, 2)  # Key LineEdit
        grid_layout.setColumnStretch(1, 8)  # Value LineEdit
        grid_layout.setColumnStretch(2, 0)  # Delete Button

        # Подключение сигнала textChanged для отслеживания изменений
        key_edit.textChanged.connect(lambda: self.mark_file_as_modified(file_path))
        value_edit.textChanged.connect(lambda: self.mark_file_as_modified(file_path))
        delete_button.clicked.connect(lambda checked, fp=file_path, k=key, idx=index, w=row_widget: self.delete_row_widget(fp, k, idx, w))

        self.edit_fields[(file_path, key, index)] = (key_edit, value_edit)
        return row_widget

    def add_new_row_to_vbox(self, file_path, index, vbox):
        new_key = f"new_key_{len(self.edit_fields)}"  # Для внутреннего использования
        row_widget = self.create_row_widget(file_path, "", "", index)  # Пустой ключ
        vbox.insertWidget(vbox.count() - 2, row_widget)  # -2 to insert before "Add Element" and stretch
        key_edit = row_widget.layout().itemAt(0).widget()
        value_edit = row_widget.layout().itemAt(1).widget()
        self.edit_fields[(file_path, new_key, index)] = (key_edit, value_edit)
        self.modified_files.add(file_path)  # Отмечаем файл как изменённый

    def delete_row_widget(self, file_path, key, index, row_widget):
        if (file_path, key, index) in self.edit_fields:
            del self.edit_fields[(file_path, key, index)]
            row_widget.setParent(None)
            row_widget.deleteLater()
            # Обновление modified_item для удаления ключа
            for i, (fp, idx, item, modified_item) in enumerate(self.edit_data):
                if fp == file_path and idx == index:
                    if modified_item is None:
                        modified_item = item.copy()
                        self.edit_data[i] = (fp, idx, item, modified_item)
                    if key in modified_item:
                        del modified_item[key]
                    self.modified_files.add(file_path)  # Отмечаем файл как изменённый
                    break

    def mark_file_as_modified(self, file_path):
        self.modified_files.add(file_path)

    def save_changes(self):
        reply = QMessageBox.question(self, "Confirm", "Save changes to JSON files?", 
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
                                    QMessageBox.StandardButton.NoButton)
        if reply == QMessageBox.StandardButton.Yes:
            # Очистка self.edit_fields от удалённых объектов
            valid_fields = {}
            for (fp, k, i), (kw, vw) in list(self.edit_fields.items()):
                try:
                    if kw.parent() is not None and vw.parent() is not None:
                        valid_fields[(fp, k, i)] = (kw, vw)
                except RuntimeError:
                    continue
            self.edit_fields.clear()
            self.edit_fields.update(valid_fields)

            for file_path, index, item, modified_item in self.edit_data:
                if file_path in self.modified_files:
                    if modified_item is None:
                        modified_item = item.copy()
                    # Удаление ключей, которые были удалены вручную
                    for (fp, k, i) in list(self.edit_fields.keys()):
                        if (fp, k, i) not in valid_fields and fp == file_path and i == index:
                            if k in modified_item:
                                del modified_item[k]
                    for (fp, key, idx), (key_widget, value_edit) in valid_fields.items():
                        if fp == file_path and idx == index:
                            new_key = key_widget.text().strip()
                            new_value = value_edit.text().strip()
                            if new_key and new_value:
                                modified_item[new_key] = new_value
                                print(f"Updating {file_path}: {new_key} = {new_value}")
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        if 0 <= index < len(data):
                            data[index] = modified_item
                            with open(file_path, 'w', encoding='utf-8') as f:
                                json.dump(data, f, ensure_ascii=False, indent=4)
                            print(f"Saved changes to {file_path}")
                    except Exception as e:
                        print(f"Error saving {file_path}: {str(e)}")
            self.accept()

    edit_fields = {}

class SearchWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Text Search Tool")
        self.resize(800, 600)
        self.move(QGuiApplication.primaryScreen().geometry().center() - self.rect().center())
        
        # Инициализация edit_data
        self.edit_data = []  # Добавляем инициализацию edit_data
        
        # Central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Folder selection
        folder_layout = QHBoxLayout()
        self.folder_label = QLabel("Folder: Not selected")
        self.choose_button = QPushButton("Choose Folder")
        self.choose_button.clicked.connect(self.choose_folder)
        folder_layout.addWidget(self.folder_label)
        folder_layout.addWidget(self.choose_button)
        layout.addLayout(folder_layout)

        # Phrase input
        phrase_layout = QHBoxLayout()
        self.phrase_input = QLineEdit()
        self.phrase_input.returnPressed.connect(self.search)  # Подключаем Enter к поиску
        self.search_button = QPushButton("Search")
        self.search_button.clicked.connect(self.search)
        phrase_layout.addWidget(QLabel("Phrase:"))
        phrase_layout.addWidget(self.phrase_input)
        phrase_layout.addWidget(self.search_button)
        layout.addLayout(phrase_layout)

        # Results display
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        layout.addWidget(self.results_text)

        # Edit and Clear buttons
        button_layout = QHBoxLayout()
        self.edit_button = QPushButton("Edit Values")
        self.edit_button.setEnabled(False)
        self.edit_button.clicked.connect(self.edit_values)
        button_layout.addWidget(self.edit_button)
        self.clear_button = QPushButton("Clear")
        self.clear_button.clicked.connect(self.clear_results)
        button_layout.addWidget(self.clear_button)
        layout.addLayout(button_layout)

        # Установка папки по умолчанию (nier_json)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.folder_path = os.path.join(script_dir, "nier_json").replace('\\', '/')
        if os.path.exists(self.folder_path):
            self.folder_label.setText(f"Folder: {self.folder_path}")
        else:
            self.folder_label.setText(f"Folder: nier_json not found")

    def choose_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder", "")
        if folder:
            self.folder_path = folder
            self.folder_label.setText(f"Folder: {folder}")

    def search_phrase(self, phrase):
        found = False
        results = []
        self.edit_data.clear()
        translator = str.maketrans("", "", string.punctuation)
        clean_phrase = phrase.lower().translate(translator)

        for root, _, files in os.walk(self.folder_path):
            for file in files:
                if file.endswith('.json'):
                    file_path = os.path.join(root, file).replace('\\', '/')
                    relative_path = os.path.relpath(file_path, self.folder_path).replace('\\', '/')
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            if not isinstance(data, list):
                                continue
                            for idx, item in enumerate(data):
                                for key, value in item.items():
                                    if isinstance(value, str):
                                        clean_value = value.lower().translate(translator)
                                        if clean_value and clean_phrase in clean_value:
                                            if not found:
                                                found = True
                                            result = f"File: {relative_path}\n"
                                            for k, v in item.items():
                                                result += f"{k}: {v}\n"
                                            result += f"{'-' * 50}\n"
                                            results.append(result)
                                            self.edit_data.append((file_path, idx, item, None))
                    except Exception as e:
                        results.append(f"Error reading {relative_path}: {str(e)}\n")
        
        if not found and not any("Error" in r for r in results):
            results.append(f"\nPhrase '{phrase}' not found in text files.\n")
        
        return results

    def search(self):
        phrase = self.phrase_input.text().strip()
        if not phrase:
            self.results_text.setText("Please enter a phrase to search.")
            return
        if not self.folder_path:
            self.results_text.setText("Please select a folder first.")
            return

        self.results_text.clear()
        self.edit_button.setEnabled(False)
        translator = str.maketrans("", "", string.punctuation)
        clean_phrase = phrase.lower().translate(translator)
        if not clean_phrase:
            self.results_text.setText("Phrase contains only punctuation. Please enter a valid phrase.")
            return

        results = self.search_phrase(clean_phrase)
        self.results_text.setText("".join(results))
        if self.edit_data:
            self.edit_button.setEnabled(True)

    def edit_values(self):
        if self.edit_data:
            EditValuesWindow(self, self.edit_data, self.folder_path)

    def clear_results(self):
        self.results_text.clear()
        self.edit_button.setEnabled(False)
        self.edit_data.clear()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SearchWindow()
    window.show()
    sys.exit(app.exec())