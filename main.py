import sys
import os
import json
import requests
import webbrowser
from datetime import datetime
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTextEdit, QPushButton, QComboBox, QCheckBox,
                             QLabel, QMessageBox, QFileDialog, QDialog, QRadioButton, QListView)
from PyQt6.QtCore import Qt, QEvent, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QShortcut, QKeySequence
from deep_translator import GoogleTranslator
import database
import pdf_generator

# --- SYSTEM FOLDER HANDLING ---
APP_DIR = os.path.expanduser("~/.LanguageLearnerPro")
os.makedirs(APP_DIR, exist_ok=True)
CONFIG_FILE = os.path.join(APP_DIR, "config.json")

# --- BACKGROUND THREAD WORKER ---
class TranslationWorker(QThread):
    # Signals to talk back to the main UI without crashing it
    finished = pyqtSignal(str, str) 
    error = pyqtSignal(str)

    def __init__(self, text, source_code, target_code, target_lang_name, needs_translit):
        super().__init__()
        self.text = text
        self.source_code = source_code
        self.target_code = target_code
        self.target_lang_name = target_lang_name
        self.needs_translit = needs_translit

    def run(self):
        # All the heavy internet requests happen here in the background!
        try:
            translator = GoogleTranslator(source=self.source_code, target=self.target_code)
            final_output = translator.translate(self.text)
            
            # Phonetic Transliteration
            if self.needs_translit and self.target_lang_name in ["🇷🇺 Russian", "🇪🇬 Arabic (Egyptian)", "🇮🇷 Persian"]:
                try:
                    url = "https://translate.googleapis.com/translate_a/single"
                    params = {
                        "client": "gtx", "sl": self.source_code, "tl": self.target_code,
                        "hl": "en", "dt": ["t", "rm"], "q": self.text
                    }
                    res = requests.get(url, params=params, timeout=3)
                    data = res.json()
                    if data and data[0] and len(data[0]) > 0:
                        pronunciation = " ".join(chunk[2] for chunk in data[0] if chunk and len(chunk) > 2 and chunk[2])                        
                        if pronunciation:
                            final_output += f"\n\n[Pronunciation: {pronunciation}]"
                except Exception:
                    pass 
            
            # Noun Article Check (RESTRICTED TO GERMAN)
            if len(self.text.split()) == 1 and self.target_lang_name == "🇩🇪 German":
                en_word = GoogleTranslator(source=self.source_code, target='en').translate(self.text)
                is_noun = False
                try:
                    response = requests.get(f"https://api.datamuse.com/words?sp={en_word}&md=p&max=1", timeout=2)
                    data = response.json()
                    if data and 'tags' in data[0] and len(data[0]['tags']) > 0 and data[0]['tags'][0] == 'n':
                        is_noun = True
                except:
                    pass
                
                if is_noun and not en_word.lower().startswith("the "):
                    en_phrase = f"the {en_word}"
                    translated_with_article = GoogleTranslator(source='en', target=self.target_code).translate(en_phrase)
                    final_output += f"\n\n[With Article: {translated_with_article}]"
            
            # Send the result back to the UI
            self.finished.emit(self.text, final_output)
            
        except Exception as e:
            self.error.emit(str(e))

class LanguageLearnerUI(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # --- APP VERSION ---
        self.current_version = "v1.1.0" 
        
        self.session_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.db_name = os.path.join(APP_DIR, f"session_{self.session_time}.db")
        database.init_db(self.db_name)
        
        self.is_dark_mode = False
        self.pdf_export_path = ""
        self.pdf_layout = "1_column" 
        
        self.load_or_request_path()
        
        self.init_ui()
        self.apply_theme()

    def load_or_request_path(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                    saved_path = config.get("pdf_path", "")
                    self.pdf_layout = config.get("pdf_layout", "1_column") 
                    if os.path.exists(saved_path):
                        self.pdf_export_path = saved_path
                        return
            except Exception:
                pass 

        self.change_export_path(is_startup=True)

    def change_export_path(self, is_startup=False):
        dialog_title = "Select Folder to Save PDFs" if not is_startup else "MANDATORY: Select a folder to save your PDF exports"
        folder = QFileDialog.getExistingDirectory(self, dialog_title)
        
        if folder:
            self.pdf_export_path = folder
            with open(CONFIG_FILE, 'w') as f:
                json.dump({"pdf_path": self.pdf_export_path, "pdf_layout": self.pdf_layout}, f)
            
            if not is_startup:
                QMessageBox.information(self, "Path Updated", f"PDFs will now be saved to:\n{self.pdf_export_path}")
        else:
            if is_startup:
                default_dir = os.path.expanduser("~/Documents")
                self.pdf_export_path = default_dir
                QMessageBox.warning(self, "Default Path Set", f"No path selected. PDFs will default to:\n{default_dir}")

    def check_for_updates(self):
        """Pings the GitHub API to see if a newer version exists."""
        try:
            url = "https://api.github.com/repos/vasif-asadov1/language-learner/releases/latest"
            response = requests.get(url, timeout=3)
            response.raise_for_status()
            
            latest_version = response.json().get("tag_name")
            release_url = response.json().get("html_url")
            
            if latest_version and latest_version != self.current_version:
                msg = QMessageBox(self)
                msg.setWindowTitle("Update Available!")
                msg.setText(f"Great news! A new version ({latest_version}) is available.\nYou are currently running {self.current_version}.")
                msg.setInformativeText("Would you like to download the new version now?")
                msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                
                if msg.exec() == QMessageBox.StandardButton.Yes:
                    webbrowser.open(release_url) # Opens their default browser to your download page
            else:
                QMessageBox.information(self, "Up to Date", f"You are running the latest version! ({self.current_version})")
                
        except Exception as e:
            QMessageBox.warning(self, "Update Check Failed", "Could not connect to GitHub to check for updates. Check your internet connection.")

    def open_layout_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("PDF Page Layout")
        dialog.setFixedSize(350, 150)
        
        layout = QVBoxLayout(dialog)
        
        lbl = QLabel("Choose your PDF export format:")
        layout.addWidget(lbl)
        
        radio_1 = QRadioButton("1 Column (Stacked)")
        radio_2 = QRadioButton("2 Columns (Left: Original | Right: Translation)")
        
        if self.pdf_layout == "2_column":
            radio_2.setChecked(True)
        else:
            radio_1.setChecked(True)
            
        layout.addWidget(radio_1)
        layout.addWidget(radio_2)
        
        btn_save = QPushButton("SAVE")
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        
        if self.is_dark_mode:
            btn_save.setStyleSheet("background-color: #0078D7; color: #ffffff; border: none; border-radius: 6px; padding: 6px 14px; font-weight: bold;")
        else:
            btn_save.setStyleSheet("background-color: #2563eb; color: #ffffff; border: none; border-radius: 6px; padding: 6px 14px; font-weight: bold;")

        btn_save.clicked.connect(dialog.accept)
        layout.addWidget(btn_save)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.pdf_layout = "2_column" if radio_2.isChecked() else "1_column"
            
            try:
                with open(CONFIG_FILE, 'r') as f:
                    config = json.load(f)
            except Exception:
                config = {}
            
            config["pdf_layout"] = self.pdf_layout
            config["pdf_path"] = self.pdf_export_path
            
            with open(CONFIG_FILE, 'w') as f:
                json.dump(config, f)

    def init_ui(self):
        self.setWindowTitle(f"Language Learner Pro - {self.current_version}")
        self.resize(1000, 600)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        top_bar = QHBoxLayout()

        # --- UNIFIED LANGUAGE MAP ---
        self.lang_map = {
            "🇪🇬 Arabic (Egyptian)": "ar",
            "🇦🇿 Azerbaijani": "az",
            "🇬🇧 English": "en",
            "🇫🇷 French": "fr",
            "🇩🇪 German": "de",
            "🇮🇹 Italian": "it",
            "🇮🇷 Persian": "fa",
            "🇵🇹 Portuguese": "pt",
            "🇷🇺 Russian": "ru",
            "🇪🇸 Spanish": "es",
            "🇹🇷 Turkish": "tr"
        }
        
        self.source_lang_combo = QComboBox()
        self.source_lang_combo.setView(QListView())
        self.source_lang_combo.addItem("🔍 Auto Detect")
        self.source_lang_combo.addItems(self.lang_map.keys())
        
        self.target_lang_combo = QComboBox()
        self.target_lang_combo.setView(QListView())
        self.target_lang_combo.addItems(self.lang_map.keys())
        self.target_lang_combo.setCurrentText("🇩🇪 German")
        
        top_bar.addWidget(QLabel("Original Language:"))
        top_bar.addWidget(self.source_lang_combo)
        top_bar.addStretch()
        top_bar.addWidget(QLabel("Translated Language:"))
        top_bar.addWidget(self.target_lang_combo)
        
        # --- DYNAMIC PRONUNCIATION SWITCH ---
        self.translit_checkbox = QCheckBox("Show Pronunciation")
        self.translit_checkbox.setCursor(Qt.CursorShape.PointingHandCursor)
        top_bar.addWidget(self.translit_checkbox)
        
        # Connect the language dropdown to our new visibility function
        self.target_lang_combo.currentTextChanged.connect(self.update_translit_visibility)
        self.update_translit_visibility(self.target_lang_combo.currentText()) # Set initial state

        # --- NEW FONT SIZE SELECTOR ---
        top_bar.addSpacing(10)
        top_bar.addWidget(QLabel("Font:"))
        
        self.font_size_combo = QComboBox()
        # self.font_size_combo.setView(QListView())
        self.font_size_combo.addItems([f"{i}pt" for i in range(10, 30)]) # Generates 10pt to 29pt
        self.font_size_combo.setCurrentText("14pt") # Set standard default
        self.font_size_combo.setMaxVisibleItems(8)
        self.font_size_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.font_size_combo.currentTextChanged.connect(self.change_font_size)
        top_bar.addWidget(self.font_size_combo)
        
        top_bar.addSpacing(20)
        
        # --- UPDATE BUTTON ---
        self.btn_update = QPushButton("🔄 Check Update")
        self.btn_update.setObjectName("btn_update") # <--- ADD THIS LINE
        self.btn_update.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_update.clicked.connect(self.check_for_updates)
        top_bar.addWidget(self.btn_update)
        
        self.btn_theme = QPushButton("🌙 Dark Mode")
        self.btn_theme.setObjectName("btn_theme")   # <--- ADD THIS LINE
        self.btn_theme.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_theme.clicked.connect(self.toggle_theme)
        top_bar.addWidget(self.btn_theme)
        
        main_layout.addLayout(top_bar)
        
        text_layout = QHBoxLayout()
        
        self.input_text = QTextEdit()
        self.input_text.setFont(QFont("Arial", 14))
        self.input_text.setPlaceholderText("Type your sentence here...\n(Press 'Shift + Enter' or click 'ENTER' to translate)")
        self.input_text.installEventFilter(self)
        
        self.output_text = QTextEdit()
        self.output_text.setFont(QFont("Arial", 14))
        self.output_text.setReadOnly(True)
        
        text_layout.addWidget(self.input_text)
        text_layout.addWidget(self.output_text)
        main_layout.addLayout(text_layout)
        
        button_layout = QHBoxLayout()
        
        btn_enter = QPushButton("ENTER")
        btn_enter.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_enter.clicked.connect(self.translate_text)

        btn_synonyms = QPushButton("SYNONYMS")
        btn_synonyms.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_synonyms.clicked.connect(self.get_synonyms)
        
        btn_clear = QPushButton("CLEAR HISTORY")
        btn_clear.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_clear.clicked.connect(self.clear_history)
        
        btn_delete_last = QPushButton("DELETE LAST")
        btn_delete_last.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_delete_last.clicked.connect(self.delete_last)
        
        btn_path = QPushButton("PATH")
        btn_path.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_path.clicked.connect(lambda: self.change_export_path(is_startup=False))
        
        btn_layout = QPushButton("LAYOUT")
        btn_layout.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_layout.clicked.connect(self.open_layout_dialog)
        
        btn_pdf = QPushButton("PDF")
        btn_pdf.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_pdf.clicked.connect(self.generate_pdf)
        
        button_layout.addWidget(btn_enter)
        button_layout.addWidget(btn_synonyms)
        button_layout.addWidget(btn_clear)
        button_layout.addWidget(btn_delete_last)
        button_layout.addWidget(btn_path)
        button_layout.addWidget(btn_layout)
        button_layout.addStretch()
        button_layout.addWidget(btn_pdf)
        
        main_layout.addLayout(button_layout)

        self.shortcut_pdf = QShortcut(QKeySequence("Ctrl+Shift+E"), self)
        self.shortcut_pdf.activated.connect(self.generate_pdf)

    def toggle_theme(self):
        self.is_dark_mode = not self.is_dark_mode
        self.apply_theme()

    def update_translit_visibility(self, lang_name):
        """Shows the pronunciation checkbox ONLY for supported languages."""
        supported_langs = ["🇷🇺 Russian", "🇪🇬 Arabic (Egyptian)", "🇮🇷 Persian"]
        if lang_name in supported_langs:
            self.translit_checkbox.setVisible(True)
            self.translit_checkbox.setChecked(True) # Default to ON when it appears
        else:
            self.translit_checkbox.setVisible(False)

    def change_font_size(self, size_str):
        """Synchronously updates the font size for both input and output windows."""
        # Extract the integer from the string (e.g., "14pt" -> 14)
        size = int(size_str.replace("pt", ""))
        
        # Apply the new font size to both text boxes instantly
        new_font = QFont("Arial", size)
        self.input_text.setFont(new_font)
        self.output_text.setFont(new_font)

    def apply_theme(self):
        """
        Applies a premium, modern UI theme (Tailwind CSS color palette).
        Explicitly targets QListView to bypass KDE Plasma's native window manager overrides.
        """
        
        # ---------------------------------------------------------
        # SHARED STYLES: Custom sleek scrollbars for both themes
        # ---------------------------------------------------------
        scrollbar_style = """
            QScrollBar:vertical {
                border: none;
                background: transparent;
                width: 8px;
                margin: 2px;
            }
            QScrollBar::handle:vertical {
                background: rgba(150, 150, 150, 0.4);
                min-height: 40px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(150, 150, 150, 0.7);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical, 
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                height: 0px; 
                background: none;
            }
        """

        if self.is_dark_mode:
            self.btn_theme.setText("☀️ Light Mode")
            self.setStyleSheet(scrollbar_style + """
                /* MAIN WINDOW & TEXT AREAS */
                QMainWindow, QWidget { 
                    background-color: #0F172A; /* Deep Slate */
                    color: #F8FAFC; 
                    font-family: 'Inter', 'Segoe UI', sans-serif;
                }
                QTextEdit { 
                    background-color: #1E293B; 
                    color: #F1F5F9; 
                    border: 1px solid #334155; 
                    border-radius: 12px; 
                    padding: 16px; 
                    line-height: 1.6;
                }
                QTextEdit:focus {
                    border: 1px solid #6366F1; /* Indigo focus ring */
                }

                /* PRIMARY BUTTONS (Gradients) */
                QPushButton { 
                    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #4F46E5, stop:1 #6366F1); 
                    color: white; 
                    border: none; 
                    border-radius: 8px; 
                    padding: 10px 18px; 
                    font-weight: bold; 
                    font-size: 13px; 
                }
                QPushButton:hover { 
                    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #4338CA, stop:1 #4F46E5); 
                }
                QPushButton:pressed { 
                    background-color: #3730A3; 
                }
                
                /* SECONDARY BUTTONS (Top Bar) */
                QPushButton#btn_theme, QPushButton#btn_update { 
                    background-color: #334155; 
                    color: #F8FAFC;
                    border: 1px solid #475569;
                }
                QPushButton#btn_theme:hover, QPushButton#btn_update:hover { 
                    background-color: #475569; 
                }
                
                /* COMBO BOX (Dropdown Button) */
                QComboBox { 
                    background-color: #1E293B; 
                    color: #F8FAFC; 
                    border: 1px solid #475569; 
                    border-radius: 8px; 
                    padding: 8px 12px; 
                    font-weight: bold;
                }
                QComboBox::drop-down { 
                    border: none; 
                }
                
                /* COMBO BOX POPUP LIST (QListView Override for KDE) */
                QComboBox QListView {
                    background-color: #1E293B;
                    color: #F8FAFC;
                    border: 1px solid #475569;
                    border-radius: 6px;
                    outline: none; /* Removes dotted focus line */
                    padding: 4px;
                }
                QComboBox QListView::item {
                    min-height: 32px;
                    padding: 4px 8px;
                    border-radius: 4px; /* Rounds the hover highlight */
                }
                QComboBox QListView::item:selected, QComboBox QListView::item:hover {
                    background-color: #6366F1;
                    color: #FFFFFF;
                }
                
                /* POPUP DIALOGS & RADIO BUTTONS */
                QDialog { 
                    background-color: #0F172A; 
                }
                QRadioButton { 
                    color: #F8FAFC; 
                    font-size: 14px; 
                    padding: 4px; 
                }
                QRadioButton::indicator { 
                    width: 18px; 
                    height: 18px; 
                    border-radius: 9px; 
                    border: 2px solid #6366F1; 
                    background-color: transparent; 
                }
                QRadioButton::indicator:checked { 
                    background-color: #6366F1; 
                    border: 4px solid #0F172A; 
                }
                QLabel { 
                    font-weight: bold; 
                    color: #94A3B8; 
                }
            """)

        else:
            self.btn_theme.setText("🌙 Dark Mode")
            self.setStyleSheet(scrollbar_style + """
                /* MAIN WINDOW & TEXT AREAS */
                QMainWindow, QWidget { 
                    background-color: #F8FAFC; /* Clean Off-White */
                    color: #0F172A; 
                    font-family: 'Inter', 'Segoe UI', sans-serif;
                }
                QTextEdit { 
                    background-color: #FFFFFF; 
                    color: #1E293B; 
                    border: 1px solid #E2E8F0; 
                    border-radius: 12px; 
                    padding: 16px; 
                    line-height: 1.6;
                }
                QTextEdit:focus { 
                    border: 1px solid #6366F1; 
                }

                /* PRIMARY BUTTONS (Gradients) */
                QPushButton { 
                    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #4F46E5, stop:1 #6366F1);
                    color: white; 
                    border: none; 
                    border-radius: 8px; 
                    padding: 10px 18px; 
                    font-weight: bold; 
                    font-size: 13px;
                }
                QPushButton:hover { 
                    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #4338CA, stop:1 #4F46E5); 
                }
                QPushButton:pressed { 
                    background-color: #3730A3; 
                }
                
                /* SECONDARY BUTTONS (Top Bar) */
                QPushButton#btn_theme, QPushButton#btn_update { 
                    background-color: #FFFFFF; 
                    color: #334155;
                    border: 1px solid #CBD5E1;
                }
                QPushButton#btn_theme:hover, QPushButton#btn_update:hover { 
                    background-color: #F1F5F9; 
                }
                
                /* COMBO BOX (Dropdown Button) */
                QComboBox { 
                    background-color: #FFFFFF; 
                    color: #0F172A; 
                    border: 1px solid #CBD5E1; 
                    border-radius: 8px; 
                    padding: 8px 12px; 
                    font-weight: bold;
                }
                QComboBox::drop-down { 
                    border: none; 
                }
                
                /* COMBO BOX POPUP LIST (QListView Override for KDE) */
                QComboBox QListView {
                    background-color: #FFFFFF;
                    color: #0F172A;
                    border: 1px solid #CBD5E1;
                    border-radius: 6px;
                    outline: none; /* Removes dotted focus line */
                    padding: 4px;
                }
                QComboBox QListView::item {
                    min-height: 32px;
                    padding: 4px 8px;
                    border-radius: 4px; /* Rounds the hover highlight */
                }
                QComboBox QListView::item:selected, QComboBox QListView::item:hover {
                    background-color: #6366F1;
                    color: #FFFFFF;
                }
                
                /* POPUP DIALOGS & RADIO BUTTONS */
                QDialog { 
                    background-color: #F8FAFC; 
                }
                QRadioButton { 
                    color: #0F172A; 
                    font-size: 14px; 
                    padding: 4px; 
                }
                QRadioButton::indicator { 
                    width: 18px; 
                    height: 18px; 
                    border-radius: 9px; 
                    border: 2px solid #CBD5E1; 
                    background-color: #FFFFFF; 
                }
                QRadioButton::indicator:checked { 
                    background-color: #6366F1; 
                    border: 4px solid #FFFFFF; 
                }
                QLabel { 
                    font-weight: bold; 
                    color: #64748B; 
                }
            """)


    def translate_text(self):
        text = self.input_text.toPlainText().strip()
        if not text:
            return
            
        # Give the user instant visual feedback that the app is working
        self.output_text.setText("Translating in background...")
        self.input_text.setEnabled(False) # Prevent spam clicking
            
        target_lang_name = self.target_lang_combo.currentText()
        target_code = self.lang_map[target_lang_name]
        
        source_selection = self.source_lang_combo.currentText()
        source_code = 'auto' if source_selection == "🔍 Auto Detect" else self.lang_map[source_selection]
        
        needs_translit = hasattr(self, 'translit_checkbox') and self.translit_checkbox.isVisible() and self.translit_checkbox.isChecked()

        # Fire off the background thread!
        self.worker = TranslationWorker(text, source_code, target_code, target_lang_name, needs_translit)
        self.worker.finished.connect(self.on_translation_finished)
        self.worker.error.connect(self.on_translation_error)
        self.worker.start()

    # --- NEW THREAD HANDLERS ---
    def on_translation_finished(self, original_text, final_output):
        self.output_text.setText(final_output)
        database.save_translation(self.db_name, original_text, final_output)
        self.input_text.setEnabled(True)
        self.input_text.setFocus()

    def on_translation_error(self, error_msg):
        QMessageBox.critical(self, "Error", f"Translation failed.\n{error_msg}")
        self.output_text.setText("")
        self.input_text.setEnabled(True)
        self.input_text.setFocus()


    def get_synonyms(self):
        text = self.input_text.toPlainText().strip()
        if not text:
            return

        if len(text.split()) > 1:
            QMessageBox.warning(self, "Invalid Input", "The Synonyms feature is applicable for single words only.")
            return

        target_lang_name = self.target_lang_combo.currentText()
        target_code = self.lang_map[target_lang_name]
        
        source_selection = self.source_lang_combo.currentText()
        source_code = 'auto' if source_selection == "🔍 Auto Detect" else self.lang_map[source_selection]


        try:
            translator_to_en = GoogleTranslator(source=source_code, target='en')
            en_word = translator_to_en.translate(text)

            response = requests.get(f"https://api.datamuse.com/words?rel_syn={en_word}")
            data = response.json()

            if not data:
                self.output_text.setText(f"No synonyms found for '{text}'.")
                return

            en_synonyms = [item['word'] for item in data[:5]]
            translator_to_target = GoogleTranslator(source='en', target=target_code)
            
            final_text = f"Original Word: {text}\nSynonyms in {target_lang_name}:\n\n"
            for syn in en_synonyms:
                translated_syn = translator_to_target.translate(syn)
                final_text += f"• {translated_syn}\n"

            formatted_output = final_text.strip()
            self.output_text.setText(formatted_output)
            database.save_translation(self.db_name, f"[Synonyms] {text}", formatted_output)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to fetch synonyms.\n{str(e)}")

    def clear_history(self):
        import sqlite3
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute("DROP TABLE IF EXISTS history")
        conn.commit()
        conn.close()
        database.init_db(self.db_name)
        self.output_text.setText("History cleared.")

    def delete_last(self):
        database.delete_last_entry(self.db_name)
        self.output_text.setText("Last entry deleted from database.")

    def generate_pdf(self):
        try:
            export_time = datetime.now().strftime("%Y_%m_%d_%H_%M")
            pdf_filename = f"{export_time}.pdf"
            
            full_path = os.path.join(self.pdf_export_path, pdf_filename)
            
            success = pdf_generator.create_pdf(self.db_name, full_path, layout=self.pdf_layout)
            
            if success:
                self.output_text.setText(f"✓ PDF generated successfully!\n\nSaved safely in:\n{full_path}")
            else:
                self.output_text.setText("⚠️ Cannot generate PDF. The session history is empty.")
                
        except Exception as e:
            QMessageBox.critical(self, "PDF Export Error", f"Failed to generate PDF.\n{str(e)}")

    def eventFilter(self, source, event):
        if source is self.input_text and event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Return and event.modifiers() == Qt.KeyboardModifier.ShiftModifier:
                self.translate_text()
                return True 
        return super().eventFilter(source, event)

    def closeEvent(self, event):
        if os.path.exists(self.db_name):
            try:
                os.remove(self.db_name)
            except Exception:
                pass
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # CRITICAL FIX: Bypass native OS styling to force our custom CSS
    app.setStyle("Fusion") 
    
    window = LanguageLearnerUI()
    window.show()
    sys.exit(app.exec())