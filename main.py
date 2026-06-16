import sys
import os
import json
import requests
import webbrowser
import re
from gtts import gTTS
import pygame
import tempfile
from datetime import datetime
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTextEdit, QPushButton, QComboBox, QCheckBox,
                             QLabel, QMessageBox, QFileDialog, QDialog, QRadioButton, QListView, QScrollArea)
from PyQt6.QtCore import Qt, QEvent, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QShortcut, QKeySequence, QIcon, QColor, QTextCharFormat
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
            
            # --- 1. BULLETPROOF NEWLINE PRESERVATION ---
            # Split by ANY sequence of newlines (\n, \n\n, \n\n\n)
            # This guarantees exact vertical visual symmetry.
            chunks = re.split(r'(\n+)', self.text)
            translated_chunks = []
            
            for chunk in chunks:
                if not chunk.strip():
                    # If it's just newlines or spaces, keep it exactly as is!
                    translated_chunks.append(chunk)
                else:
                    # Translate the actual text chunk
                    translated_chunks.append(translator.translate(chunk.strip()))
            
            # Re-join everything exactly as it was formatted
            final_output = ''.join(translated_chunks)
            
            # --- 2. PHONETIC TRANSLITERATION ---
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
            
            # --- 3. NOUN ARTICLE CHECK (GERMAN ONLY) ---
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
            
            # --- 4. SEND RESULT BACK TO UI ---
            self.finished.emit(self.text, final_output)
            
        except Exception as e:
            self.error.emit(str(e))


# --- BACKGROUND AUDIO WORKER ---
class AudioWorker(QThread):
    error = pyqtSignal(str)

    def __init__(self, text, lang_code):
        super().__init__()
        self.text = text
        self.lang_code = lang_code

    def run(self):
        try:
            # 1. Generate the audio file from Google
            tts = gTTS(text=self.text, lang=self.lang_code)
            
            # 2. Save it to a temporary folder
            temp_dir = tempfile.gettempdir()
            audio_path = os.path.join(temp_dir, "llp_audio.mp3")
            tts.save(audio_path)

            # 3. Play the audio using the pre-initialized mixer
            pygame.mixer.music.load(audio_path)
            pygame.mixer.music.play()
            
            # 4. Keep thread alive while playing
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
            
            
        except Exception as e:
            self.error.emit(str(e))



class LanguageLearnerUI(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # --- INITIALIZE AUDIO ENGINE ONCE ---
        pygame.mixer.init()
        
        # --- APP VERSION ---
        self.current_version = "v1.1.3"
        # --- APP VERSION ---
        self.current_version = "v1.1.3" 
        
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

    def open_github(self):
        """Opens the user's default web browser directly to the project repository."""
        webbrowser.open("https://github.com/vasif-asadov1/language-learner")

    def open_layout_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("PDF Page Layout")
        dialog.setFixedSize(350, 150)
        
        layout = QVBoxLayout(dialog)
        
        lbl = QLabel("Choose your PDF export format:")
        layout.addWidget(lbl)
        
        radio_1 = QRadioButton("1 Column Layout")
        radio_2 = QRadioButton("2 Columns Layout")
        
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
        self.setWindowIcon(QIcon("images/icon.png"))
        self.resize(1000, 600)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)
                
        top_bar_container = QWidget()
        top_bar_container.setObjectName("topBarCard")

        top_bar = QHBoxLayout(top_bar_container)

        top_bar.setContentsMargins(14, 10, 14, 10)
        top_bar.setSpacing(12)

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
        self.source_lang_combo.setMaxVisibleItems(6)
        self.source_lang_combo.setView(QListView())
        self.source_lang_combo.view().setVerticalScrollMode(
            QListView.ScrollMode.ScrollPerPixel
        )
        self.source_lang_combo.addItem("🔍 Auto Detect")
        self.source_lang_combo.addItems(self.lang_map.keys())
        
        self.target_lang_combo = QComboBox()
        self.target_lang_combo.setMaxVisibleItems(6)
        self.target_lang_combo.view().setVerticalScrollMode(
            QListView.ScrollMode.ScrollPerPixel
        )
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
        # top_bar.addWidget(self.translit_checkbox)
        
        # Connect the language dropdown to our new visibility function
        self.target_lang_combo.currentTextChanged.connect(self.update_translit_visibility)
        self.update_translit_visibility(self.target_lang_combo.currentText()) # Set initial state

        # --- NEW FONT SIZE SELECTOR ---
        top_bar.addSpacing(10)
        top_bar.addWidget(QLabel("Font:"))
        
        self.font_size_combo = QComboBox()
        self.font_size_combo.setObjectName("fontSelector")
        # self.font_size_combo.setView(QListView())
        self.font_size_combo.addItems([f"{i}pt" for i in range(10, 30)]) # Generates 10pt to 29pt
        self.font_size_combo.setCurrentText("14pt") # Set standard default
        self.font_size_combo.setMaxVisibleItems(8)
        self.font_size_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.font_size_combo.currentTextChanged.connect(self.change_font_size)
        top_bar.addWidget(self.font_size_combo)
        
        top_bar.addSpacing(20)
        
        # --- GITHUB BUTTON ---
        self.btn_github = QPushButton(" GitHub")
        self.btn_github.setObjectName("btn_github")
        self.btn_github.setIcon(QIcon("images/github.svg"))
        self.btn_github.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Professional Tooltip
        self.btn_github.setToolTip("Visit the official GitHub repository to view the source code and download the latest releases.")
        
        self.btn_github.clicked.connect(self.open_github)
        top_bar.addWidget(self.btn_github)
        
        self.btn_theme = QPushButton("🌙 Dark Mode")
        self.btn_theme.setObjectName("btn_theme")   # <--- ADD THIS LINE
        self.btn_theme.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_theme.clicked.connect(self.toggle_theme)
        top_bar.addWidget(self.btn_theme)
        
        main_layout.addWidget(top_bar_container)
        
        text_layout = QHBoxLayout()
        text_layout.setSpacing(10)
        
        self.input_text = QTextEdit()
        self.input_text.setFont(QFont("Arial", 14))
        self.input_text.setPlaceholderText("Type your sentence here...\n(Press 'Shift + Enter' or click 'ENTER' to translate)")
        self.input_text.installEventFilter(self)
        self.input_text.document().setDefaultStyleSheet("")
        
        
        self.output_text = QTextEdit()
        self.output_text.setFont(QFont("Arial", 14))
        self.output_text.setReadOnly(True)
        self.output_text.document().setDefaultStyleSheet("")
        self.output_text.installEventFilter(self)

        # --- NEW: FLOATING COPY BUTTONS ---
        self.btn_copy_in = QPushButton("📋", self.input_text)
        self.btn_copy_in.setObjectName("copyBtn")
        self.btn_copy_in.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_copy_in.setToolTip("Copy Original Text")
        self.btn_copy_in.clicked.connect(lambda: self.copy_to_clipboard(self.input_text, self.btn_copy_in))

        self.btn_copy_out = QPushButton("📋", self.output_text)
        self.btn_copy_out.setObjectName("copyBtn")
        self.btn_copy_out.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_copy_out.setToolTip("Copy Translated Text")
        self.btn_copy_out.clicked.connect(lambda: self.copy_to_clipboard(self.output_text, self.btn_copy_out))
        
        text_layout.addWidget(self.input_text)
        text_layout.addWidget(self.output_text)
        main_layout.addLayout(text_layout)

        self.input_text.currentCharFormatChanged.connect(self._enforce_input_color)
        
        action_bar = QWidget()
        action_bar.setObjectName("actionBar")

        button_layout = QHBoxLayout(action_bar)

        button_layout.setContentsMargins(12, 10, 12, 10)
        button_layout.setSpacing(8)
        
        btn_enter = QPushButton("ENTER")
        btn_enter.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_enter.setToolTip("Shift+Enter")
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

        # --- NEW CLEAR OUTPUT BUTTON ---
        btn_clear_output = QPushButton("CLEAR CANVAS")
        btn_clear_output.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_clear_output.setToolTip("Ctrl+Delete")
        btn_clear_output.clicked.connect(self.clear_output)
        
        btn_path = QPushButton("PATH")
        btn_path.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_path.clicked.connect(lambda: self.change_export_path(is_startup=False))
        
        btn_layout = QPushButton("LAYOUT")
        btn_layout.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_layout.clicked.connect(self.open_layout_dialog)

        # --- NEW HELP BUTTON ---
        btn_help = QPushButton("HELP")
        btn_help.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_help.clicked.connect(self.show_help_dialog)

        btn_play = QPushButton("🔊 PLAY")
        btn_play.setObjectName("playButton")
        btn_play.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_play.clicked.connect(self.play_audio)
        
        btn_pdf = QPushButton("PDF")
        btn_pdf.setObjectName("pdfButton")
        btn_pdf.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_pdf.setToolTip("Ctrl+Shift+E")
        btn_pdf.clicked.connect(self.generate_pdf)
        
        button_layout.addWidget(btn_enter)
        button_layout.addWidget(btn_synonyms)
        button_layout.addWidget(btn_clear)
        button_layout.addWidget(btn_delete_last)
        button_layout.addWidget(btn_clear_output)
        button_layout.addWidget(btn_path)
        button_layout.addWidget(btn_layout)
        button_layout.addWidget(btn_help)
        button_layout.addStretch()
        button_layout.addWidget(self.translit_checkbox)
        button_layout.addWidget(btn_play)
        button_layout.addWidget(btn_pdf)
        
        main_layout.addWidget(action_bar)

        self.shortcut_pdf = QShortcut(QKeySequence("Ctrl+Shift+E"), self)
        self.shortcut_pdf.activated.connect(self.generate_pdf)

        # --- CLEAR CANVAS SHORTCUT ---
        self.shortcut_clear = QShortcut(QKeySequence("Ctrl+Delete"), self)
        self.shortcut_clear.activated.connect(self.clear_output)

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

    def _enforce_input_color(self, fmt):
        """Prevents PyQt6 from inheriting old HTML span colors on new keystrokes."""
        target_color = QColor("#CBD5E1") if self.is_dark_mode else QColor("#2B2A28")
        if fmt.foreground().color() != target_color:
            correct_fmt = QTextCharFormat()
            correct_fmt.setForeground(target_color)
            # Block signal to avoid infinite loop
            self.input_text.blockSignals(True)
            self.input_text.mergeCurrentCharFormat(correct_fmt)
            self.input_text.blockSignals(False)

    def apply_theme(self):
        """
        Applies a premium, modern UI theme (Tailwind CSS color palette).
        Explicitly targets exact geometries to ensure pixel-perfect symmetry 
        between light and dark modes.
        """
        
        # ---------------------------------------------------------
        # SHARED STYLES: Custom sleek scrollbars for both themes
            # ---------------------------------------------------------
        dark = self.is_dark_mode
        input_color  = "#CBD5E1" if dark else "#2B2A28"   # soft blue-white
        output_color = "#67E8F9" if dark else "#2B2A28"   # calm cyan

        # Nuclear option: grab plain text, wipe document, rewrite with correct color
        input_plain  = self.input_text.toPlainText()
        output_plain = self.output_text.toPlainText()

        self.input_text.clear()
        self.output_text.clear()

        # Set the default char format BEFORE inserting text
        input_fmt = QTextCharFormat()
        input_fmt.setForeground(QColor(input_color))
        self.input_text.setCurrentCharFormat(input_fmt)

        output_fmt = QTextCharFormat()
        output_fmt.setForeground(QColor(output_color))
        self.output_text.setCurrentCharFormat(output_fmt)

        # Now insert — text will have the correct color baked in
        self.input_text.setPlainText(input_plain)
        self.output_text.setPlainText(output_plain)

        # Re-apply format after setPlainText (it resets cursor format)
        self.input_text.setCurrentCharFormat(input_fmt)
        self.output_text.setCurrentCharFormat(output_fmt)



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
            
            # fmt = QTextCharFormat()
            # fmt.setForeground(QColor("#D0DEDC"))

            # cursor = self.input_text.textCursor()
            # cursor.select(cursor.SelectionType.Document)
            # cursor.mergeCharFormat(fmt)

            # self.input_text.mergeCurrentCharFormat(fmt)

            # self.input_text.setTextColor(QColor("#D0DEDC"))
            # self.output_text.setTextColor(QColor("#D9E6FF"))



            self.btn_theme.setText("☀️ Light Mode")
            QApplication.instance().setStyleSheet(scrollbar_style + """
                /* MAIN WINDOW & TEXT AREAS */
                QMainWindow, QWidget { 
                    background-color: #071224;
                    color: #F8FAFC; 
                    font-family: 'Inter', 'Segoe UI', sans-serif;
                }

                /* --- NEW PREMIUM TOOLTIP --- */
                QToolTip {
                    background-color: #1E293B;
                    color: #94A3B8;
                    border: 1px solid #334155;
                    border-radius: 5px;
                    padding: 4px 8px;
                    font-family: 'Inter', 'Segoe UI', sans-serif;
                    font-size: 11px;
                    font-weight: bold;
                }

                QTextEdit {
                    background-color: #16284A;
                    color: #00F8D9;
                    border: 1px solid #2E4772;
                    border-radius: 22px;
                    padding: 24px;
                    line-height: 1.8;
                }
                                                  
                QPushButton#copyBtn {
                    background-color: transparent;
                    border: none;
                    font-size: 18px;
                    padding: 4px;
                    min-height: 0px;
                }
                QPushButton#copyBtn:hover {
                    background-color: #2E4772;
                    border-radius: 8px;
                }

                QTextEdit:focus {
                    border: 2px solid #6C72E8;
                }                              

                QTextEdit[placeholderText] {
                    color: #A7A093;
                }

                /* PRIMARY BUTTONS */
                QPushButton {
                    background-color: #424DA8;
                    color: #EAF0FF;
                    border: none;
                    border-radius: 10px;
                    padding: 10px 16px;
                    font-weight: bold;
                    font-size: 13px;
                    min-height: 22px;
                }

                QPushButton:hover {
                    background-color: #4D59BB;
                }

                QPushButton:pressed {
                    background-color: #37418F;
                }
                               
                /* SECONDARY BUTTONS (Top Bar) */
                               

                QPushButton#btn_theme, QPushButton#btn_github { 
                    background-color: #334155; 
                    color: #F8FAFC;
                    border: 1px solid #475569;
                }
                QPushButton#btn_theme:hover, QPushButton#btn_github:hover { 
                    background-color: #475569; 
                }
                
                /* COMBO BOX */
                QComboBox { 
                    background-color: #1E293B; 
                    color: #F8FAFC; 
                    border: 1px solid #475569; 
                    border-radius: 10px;
                    padding: 10px 14px;
                    font-weight: bold;
                    min-height: 22px;
                }
                QComboBox:hover {
                    background-color: #27344A;
                }
                QComboBox::drop-down { 
                    border: none; 
                    width: 26px;
                }
                
                /* COMBO BOX POPUP LIST */
                QAbstractItemView {
                    background-color: #1E293B;
                    color: #F8FAFC;
                    border: 1px solid #475569;
                    border-radius: 10px;
                    outline: none; 
                    padding: 8px;
                }
                QAbstractItemView::item {
                    min-height: 38px;
                    padding: 6px 10px;
                    border-radius: 8px; 
                }
                QAbstractItemView::item:selected, QAbstractItemView::item:hover {
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
                    font-weight: 600;
                    color: #B7C3D9;
                    background-color: #13213C;
                    border-radius: 8px;
                    padding: 6px 10px;
                }                              

                QWidget#topBarCard {
                    background-color: #0F1C34;
                    border: 1px solid #233654;
                    border-radius: 18px;
                }

                QWidget#actionBar {
                    background-color: #0F1C34;
                    border: 1px solid #233654;
                    border-radius: 18px;
                }

                QCheckBox {
                    background-color: #1D2B48;
                    border: 1px solid #304464;
                    border-radius: 10px;
                    padding: 10px 14px;
                    color: #F8FAFC;
                    font-weight: 600;
                    spacing: 8px;
                }

                QCheckBox::indicator {
                    width: 18px;
                    height: 18px;
                    border-radius: 5px;
                    border: 1px solid #4A5D84;
                    background-color: #16243F;
                }

                QCheckBox::indicator:checked {
                    background-color: #5B5CE2;
                    border: 1px solid #5B5CE2;
                }   

                /* ACTION BUTTONS (PDF & PLAY) */
                QPushButton#pdfButton {
                    background-color: #1D6A52;
                    color: #E8FFF6;
                    border: none;
                    border-radius: 10px;
                    padding: 10px 20px;
                    min-width: 90px;
                }
                QPushButton#pdfButton:hover {
                    background-color: #248164;
                }
                QPushButton#pdfButton:pressed {
                    background-color: #15503E;
                }

                QPushButton#playButton {
                    background-color: #2D3748; 
                    color: #A0AEC0; 
                    border: none;
                    border-radius: 10px;
                    padding: 10px 20px;
                    min-width: 90px; 
                }
                QPushButton#playButton:hover { 
                    background-color: #4A5568; 
                }
                QPushButton#playButton:pressed { 
                    background-color: #1A202C; 
                }
            """)

        else:

            
 
            # fmt = QTextCharFormat()
            # fmt.setForeground(QColor("#2B2A28"))

            # cursor = self.input_text.textCursor()
            # cursor.select(cursor.SelectionType.Document)
            # cursor.mergeCharFormat(fmt)

            # self.input_text.mergeCurrentCharFormat(fmt)

            # self.input_text.setTextColor(QColor("#2B2A28"))
            # self.output_text.setTextColor(QColor("#2B2A28"))


            self.btn_theme.setText("🌙 Dark Mode")
            QApplication.instance().setStyleSheet(scrollbar_style + """
                /* MAIN WINDOW & TEXT AREAS */
                QMainWindow, QWidget { 
                    background-color: #F5F3EE;
                    color: #0F172A; 
                    font-family: 'Inter', 'Segoe UI', sans-serif;
                }
                
                /* --- SLEEK COMPACT TOOLTIP (LIGHT) --- */
                QToolTip {
                    background-color: #FFFFFF;
                    color: #334155;
                    border: 1px solid #CBD5E1;
                    border-radius: 5px;
                    padding: 4px 8px;
                    font-family: 'Inter', 'Segoe UI', sans-serif;
                    font-size: 11px;
                    font-weight: bold;
                }
                               
                                                            
                QTextEdit {
                    background-color: #FEFDFC;
                    color: #2B2A28;
                    border: 1px solid #E4DFD4;
                    border-radius: 22px;
                    padding: 24px;
                    line-height: 1.8;
                }

                QTextEdit:focus {
                    border: 2px solid #8E97D6;
                }
                                            
                QWidget#topBarCard {
                    background-color: #FBF9F4;
                    border: 1px solid #DCD7CA;
                    border-radius: 18px;
                }

                QWidget#actionBar {
                    background-color: #F8F5EE;
                    border: 1px solid #D8D2C6;
                    border-radius: 18px;
                }
                               
                QComboBox#fontSelector {
                    background-color: #F5F4EF;
                    border: 1px solid #D9D4C8;
                }

                /* PRIMARY BUTTONS */
                QPushButton {
                    background-color: #737DB9;
                    color: white;
                    border: none;
                    border-radius: 10px;
                    padding: 10px 16px;
                    font-weight: bold;
                    font-size: 13px;
                    min-height: 22px;
                }

                QPushButton:hover {
                    background-color: #6772B0;
                }

                QPushButton:pressed {
                    background-color: #5A66A6;
                }

                /* SECONDARY BUTTONS (Top Bar) */
                               
                QPushButton#btn_theme, QPushButton#btn_github { 
                    background-color: #FFFFFF; 
                    color: #334155;
                    border: 1px solid #CBD5E1;
                }
                QPushButton#btn_theme:hover, QPushButton#btn_github:hover { 
                    background-color: #F1F5F9; 
                }
                                                  
                QPushButton#copyBtn {
                    background-color: transparent;
                    border: none;
                    font-size: 18px;
                    padding: 4px;
                    min-height: 0px;
                }
                QPushButton#copyBtn:hover {
                    background-color: #E4DFD4;
                    border-radius: 8px;
                }
                
                /* COMBO BOX */
                QComboBox {
                    background-color: #E9EEE4;
                    color: #2F2A24;
                    border: 1px solid #CBD3C1;
                    border-radius: 10px;
                    padding: 10px 14px;
                    font-weight: bold;
                    min-height: 22px;
                }
                QComboBox:hover {
                    background-color: #EEF2EA;
                }
                QComboBox::drop-down {
                    border: none;
                    width: 26px;
                }
 
                /* COMBO BOX POPUP LIST */
                QAbstractItemView {
                    background-color: #F8F5EE;
                    color: #2F2A24;
                    border: 1px solid #D7D1C5;
                    border-radius: 10px;
                    outline: none;
                    padding: 8px;
                }
                QAbstractItemView::item {
                    min-height: 38px;
                    padding: 6px 10px;
                    border-radius: 8px;
                }
                QAbstractItemView::item:selected, QAbstractItemView::item:hover {
                    background-color: #7E88C7;
                    color: white;
                }

                QCheckBox {
                    background-color: #F3F0E8;
                    border: 1px solid #D8D2C6; /* Added subtle border to match dark mode symmetry */
                    border-radius: 10px;
                    padding: 10px 14px;
                    color: #2F2A24;
                    font-weight: 600;
                    spacing: 8px;
                }

                QCheckBox::indicator {
                    width: 18px;
                    height: 18px;
                    border-radius: 5px;
                    border: 1px solid #CFC8BB;
                    background-color: #FFFFFF;
                }

                QCheckBox::indicator:checked {
                    background-color: #737DB9;
                    border: 1px solid #737DB9;
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
                    font-weight: 600;
                    color: #665D52;
                    background-color: #F3F0E8;
                    border-radius: 8px;
                    padding: 6px 10px;
                }
                               
                /* ACTION BUTTONS (PDF & PLAY) */
                QPushButton#pdfButton {
                    background-color: #BFD8C4;
                    color: #234234;
                    border: none;
                    border-radius: 10px;
                    padding: 10px 20px;
                    min-width: 90px;
                }
                QPushButton#pdfButton:hover {
                    background-color: #AED0B5;
                }
                QPushButton#pdfButton:pressed {
                    background-color: #98C5A1;
                }

                QPushButton#playButton {
                    background-color: #E2E2D9; 
                    color: #6B6A63; 
                    border: none;
                    border-radius: 10px;
                    padding: 10px 20px; 
                    min-width: 90px; 
                }
                QPushButton#playButton:hover { 
                    background-color: #D6D6CC; 
                }
                QPushButton#playButton:pressed { 
                    background-color: #C2C2B8; 
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
    # def on_translation_finished(self, original_text, final_output):
    #     self.output_text.setText(final_output)
    #     database.save_translation(self.db_name, original_text, final_output)
    #     self.input_text.setEnabled(True)
    #     self.input_text.setFocus()

    def on_translation_finished(self, original_text, final_output):
        self.output_text.setPlainText(final_output)
        
        # Re-apply current theme color so new text isn't colorless
        dark = self.is_dark_mode
        self.output_text.setTextColor(QColor("#67E8F9" if dark else "#2B2A28"))
        self.input_text.setTextColor(QColor("#CBD5E1" if dark else "#2B2A28"))
        
        database.save_translation(self.db_name, original_text, final_output)
        self.input_text.setEnabled(True)
        self.input_text.setFocus()

    def on_translation_error(self, error_msg):
        QMessageBox.critical(self, "Error", f"Translation failed.\n{error_msg}")
        self.output_text.setText("")
        self.input_text.setEnabled(True)
        self.input_text.setFocus()

    def play_audio(self):
        # Grab the raw text from the output box
        raw_text = self.output_text.toPlainText().strip()
        
        if not raw_text or "Translating in background" in raw_text or "No synonyms" in raw_text:
            return

        # CLEAN THE TEXT: Ignore [Pronunciation: ...] and [With Article: ...]
        clean_text = raw_text.split("\n\n[")[0].strip()
        
        # If the user used the Synonyms tool, the text is formatted with bullet points.
        # We just read the whole thing.
        if "Synonyms in" in clean_text:
            clean_text = clean_text.replace("Original Word:", "").replace("Synonyms in", "Synonyms")

        target_lang_name = self.target_lang_combo.currentText()
        target_code = self.lang_map[target_lang_name]

        # Fire off the audio thread!
        self.audio_worker = AudioWorker(clean_text, target_code)
        self.audio_worker.error.connect(lambda err: QMessageBox.warning(self, "Audio Error", f"Could not play audio:\n{err}"))
        self.audio_worker.start()


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

    def clear_output(self):
        """Clears the right-side translation area visually without affecting the database."""
        self.output_text.clear()

    def copy_to_clipboard(self, text_box, button):
        """Copies text to the clipboard and gives instant visual feedback."""
        text = text_box.toPlainText()
        if not text:
            return
            
        QApplication.clipboard().setText(text)
        
        # Change icon to checkmark
        button.setText("✅")
        
        # Create a timer to change it back to the clipboard icon after 1.5 seconds
        QTimer.singleShot(1500, lambda: button.setText("📋"))

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

    def show_help_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Language Learner - User Guide")
        dialog.resize(620, 550) 
        
        # Determine background color based on theme
        bg_color = "#071224" if self.is_dark_mode else "#F5F3EE"
        dialog.setStyleSheet(f"background-color: {bg_color};")

        main_layout = QVBoxLayout(dialog)
        main_layout.setContentsMargins(0, 0, 0, 0) 

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background: transparent;")

        content_widget = QWidget()
        content_widget.setStyleSheet("background: transparent;")
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(30, 30, 30, 30)
        content_layout.setSpacing(20)

        help_text = QLabel()
        help_text.setWordWrap(True)
        help_text.setTextFormat(Qt.TextFormat.RichText)
        
        # --- THE MASTER INSTRUCTIONS LIST ---
        instructions = """
        <h2 style='margin-bottom: 5px; font-size: 22px;'>🚀 Welcome to Language Learner</h2>
        <p style='font-size: 14px;'>Language Learner is a simple, distraction-free tool to translate text, listen to pronunciations, and automatically save your study notes into beautiful PDFs.</p>
        
        <hr style='border: 1px solid #64748B; margin: 15px 0;'>

        <h3 style='font-size: 16px;'>✨ Core Features</h3>
        <ul style='font-size: 14px; margin-left: -20px; line-height: 1.6;'>
            <li style='margin-bottom: 6px;'><b>Translation:</b> Type your word or sentence and click <b>ENTER</b>.</li>
            <li style='margin-bottom: 6px;'><b>Auto Detect:</b> Not sure what language you are reading? Choose 'Auto Detect' and let the app figure it out.</li>
            <li style='margin-bottom: 6px;'><b>Synonyms:</b> Type a single word and click <b>SYNONYMS</b> to see similar words and expand your vocabulary.</li>
            <li style='margin-bottom: 6px;'><b>Pronunciation:</b> Translating to Russian, Arabic, or Persian? Check <b>Show Pronunciation</b> to see how to read the alphabet in English letters.</li>
            <li style='margin-bottom: 6px;'><b>Audio Playback:</b> Click <b>🔊 PLAY</b> to hear a native voice read your translation out loud.</li>
            <li style='margin-bottom: 6px;'><b>German Articles:</b> Translate a single English noun to German, and the app will automatically find the correct "der, die, or das" for you.</li>
            <li style='margin-bottom: 6px;'><b>Font Adjustments:</b> Use the 'Font' dropdown at the top to make the text bigger or smaller for easy reading.</li>
        </ul>

        <h3 style='font-size: 16px; margin-top: 15px;'>📄 PDF Exporting & History</h3>
        <p style='font-size: 14px; margin-bottom: 10px;'>Everything you translate is temporarily saved in your current session so you can export it as a study guide.</p>
        <ul style='font-size: 14px; margin-left: -20px; line-height: 1.6;'>
            <li style='margin-bottom: 6px;'><b>PATH:</b> Choose the exact folder on your computer where your PDFs will be saved.</li>
            <li style='margin-bottom: 6px;'><b>LAYOUT:</b> Choose how your PDF looks: a stacked 1-Column format, or a side-by-side view.</li>
            <li style='margin-bottom: 6px;'><b>PDF:</b> Click this to instantly create and save a beautiful document of everything you learned today.</li>
            <li style='margin-bottom: 6px;'><b>DELETE LAST:</b> Made a mistake? Click this to remove your very last translation from the PDF memory.</li>
            <li style='margin-bottom: 6px;'><b>CLEAR HISTORY:</b> Click this to completely wipe the current memory and start a fresh study session.</li>
        </ul>

        <h3 style='font-size: 16px; margin-top: 15px;'>⌨️ Keyboard Shortcuts</h3>
        <ul style='font-size: 14px; margin-left: -20px; line-height: 1.6;'>
            <li style='margin-bottom: 8px;'><b>Shift + Enter</b> &nbsp;&mdash;&nbsp; Translate Text</li>
            <li style='margin-bottom: 8px;'><b>Ctrl + Delete</b> &nbsp;&mdash;&nbsp; Clear Canvas</li>
            <li style='margin-bottom: 8px;'><b>Ctrl + Shift + E</b> &nbsp;&mdash;&nbsp; Export to PDF</li>
        </ul>

        <h3 style='font-size: 16px; margin-top: 15px;'>🌐 Support the Project</h3>
        <p style='font-size: 14px;'>If you enjoy using Language Learner, click the <b>GitHub</b> button at the top to visit the official repository. You can check for new releases, view the source code, and leave a ⭐ star to support the project!</p>
        """
        
        # Apply theme-specific text colors
        if self.is_dark_mode:
            help_text.setStyleSheet("color: #D9E6FF; line-height: 1.6;")
        else:
            help_text.setStyleSheet("color: #2B2A28; line-height: 1.6;")

        help_text.setText(instructions)
        content_layout.addWidget(help_text)
        content_layout.addStretch()
        
        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)

        # Bottom Close Button
        btn_close = QPushButton("Got it, let's learn!")
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.clicked.connect(dialog.accept)
        
        if self.is_dark_mode:
            btn_close.setStyleSheet("background-color: #424DA8; color: #FFFFFF; border: none; border-radius: 8px; padding: 12px; margin: 10px 30px 20px 30px; font-weight: bold; font-size: 14px;")
        else:
            btn_close.setStyleSheet("background-color: #737DB9; color: #FFFFFF; border: none; border-radius: 8px; padding: 12px; margin: 10px 30px 20px 30px; font-weight: bold; font-size: 14px;")
            
        main_layout.addWidget(btn_close)

        dialog.exec()


    def eventFilter(self, source, event):
        # 1. Keep the buttons glued to the top-right corners when the window resizes
        if event.type() == QEvent.Type.Resize:
            if source is self.input_text:
                self.btn_copy_in.move(self.input_text.width() - 45, 15)
            elif source is self.output_text:
                self.btn_copy_out.move(self.output_text.width() - 45, 15)

        # 2. Keep your existing Shift+Enter translation logic
        if source is self.input_text and event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Return and event.modifiers() == Qt.KeyboardModifier.ShiftModifier:
                self.translate_text()
                return True 
                
        return super().eventFilter(source, event)

    def closeEvent(self, event):
        pygame.mixer.quit()
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