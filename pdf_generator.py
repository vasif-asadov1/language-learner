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
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Load BOTH fonts into the PDF engine
    pdf.add_font("DejaVu", "", fname=DEJAVU_PATH)
    pdf.add_font("Amiri", "", fname=AMIRI_PATH)
        
    # --- PREMIUM HEADER ---
    pdf.set_fill_color(42, 57, 95)
    pdf.rect(10, 10, 190, 18, "F")

    pdf.set_font("DejaVu", size=20)
    pdf.set_text_color(255, 255, 255)

    pdf.set_xy(10, 13)
    pdf.cell(
        w=190,
        h=8,
        text="Language Learning Notes",
        align="C"
    )

    pdf.set_y(35)
    pdf.set_font("DejaVu", size=11)
    pdf.set_text_color(120, 120, 120)

    # Force English month names regardless of system locale
    months = ["", "January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
    now = datetime.now()
    current_date = f"{now.day:02d} {months[now.month]} {now.year}"

    pdf.cell(
        w=pdf.epw,
        h=8,
        text=current_date,
        new_x="LMARGIN",
        new_y="NEXT",
        align="C"
    )

    pdf.ln(8)
    
    translations = database.get_all_translations(db_name)
    
    if not translations:
        return False 
    
    # --- 2 COLUMN FLASHCARD LAYOUT ---
    if layout == "2_column":
        half_w = (pdf.epw / 2) - 5
        mid_x = pdf.l_margin + half_w + 5

        pdf.set_font("DejaVu", size=11)
        pdf.set_text_color(90, 90, 90)

        pdf.cell(half_w, 8, "Original", align="L")
        pdf.cell(half_w, 8, "Translation", align="L")
        pdf.ln(10)

        for index, (original, translated) in enumerate(translations, start=1):
            
            # 1. Split the text into lines/paragraphs to lock them side-by-side
            orig_lines = original.split('\n')
            trans_lines = translated.split('\n')

            # 2. Ensure both lists are the exact same length for perfect pairing
            max_len = max(len(orig_lines), len(trans_lines))
            orig_lines += [""] * (max_len - len(orig_lines))
            trans_lines += [""] * (max_len - len(trans_lines))

            for i, (o_line, t_line) in enumerate(zip(orig_lines, trans_lines)):
                # If it's an empty line (paragraph spacing), add vertical space and skip
                if not o_line.strip() and not t_line.strip():
                    pdf.ln(4)
                    continue

                # Add the numbering only to the very first line of the block
                o_text = f"{index}. {o_line}" if i == 0 else o_line

                # 3. Process text immediately so we can measure it
                orig_text, orig_align, orig_font = process_text(o_text)
                trans_text, trans_align, trans_font = process_text(t_line)

                # --- 4. PREDICTIVE PAGE BREAK CALCULATOR ---
                # Calculate exactly how many lines this paragraph will consume based on string width
                pdf.set_font(orig_font, size=12)
                lines_left = (pdf.get_string_width(orig_text) / half_w) + orig_text.count('\n')
                
                pdf.set_font(trans_font, size=12)
                lines_right = (pdf.get_string_width(trans_text) / half_w) + trans_text.count('\n')
                
                # Multiply the longest column by our line height (8) and add a safety buffer
                estimated_height = (max(lines_left, lines_right) + 1.5) * 8

                # If the paragraph will spill off the bottom, trigger a clean page break NOW!
                if pdf.get_y() + estimated_height > 275: # 297mm is standard A4 height
                    pdf.add_page()
                
                # Now we are 100% safe to lock in our starting Y coordinate
                start_y = pdf.get_y()

                # --- Left Column ---
                pdf.set_font(orig_font, size=12)
                pdf.set_text_color(59, 86, 164)
                pdf.set_xy(pdf.l_margin, start_y)
                pdf.multi_cell(w=half_w, h=8, text=orig_text, align=orig_align)
                end_y_left = pdf.get_y()

                # --- Right Column ---
                pdf.set_font(trans_font, size=12)
                pdf.set_text_color(31, 111, 81)
                pdf.set_xy(mid_x, start_y)
                pdf.multi_cell(w=half_w, h=8, text=trans_text, align=trans_align)
                end_y_right = pdf.get_y()

                # Find the lowest point between the two columns to draw the separator line
                max_y = max(end_y_left, end_y_right)
                
                # Only draw the middle line if an extreme edge-case page break didn't occur
                if end_y_left >= start_y and end_y_right >= start_y:
                    pdf.set_draw_color(225, 225, 225)
                    pdf.line(mid_x - 2.5, start_y, mid_x - 2.5, max_y)

                # Move the cursor down for the next paragraph
                pdf.set_y(max_y + 2)
            
            # Add extra space between entirely different translation sessions
            pdf.ln(8)
            
    # --- STANDARD 1 COLUMN LAYOUT ---
    else:
        for index, (original, translated) in enumerate(translations, start=1):
            
            # Original Text
            orig_text, orig_align, orig_font = process_text(f"{index}. {original}")
            pdf.set_font(orig_font, size=12)
            pdf.set_text_color(59, 86, 164)
            pdf.multi_cell(w=pdf.epw, h=8, text=orig_text, align=orig_align, new_x="LMARGIN", new_y="NEXT")
            
            # Translated Text
            trans_text, trans_align, trans_font = process_text(translated)
            pdf.set_font(trans_font, size=12)
            pdf.set_text_color(31, 111, 81)
            pdf.multi_cell(w=pdf.epw, h=8, text=trans_text, align=trans_align, new_x="LMARGIN", new_y="NEXT")
            
            pdf.ln(5) 
            
    pdf.output(filename)
    return True