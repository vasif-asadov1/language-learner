import os
import re
import requests
from fpdf import FPDF
import database
from datetime import datetime
import arabic_reshaper
from bidi.algorithm import get_display

APP_DIR = os.path.expanduser("~/.LanguageLearnerPro")
os.makedirs(APP_DIR, exist_ok=True)

# --- DUAL FONT SYSTEM ---
DEJAVU_URL = "https://raw.githubusercontent.com/matplotlib/matplotlib/main/lib/matplotlib/mpl-data/fonts/ttf/DejaVuSans.ttf"
DEJAVU_PATH = os.path.join(APP_DIR, "DejaVuSans.ttf")

AMIRI_URL = "https://github.com/aliftype/amiri/raw/main/fonts/Amiri-Regular.ttf"
AMIRI_PATH = os.path.join(APP_DIR, "amiri-regular.ttf")

def download_fonts():
    """Downloads both free font files safely using requests."""
    fonts = [(DEJAVU_PATH, DEJAVU_URL), (AMIRI_PATH, AMIRI_URL)]
    for path, url in fonts:
        if not os.path.exists(path):
            try:
                response = requests.get(url, timeout=15)
                response.raise_for_status() 
                with open(path, 'wb') as out_file:
                    out_file.write(response.content)
            except Exception as e:
                print(f"Failed to download font from {url}: {e}")

def process_text(text):
    """
    Scans text for Arabic/Persian characters.
    Returns: (Processed Text, Alignment Direction, Font Name)
    """

    text = re.sub(r'[^\x00-\uFFFF]', '', text)
    if re.search(r'[\u0600-\u06FF]', text):
        # Arabic/Persian detected: Reshape, Bidi-flip, Align Right, Use Amiri
        reshaped_text = arabic_reshaper.reshape(text)
        bidi_text = get_display(reshaped_text)
        return bidi_text, 'R', 'Amiri'
    
    # Standard text (Russian, Turkish, English, etc.): Align Left, Use DejaVu
    return text, 'L', 'DejaVu'

def create_pdf(db_name, filename="learning_materials.pdf", layout="1_column"):
    download_fonts()
    
    pdf = FPDF()
    pdf.add_page()
    
    # Load BOTH fonts into the PDF engine
    pdf.add_font("DejaVu", "", fname=DEJAVU_PATH)
    pdf.add_font("Amiri", "", fname=AMIRI_PATH)
    
    # --- HEADING & DATE (Always DejaVu for English headers) ---
    pdf.set_font("DejaVu", size=20)
    pdf.cell(w=pdf.epw, h=10, text="Language Learning Notes", new_x="LMARGIN", new_y="NEXT", align="C")
    
    pdf.set_font("DejaVu", size=12)
    current_date = datetime.now().strftime("%Y-%m-%d") 
    pdf.cell(w=pdf.epw, h=8, text=current_date, new_x="LMARGIN", new_y="NEXT", align="C")
    
    pdf.ln(10) 
    
    translations = database.get_all_translations(db_name)
    
    if not translations:
        return False 
    
    # --- 2 COLUMN FLASHCARD LAYOUT ---
    if layout == "2_column":
        half_w = (pdf.epw / 2) - 5
        mid_x = pdf.l_margin + half_w + 5
        
        for index, (original, translated) in enumerate(translations, start=1):
            if pdf.get_y() > 210:
                pdf.add_page()
                
            start_y = pdf.get_y()
            
            # Left Column (Original Text)
            orig_text, orig_align, orig_font = process_text(f"{index}. {original}")
            pdf.set_font(orig_font, size=12) # Dynamically set the exact font needed
            pdf.set_text_color(0, 0, 150)
            pdf.set_xy(pdf.l_margin, start_y)
            pdf.multi_cell(w=half_w, h=8, text=orig_text, align=orig_align)
            end_y_left = pdf.get_y()
            
            # Right Column (Translated Text)
            trans_text, trans_align, trans_font = process_text(translated)
            pdf.set_font(trans_font, size=12) # Dynamically set the exact font needed
            pdf.set_text_color(0, 100, 0)
            pdf.set_xy(mid_x, start_y)
            pdf.multi_cell(w=half_w, h=8, text=trans_text, align=trans_align)
            end_y_right = pdf.get_y()
            
            max_y = max(end_y_left, end_y_right)
            
            # Draw the thin separator line down the middle
            pdf.set_draw_color(200, 200, 200)
            pdf.line(mid_x - 2.5, start_y, mid_x - 2.5, max_y)
            
            pdf.set_y(max_y + 8)
            
    # --- STANDARD 1 COLUMN LAYOUT ---
    else:
        for index, (original, translated) in enumerate(translations, start=1):
            
            # Original Text
            orig_text, orig_align, orig_font = process_text(f"{index}. {original}")
            pdf.set_font(orig_font, size=12)
            pdf.set_text_color(0, 0, 150)
            pdf.multi_cell(w=pdf.epw, h=8, text=orig_text, align=orig_align, new_x="LMARGIN", new_y="NEXT")
            
            # Translated Text
            trans_text, trans_align, trans_font = process_text(translated)
            pdf.set_font(trans_font, size=12)
            pdf.set_text_color(0, 100, 0)
            pdf.multi_cell(w=pdf.epw, h=8, text=trans_text, align=trans_align, new_x="LMARGIN", new_y="NEXT")
            
            pdf.ln(5) 
            
    pdf.output(filename)
    return True