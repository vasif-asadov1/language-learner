import os
import urllib.request
from fpdf import FPDF
import database

# Using the highly stable Matplotlib repository for the font
FONT_URL = "https://raw.githubusercontent.com/matplotlib/matplotlib/main/lib/matplotlib/mpl-data/fonts/ttf/DejaVuSans.ttf"
FONT_PATH = "DejaVuSans.ttf"

def download_font():
    """Downloads a free font file if it isn't already in the folder."""
    if not os.path.exists(FONT_PATH):
        print("Downloading UTF-8 font for proper text rendering...")
        req = urllib.request.Request(FONT_URL, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response, open(FONT_PATH, 'wb') as out_file:
            out_file.write(response.read())

def create_pdf(db_name, filename="learning_materials.pdf"):
    """Fetches translations from the SPECIFIC SESSION database and compiles them into a PDF."""
    download_font()
    
    pdf = FPDF()
    pdf.add_page()
    
    # Load and set the font
    pdf.add_font("DejaVu", "", FONT_PATH)
    
    # Title
    pdf.set_font("DejaVu", size=16)
    pdf.cell(w=pdf.epw, h=10, text="My Language Learning Notes", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(10)
    
    # Fetch data from the specific session database
    translations = database.get_all_translations(db_name)
    
    if not translations:
        return False # Return False if there is nothing to print

    # Loop through each translation and write it to the PDF
    pdf.set_font("DejaVu", size=12)
    for index, (original, translated) in enumerate(translations, start=1):
        # Original Text (Blue)
        pdf.set_text_color(0, 0, 150)
        pdf.multi_cell(w=pdf.epw, h=8, text=f"{index}. {original}", new_x="LMARGIN", new_y="NEXT")
        
        # Target Text (Green)
        pdf.set_text_color(0, 100, 0)
        pdf.multi_cell(w=pdf.epw, h=8, text=translated, new_x="LMARGIN", new_y="NEXT")
        
        pdf.ln(5) 
        
    pdf.output(filename)
    return True