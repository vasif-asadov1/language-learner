# Language Learner Pro 

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg?logo=python&logoColor=white)
![PyQt6](https://img.shields.io/badge/UI-PyQt6-green.svg?logo=qt&logoColor=white)
![SQLite](https://img.shields.io/badge/Database-SQLite3-003B57.svg?logo=sqlite&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-Linux%20%7C%20Windows-lightgrey.svg)
![Build](https://img.shields.io/badge/Build-GitHub%20Actions-2088FF.svg?logo=github-actions&logoColor=white)

**Language Learner Pro** is a high-performance, cross-platform desktop application designed for serious language learners. Built with Python and PyQt6, it combines real-time translation, intelligent part-of-speech (POS) tagging, session-based local data storage, and automated PDF reporting into a seamless, distraction-free interface.


# Why Use Language Learner?

1. **The "Google Translate" Problem (Automated Note-Taking):** 
While standard web translators allow limitless translations, they force a highly manual workflow: translating a word, copying it, switching to a separate note-taking app, formatting the text, and manually saving it. **Language Learner** eliminates this friction. You simply type and translate. With one click, your entire session is compiled into a cleanly formatted, timestamped PDF (e.g., `2026_06_13_22_11.pdf`), allowing you to effortlessly track your learning progress over time.

2. **The "Paid App" Problem (100% Free & Unlimited):**
Many automated vocabulary and language learning tools lock core features behind paywalls or impose strict daily translation limits. This application is completely free to run. It does not want your money, and there are absolutely zero limits on your translations or PDF generations. (If this tool helps your language journey, please consider giving the repository a star ⭐ and leaving a comment to support future improvements!)

# 🌐 Supported Languages

Currently, the application supports Universal Input (you can type in any language using Auto-Detect) and outputs precise translations and synonyms into the following target languages:

🇩🇪 German
🇬🇧 English
🇪🇸 Spanish
🇫🇷 French
🇮🇹 Italian

*(More target languages are actively planned for future releases).*

# Keyboard Shortcuts

Speed is critical for an unbroken learning workflow. The application features global hotkeys:

| Action | Shortcut | Description | 
| ----- | ----- | ----- | 
| **Translate** | `Shift + Enter` | Instantly translates the current input block. | 
| **New Line** | `Enter` | Drops to a new line inside the input box for longer texts. | 
| **Export PDF** | `Ctrl + Shift + E` | Immediately compiles the current session into a saved PDF. |


# Overview & Data Architecture

Engineered to solve the inefficiencies of standard translation workflows, this app utilizes robust backend logic and local data governance principles:

1. **Intelligent "Smart Article" Heuristic (NLP Integration):** Translation engines notoriously drop definitive articles (der/die/das, le/la, el/la) on single nouns. This app utilizes the Datamuse API to perform real-time Part-of-Speech tagging. By extracting the primary grammatical tag, the backend dynamically modifies the string prior to translation, forcing the engine to return the correct grammatical article for nouns while safely ignoring verbs and adjectives.

2. **Session-Based Data Persistence:** Every session dynamically provisions a temporary SQLite database safely stored in a hidden system configuration folder (~/.LanguageLearner). All user inputs and API responses are logged via standard CRUD operations.

3. **Automated ETL to PDF:** Upon session completion, the application queries the SQLite database, extracts the datasets, and utilizes fpdf2 to dynamically compile a structured report routed automatically to the user's customized export directory.

4. **Automated Cleanup:** To prevent storage bloat, overriding the Qt closeEvent ensures the temporary SQLite database is securely wiped from the system the exact millisecond the application window is closed.

# Key Features

* **Real-Time Translation:** Powered by `deep-translator` (Google Translate engine) with global keyboard shortcuts (`Shift+Enter`).
* **Contextual Synonyms:** Fetches the top 5 synonyms for any given word and translates them into the target language.
* **Modern UI/UX:** Clean, responsive PyQt6 interface featuring dynamic Dark/Light modes and centralized stylesheet management.
* **Smart PDF Export:** Generates perfectly formatted learning notes (`Ctrl+Shift+E`) complete with custom titles, timestamps, and color-coded text.

# Installation & Usage

This project utilizes a fully automated CI/CD pipeline via GitHub Actions to compile standalone binaries for Linux and Windows. **No Python installation or package management is required.**

## For Linux Users
1. Go to the [Releases page](https://github.com/vasif-asadov1/language-learner/releases).
2. Download `LanguageLearner-Linux`.
3. Open your terminal, navigate to the download folder, and make it executable:

```bash
   chmod +x LanguageLearner-Linux
```
4. Run the application:

```bash
   ./LanguageLearner-Linux
```

*(Alternatively, just double-click the file in your file manager).*

## For Windows Users
1. Go to the [Releases page](https://github.com/vasif-asadov1/language-learner/releases).
2. Download `LanguageLearner-Windows.exe`.
3. Double-click the `.exe` file to launch the application instantly.

# Development & Building from Source

If you wish to run the Python script locally or compile it yourself:

1. Clone the repository:
```bash
    git clone [https://github.com/vasif-asadov1/language-learner.git](https://github.com/vasif-asadov1/language-learner.git)
    cd language-learner
    ```

2. Create a virtual environment and install dependencies:
```bash
    python -m venv .venv
    source .venv/bin/activate  # Linux/Mac
    # .venv\Scripts\activate   # Windows
    pip install pyinstaller PyQt6 deep-translator requests fpdf2
    ```

3. Run the application:
```bash
    python main.py
    ```

4. Compile the standalone executable:
```bash
    pyinstaller --onefile --windowed --name "LanguageLearner" main.py
    ```

# 🔒 License & Copyright

**Copyright © 2026 Vasif Asadov. All rights reserved.**

This application is proprietary software. It is provided strictly as **Freeware** for personal, educational, and non-commercial language learning purposes. 

* **Usage:** Anyone is free to download, run, and use the compiled application binaries (`LanguageLearner-Linux` and `LanguageLearner-Windows.exe`) completely free of charge.
* **Restrictions:** Unauthorized copying, cloning, modification, redistribution, sublicensing, or creating public forks of this source code repository for any purpose is **strictly prohibited** without prior written permission from the copyright holder. 

By downloading or accessing this software, you agree to use it as an end-user only.
