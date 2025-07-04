import os
import sys
import json
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLineEdit, QPushButton, QFileDialog, QLabel, QScrollArea, QGroupBox)
from PyQt6.QtCore import Qt
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

class SearchWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Text Search Tool")
        self.resize(800, 600)
        self.move(QGuiApplication.primaryScreen().geometry().center() - self.rect().center())
        
        # Central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Folder selection
        folder_layout = QHBoxLayout()
        self.folder_label = CopyableLineEdit("Not selected")
        self.folder_label.setReadOnly(True)
        self.choose_button = QPushButton("Choose Folder")
        self.choose_button.clicked.connect(self.choose_folder)
        folder_layout.addWidget(QLabel("Folder:"))
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

        # Scroll area for results
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)  # Отключаем горизонтальный скроллинг
        self.results_widget = QWidget()
        self.results_layout = QVBoxLayout(self.results_widget)
        self.scroll_area.setWidget(self.results_widget)
        layout.addWidget(self.scroll_area)

        # Установка папки по умолчанию (nier_json)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.folder_path = os.path.join(script_dir, "nier_json").replace('\\', '/')
        if os.path.exists(self.folder_path):
            self.folder_label.setText(os.path.basename(self.folder_path))
        else:
            self.folder_label.setText("nier_json not found")

    def choose_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder", "")
        if folder:
            self.folder_path = folder
            self.folder_label.setText(os.path.basename(folder))

    def search_phrase(self, phrase):
        found = False
        results = []
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
                            for item in data:
                                for key, value in item.items():
                                    if isinstance(value, str):
                                        clean_value = value.lower().translate(translator)
                                        if clean_value and clean_phrase in clean_value:
                                            if not found:
                                                found = True
                                            results.append((file_path, relative_path, item))
                    except Exception as e:
                        results.append((file_path, relative_path, {"error": f"Error reading {relative_path}: {str(e)}"}))
        
        if not found and not any("error" in r[2] for r in results):
            results.append((None, None, {"message": f"Phrase '{phrase}' not found in text files."}))
        
        return results

    def search(self):
        phrase = self.phrase_input.text().strip()
        if not phrase:
            # Очищаем результаты и показываем сообщение
            while self.results_layout.count():
                item = self.results_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            self.results_layout.addWidget(QLabel("Please enter a phrase to search."))
            return
        if not self.folder_path:
            while self.results_layout.count():
                item = self.results_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            self.results_layout.addWidget(QLabel("Please select a folder first."))
            return

        # Очищаем предыдущие результаты
        while self.results_layout.count():
            item = self.results_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        translator = str.maketrans("", "", string.punctuation)
        clean_phrase = phrase.lower().translate(translator)
        if not clean_phrase:
            self.results_layout.addWidget(QLabel("Phrase contains only punctuation. Please enter a valid phrase."))
            return

        results = self.search_phrase(clean_phrase)
        for file_path, relative_path, item in results:
            if "error" in item:
                label = QLabel(item["error"])
                label.setWordWrap(True)
                self.results_layout.addWidget(label)
            elif "message" in item:
                label = QLabel(item["message"])
                label.setWordWrap(True)
                self.results_layout.addWidget(label)
            else:
                # Используем QGroupBox для каждого блока
                group_box = QGroupBox(f"File: {relative_path}")
                group_box.mousePressEvent = lambda event, rp=relative_path, it=item: self.copy_path(event, rp, it)
                layout = QVBoxLayout(group_box)
                for key, value in item.items():
                    label = QLabel(f"{key}: {value}")
                    label.setWordWrap(True)  # Включаем перенос текста
                    layout.addWidget(label)
                self.results_layout.addWidget(group_box)

        # Добавляем stretch в конец для прижатия к верху
        self.results_layout.addStretch()

    def copy_path(self, event, relative_path, item):
        if event.button() == Qt.MouseButton.RightButton:
            if relative_path and "wav" in item:
                # Удаляем "nier_audio_json/" с начала
                if relative_path.startswith("nier_audio_json/"):
                    relative_path = relative_path[15:]  # Удаляем первые 15 символов ("nier_audio_json/")
                # Удаляем ".json" с конца
                relative_path = relative_path.replace(".json", "")
                # Убираем ведущий слэш, если он есть
                relative_path = relative_path.lstrip('/')
                # Берем значение из поля "wav" и добавляем в конец
                wav_value = item["wav"]
                new_path = f"{relative_path}/{wav_value}"
                QApplication.clipboard().setText(new_path)
                event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SearchWindow()
    window.show()
    sys.exit(app.exec())