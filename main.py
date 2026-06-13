import sys
import os
import json
import requests
from datetime import datetime
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTextEdit, QPushButton, QComboBox, 
                             QLabel, QMessageBox, QFileDialog)
from PyQt6.QtCore import Qt, QEvent
from PyQt6.QtGui import QFont, QShortcut, QKeySequence
from deep_translator import GoogleTranslator
import database
import pdf_generator

# --- NEW: SYSTEM FOLDER HANDLING ---
APP_DIR = os.path.expanduser("~/.LanguageLearnerPro")
os.makedirs(APP_DIR, exist_ok=True)
CONFIG_FILE = os.path.join(APP_DIR, "config.json")

class LanguageLearnerUI(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.session_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        # Lock the database to the hidden app folder
        self.db_name = os.path.join(APP_DIR, f"session_{self.session_time}.db")
        database.init_db(self.db_name)
        
        self.is_dark_mode = False
        self.pdf_export_path = ""
        
        self.load_or_request_path()
        
        self.init_ui()
        self.apply_theme()

    def load_or_request_path(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                    saved_path = config.get("pdf_path", "")
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
                json.dump({"pdf_path": self.pdf_export_path}, f)
            
            if not is_startup:
                QMessageBox.information(self, "Path Updated", f"PDFs will now be saved to:\n{self.pdf_export_path}")
        else:
            if is_startup:
                default_dir = os.path.expanduser("~/Documents")
                self.pdf_export_path = default_dir
                QMessageBox.warning(self, "Default Path Set", f"No path selected. PDFs will default to:\n{default_dir}")

    def init_ui(self):
        self.setWindowTitle("Language Learner Pro")
        self.resize(1000, 600)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        top_bar = QHBoxLayout()
        
        self.source_lang_combo = QComboBox()
        self.source_lang_combo.addItems(["Auto Detect", "Turkish", "English"])
        
        self.target_lang_combo = QComboBox()
        self.target_langs = {
            "German": "de",
            "Spanish": "es",
            "English": "en",
            "French": "fr",
            "Italian": "it"
        }
        self.target_lang_combo.addItems(self.target_langs.keys())
        
        top_bar.addWidget(QLabel("Original Language:"))
        top_bar.addWidget(self.source_lang_combo)
        top_bar.addStretch()
        top_bar.addWidget(QLabel("Translated Language:"))
        top_bar.addWidget(self.target_lang_combo)
        
        top_bar.addSpacing(20)
        self.btn_theme = QPushButton("🌙 Dark Mode")
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
        
        btn_pdf = QPushButton("PDF")
        btn_pdf.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_pdf.clicked.connect(self.generate_pdf)
        
        button_layout.addWidget(btn_enter)
        button_layout.addWidget(btn_synonyms)
        button_layout.addWidget(btn_clear)
        button_layout.addWidget(btn_delete_last)
        button_layout.addWidget(btn_path)
        button_layout.addStretch()
        button_layout.addWidget(btn_pdf)
        
        main_layout.addLayout(button_layout)

        self.shortcut_pdf = QShortcut(QKeySequence("Ctrl+Shift+E"), self)
        self.shortcut_pdf.activated.connect(self.generate_pdf)

    def toggle_theme(self):
        self.is_dark_mode = not self.is_dark_mode
        self.apply_theme()

    def apply_theme(self):
        if self.is_dark_mode:
            self.btn_theme.setText("☀️ Light Mode")
            self.setStyleSheet("""
                QMainWindow, QWidget { background-color: #2b2b2b; color: #e0e0e0; }
                QTextEdit { background-color: #1e1e1e; color: #ffffff; border: 1px solid #444; border-radius: 8px; padding: 10px; }
                QPushButton { background-color: #0078D7; color: #ffffff; border: none; border-radius: 6px; padding: 6px 14px; font-weight: bold; font-size: 12px; }
                QPushButton:hover { background-color: #005A9E; }
                QPushButton#btn_theme { background-color: #444; }
                QPushButton#btn_theme:hover { background-color: #555; }
                QComboBox { background-color: #3a3a3a; color: #ffffff; border: 1px solid #555; border-radius: 4px; padding: 4px; }
            """)
        else:
            self.btn_theme.setText("🌙 Dark Mode")
            self.setStyleSheet("""
                QMainWindow, QWidget { background-color: #f3f4f6; color: #1f2937; }
                QTextEdit { background-color: #ffffff; color: #111827; border: 1px solid #d1d5db; border-radius: 8px; padding: 10px; }
                QPushButton { background-color: #2563eb; color: #ffffff; border: none; border-radius: 6px; padding: 6px 14px; font-weight: bold; font-size: 12px; }
                QPushButton:hover { background-color: #1d4ed8; }
                QPushButton#btn_theme { background-color: #e5e7eb; color: #1f2937; }
                QPushButton#btn_theme:hover { background-color: #d1d5db; }
                QComboBox { background-color: #ffffff; color: #111827; border: 1px solid #d1d5db; border-radius: 4px; padding: 4px; }
            """)

    def translate_text(self):
        text = self.input_text.toPlainText().strip()
        if not text:
            return
            
        target_lang_name = self.target_lang_combo.currentText()
        target_code = self.target_langs[target_lang_name]
        
        source_selection = self.source_lang_combo.currentText()
        source_code = 'auto' if source_selection == "Auto Detect" else ("tr" if source_selection == "Turkish" else "en")
        
        try:
            translator = GoogleTranslator(source=source_code, target=target_code)
            translated = translator.translate(text)
            final_output = translated
            
            if len(text.split()) == 1:
                en_word = GoogleTranslator(source=source_code, target='en').translate(text)
                is_noun = False
                try:
                    response = requests.get(f"https://api.datamuse.com/words?sp={en_word}&md=p&max=1", timeout=2)
                    data = response.json()
                    if data and 'tags' in data[0] and 'n' in data[0]['tags']:
                        is_noun = True
                except:
                    pass
                
                if is_noun and not en_word.lower().startswith("the "):
                    en_phrase = f"the {en_word}"
                    translated_with_article = GoogleTranslator(source='en', target=target_code).translate(en_phrase)
                    final_output = f"{translated}\n\n[With Article: {translated_with_article}]"
            
            self.output_text.setText(final_output)
            database.save_translation(self.db_name, text, final_output)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Translation failed.\n{str(e)}")

    def get_synonyms(self):
        text = self.input_text.toPlainText().strip()
        if not text:
            return

        if len(text.split()) > 1:
            QMessageBox.warning(self, "Invalid Input", "The Synonyms feature is applicable for single words only.")
            return

        target_lang_name = self.target_lang_combo.currentText()
        target_code = self.target_langs[target_lang_name]
        
        source_selection = self.source_lang_combo.currentText()
        source_code = 'auto' if source_selection == "Auto Detect" else ("tr" if source_selection == "Turkish" else "en")

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
            pdf_filename = f"session_{self.session_time}.pdf"
            full_path = os.path.join(self.pdf_export_path, pdf_filename)
            
            success = pdf_generator.create_pdf(self.db_name, full_path)
            
            if success:
                self.output_text.setText(f"✓ PDF generated successfully!\n\nSaved safely in:\n{full_path}")
            else:
                self.output_text.setText("⚠️ Cannot generate PDF. The session history is empty.")
                
        except Exception as e:
            # If ANYTHING fails, keep the app open and show the error!
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
                # Removed the print statement so it stays completely silent
            except Exception:
                pass
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = LanguageLearnerUI()
    window.show()
    sys.exit(app.exec())