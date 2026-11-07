import pytest
import io
import fitz
import zipfile
from services.document_parser import extract_text_from_file_bytes

def test_extract_plain_text_and_markdown():
    text_content = (
        "# Pengarahan Menteri Koordinator Bidang Politik dan Keamanan\n\n"
        "Keamanan nasional dan kedaulatan maritim merupakan pilar utama stabilitas negara.\n\n"
        "Langkah preventif harus diperkuat di seluruh titik perbatasan."
    ).encode("utf-8")

    result = extract_text_from_file_bytes(text_content, "arahan_menko.md")
    assert result["filename"] == "arahan_menko.md"
    assert "Keamanan nasional" in result["text"]
    assert result["word_count"] > 10
    assert result["page_count"] == 1
    assert len(result["paragraphs"]) == 3

def test_extract_pdf_document():
    # Build a 2-page in-memory PDF using fitz
    doc = fitz.open()
    p1 = doc.new_page()
    p1.insert_text((50, 50), "Halaman 1: Pidato Kedaulatan Wilayah Maritim UNCLOS 1982.")
    p2 = doc.new_page()
    p2.insert_text((50, 50), "Halaman 2: Sinergi BSSN dan TNI dalam Pengamanan Ruang Siber.")
    pdf_bytes = doc.tobytes()

    result = extract_text_from_file_bytes(pdf_bytes, "Nota_Kebijakan.pdf")
    assert result["filename"] == "Nota_Kebijakan.pdf"
    assert "Halaman 1" in result["text"]
    assert "Halaman 2" in result["text"]
    assert result["page_count"] == 2
    assert result["word_count"] > 10

def test_extract_docx_document():
    # Build in-memory DOCX OpenXML zip
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        xml_data = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            '<w:body>'
            '<w:p><w:r><w:t>Pernyataan Pers Resmi Kemenko Polkam.</w:t></w:r></w:p>'
            '<w:p><w:r><w:t>Penegakan integritas data perbatasan.</w:t></w:r></w:p>'
            '</w:body>'
            '</w:document>'
        )
        z.writestr("word/document.xml", xml_data.encode("utf-8"))
    docx_bytes = buf.getvalue()

    result = extract_text_from_file_bytes(docx_bytes, "Pernyataan_Pers.docx")
    assert result["filename"] == "Pernyataan_Pers.docx"
    assert "Pernyataan Pers Resmi Kemenko Polkam." in result["text"]
    assert "Penegakan integritas data perbatasan." in result["text"]
    assert len(result["paragraphs"]) == 2

def test_document_extract_api_endpoint():
    import base64
    from fastapi.testclient import TestClient
    from main import app

    client = TestClient(app)
    sample_text = "Naskah Pidato Resmi Menteri Koordinator Bidang Politik dan Keamanan Tahun 2026."
    b64_content = base64.b64encode(sample_text.encode("utf-8")).decode("utf-8")

    response = client.post("/api/document/extract", json={
        "filename": "pidato_menko.txt",
        "file_base64": b64_content
    })

    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "pidato_menko.txt"
    assert data["word_count"] > 5
    assert "Naskah Pidato Resmi" in data["text"]
    assert "estimated_speaking_duration" in data
