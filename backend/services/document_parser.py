"""
Document Text Extraction Service for Menkopolkam AI Hub Teleprompter.
Extracts clean, structured text from PDF, DOCX, TXT, and Markdown files.
"""

import io
import re
import zipfile
import xml.etree.ElementTree as ET
from typing import Dict, Any, List

def extract_text_from_file_bytes(file_bytes: bytes, filename: str) -> Dict[str, Any]:
    """
    Extracts text and metadata from document binary bytes.
    Supports PDF (via fitz / PyMuPDF), DOCX (via zipfile & XML), and Plain Text/Markdown.
    """
    lower_name = filename.lower()
    clean_text = ""
    page_count = 1
    page_images: List[str] = []

    # 1. PDF Parsing
    if lower_name.endswith(".pdf") or file_bytes.startswith(b"%PDF-"):
        try:
            import fitz
            import base64
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            page_count = len(doc)
            page_texts: List[str] = []
            for i, page in enumerate(doc):
                txt = page.get_text()
                if txt.strip():
                    page_texts.append(txt.strip())
                # Render high-resolution page image for 100% authentic visual display (up to 25 pages)
                if i < 25:
                    pix = page.get_pixmap(dpi=150)
                    img_png = pix.tobytes("png")
                    b64_png = base64.b64encode(img_png).decode("ascii")
                    page_images.append(f"data:image/png;base64,{b64_png}")
            clean_text = "\n\n".join(page_texts)
        except Exception as e:
            # Fallback if fitz encounters non-standard encryption
            clean_text = f"Gagal mengekstrak teks PDF ({str(e)}). Silakan gunakan format DOCX atau TXT."

    # 2. DOCX Parsing (Word 2007+ OpenXML)
    elif lower_name.endswith(".docx") or file_bytes.startswith(b"PK\x03\x04"):
        try:
            with zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
                if "word/document.xml" in z.namelist():
                    xml_data = z.read("word/document.xml")
                    tree = ET.fromstring(xml_data)
                    # Extract all text elements with tag ending in 't' (w:t)
                    paragraphs: List[str] = []
                    # Find all paragraph tags (w:p)
                    for p in tree.iter():
                        if p.tag.endswith("p"):
                            texts = [elem.text for elem in p.iter() if elem.tag.endswith("t") and elem.text]
                            if texts:
                                paragraphs.append("".join(texts).strip())
                    clean_text = "\n\n".join(p for p in paragraphs if p)
                else:
                    clean_text = "Format DOCX tidak valid: komponen word/document.xml tidak ditemukan."
        except Exception as e:
            clean_text = f"Gagal membaca file DOCX ({str(e)}). Pastikan file tidak terkunci atau rusak."

    # 3. Plain Text / Markdown / RTF / Other Text Formats
    else:
        try:
            clean_text = file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            try:
                clean_text = file_bytes.decode("latin-1")
            except Exception:
                clean_text = str(file_bytes, errors="replace")

    # Clean up formatting
    clean_text = clean_text.replace("\r\n", "\n").replace("\r", "\n")
    # Normalize multiple line breaks
    clean_text = re.sub(r"\n{3,}", "\n\n", clean_text).strip()

    words = clean_text.split()
    word_count = len(words)
    char_count = len(clean_text)

    # Estimate reading duration (standard Indonesian speaking rate ~130 WPM)
    reading_seconds = int((word_count / 130) * 60) if word_count > 0 else 0
    est_minutes = reading_seconds // 60
    est_remainder_sec = reading_seconds % 60
    duration_str = f"{est_minutes:02d}:{est_remainder_sec:02d}"

    paragraphs = [p.strip() for p in clean_text.split("\n\n") if p.strip()]

    return {
        "filename": filename,
        "text": clean_text,
        "word_count": word_count,
        "char_count": char_count,
        "page_count": max(1, page_count),
        "estimated_speaking_duration": duration_str,
        "estimated_seconds": reading_seconds,
        "paragraphs": paragraphs,
        "page_images": page_images
    }
