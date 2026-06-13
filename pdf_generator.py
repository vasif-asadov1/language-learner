import os
import requests
from fpdf import FPDF
import database
from datetime import datetime # <-- NEW IMPORT

APP_DIR = os.path.expanduser("~/.LanguageLearnerPro")
os.makedirs(APP_DIR, exist_ok=True)

FONT_URL = "https://raw.githubusercontent.com/matplotlib/matplotlib/main/lib/matplotlib/mpl-data/fonts/ttf/DejaVuSans.ttf"
FONT_PATH = os.path.join(APP_DIR, "DejaVuSans.ttf")

def download_font():
    """Downloads a free font file safely using requests."""
    if not os.path.exists(FONT_PATH):
        response = requests.get(FONT_URL, timeout=15)
        response.raise_for_status() 
        with open(FONT_PATH, 'wb') as out_file:
            out_file.write(response.content)

def create_pdf(db_name, filename="learning_materials.pdf"):
    download_font()
    
    pdf = FPDF()
    pdf.add_page()
    
    pdf.add_font("DejaVu", "", fname=FONT_PATH)
    
    # --- NEW HEADING & DATE DESIGN ---
    pdf.set_font("DejaVu", size=20)
    pdf.cell(w=pdf.epw, h=10, text="Language Learning Notes", new_x="LMARGIN", new_y="NEXT", align="C")
    
    pdf.set_font("DejaVu", size=12)
    # Get current date in YYYY-MM-DD format
    current_date = datetime.now().strftime("%Y-%m-%d") 
    pdf.cell(w=pdf.epw, h=8, text=current_date, new_x="LMARGIN", new_y="NEXT", align="C")
    
    pdf.ln(10) # Add a nice gap before the translations start
    # ---------------------------------
    
    translations = database.get_all_translations(db_name)
    
    if not translations:
        return False 

    pdf.set_font("DejaVu", size=12)
    for index, (original, translated) in enumerate(translations, start=1):
        pdf.set_text_color(0, 0, 150)
        pdf.multi_cell(w=pdf.epw, h=8, text=f"{index}. {original}", new_x="LMARGIN", new_y="NEXT")
        
        pdf.set_text_color(0, 100, 0)
        pdf.multi_cell(w=pdf.epw, h=8, text=translated, new_x="LMARGIN", new_y="NEXT")
        
        pdf.ln(5) 
        
    pdf.output(filename)
    return True