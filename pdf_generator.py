import os
import urllib.request
from fpdf import FPDF
import database

# 1. Create a hidden background folder for app data
APP_DIR = os.path.expanduser("~/.LanguageLearnerPro")
os.makedirs(APP_DIR, exist_ok=True)

# 2. Lock the font to the hidden folder
FONT_URL = "https://raw.githubusercontent.com/matplotlib/matplotlib/main/lib/matplotlib/mpl-data/fonts/ttf/DejaVuSans.ttf"
FONT_PATH = os.path.join(APP_DIR, "DejaVuSans.ttf")

def download_font():
    """Downloads a free font file if it isn't already in the folder."""
    if not os.path.exists(FONT_PATH):
        req = urllib.request.Request(FONT_URL, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response, open(FONT_PATH, 'wb') as out_file:
            out_file.write(response.read())

def create_pdf(db_name, filename="learning_materials.pdf"):
    download_font()
    
    pdf = FPDF()
    pdf.add_page()
    
    pdf.add_font("DejaVu", "", FONT_PATH)
    
    pdf.set_font("DejaVu", size=16)
    pdf.cell(w=pdf.epw, h=10, text="My Language Learning Notes", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(10)
    
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