# Language Learner Pro 

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg?logo=python&logoColor=white)
![PyQt6](https://img.shields.io/badge/UI-PyQt6-green.svg?logo=qt&logoColor=white)
![SQLite](https://img.shields.io/badge/Database-SQLite3-003B57.svg?logo=sqlite&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-Linux%20%7C%20Windows-lightgrey.svg)
![Build](https://img.shields.io/badge/Build-GitHub%20Actions-2088FF.svg?logo=github-actions&logoColor=white)

**Language Learner Pro** is a high-performance, cross-platform desktop application designed for serious language learners. Built with Python and PyQt6, it combines real-time translation, intelligent part-of-speech (POS) tagging, session-based local data storage, and automated PDF reporting into a seamless, distraction-free interface.

## Overview & Data Architecture

As a Data Professional, I built this application to address the inefficiencies of standard web-based translators by applying robust software engineering and local data governance principles:

1. **Intelligent "Smart Article" Heuristic:** Translation engines notoriously drop definitive articles (der/die/das, le/la, el/la) on single nouns. This app uses the **Datamuse API** to perform real-time Part-of-Speech tagging. If a single word is classified primarily as a noun, the backend dynamically modifies the string prior to translation to force the engine to return the correct grammatical article.
2. **Session-Based Data Persistence:** Every session dynamically provisions a temporary SQLite database hidden safely in a system configuration folder (`~/.LanguageLearnerPro`). All user inputs and API responses are logged via CRUD operations, allowing the user to seamlessly clear history or delete the latest entry without touching the filesystem.
3. **Automated ETL to PDF:** Upon session completion, the application queries the SQLite database, extracts the translated datasets, and utilizes `fpdf2` to dynamically format and compile a structured, timestamped PDF report routed to the user's customized export directory.
4. **Automated Cleanup:** To prevent storage bloat, overriding the Qt `closeEvent` ensures the temporary SQLite database is wiped from the system the exact millisecond the application window is closed.

## Key Features

* **Real-Time Translation:** Powered by `deep-translator` (Google Translate engine) with global keyboard shortcuts (`Shift+Enter`).
* **Contextual Synonyms:** Fetches the top 5 synonyms for any given word and translates them into the target language.
* **Modern UI/UX:** Clean, responsive PyQt6 interface featuring dynamic Dark/Light modes and centralized stylesheet management.
* **Smart PDF Export:** Generates perfectly formatted learning notes (`Ctrl+Shift+E`) complete with custom titles, timestamps, and color-coded text.

## Installation & Usage

This project utilizes a fully automated CI/CD pipeline via GitHub Actions to compile standalone binaries for Linux and Windows. **No Python installation or package management is required.**

### For Linux Users
1. Go to the [Releases page](https://github.com/vasif-asadov1/language-learner/releases).
2. Download `LanguageLearner-Linux`.
3. Open your terminal, navigate to the download folder, and make it executable:

   ```bash
   chmod +x LanguageLearner-Linux
   ```

1. Run the application:
    ```bash
    ./LanguageLearner-Linux &
    ```


*(Alternatively, just double-click the file in your file manager).*

### For Windows Users

1. Go to the [Releases page](https://github.com/vasif-asadov1/language-learner/releases).
2. Download `LanguageLearner-Windows.exe`.
3. Double-click the `.exe` file to launch the application instantly.

## Development & Building from Source

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



## 📄 License

This project is open-source and available under the MIT License. Feel free to fork, modify, and improve!

