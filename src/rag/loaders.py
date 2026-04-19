import csv
from pathlib import Path

from bs4 import BeautifulSoup
from pypdf import PdfReader

SOURCES_DIR = Path(__file__).parents[2] / "data" / "research_pack" / "sources"


def _chunk_text(text: str, size: int = 500, overlap: int = 100) -> list[str]:
    chunks = []
    start = 0
    while start < len(text):
        chunks.append(text[start : start + size])
        start += size - overlap
    return [c for c in chunks if c.strip()]


def _load_html(path: Path, source_id: str) -> list[dict]:
    soup = BeautifulSoup(path.read_text(encoding="utf-8"), "lxml")
    text = soup.get_text(separator=" ", strip=True)
    return [
        {"text": chunk, "source_id": source_id, "source_type": "html", "chunk_index": i}
        for i, chunk in enumerate(_chunk_text(text))
    ]


def _load_csv(path: Path) -> list[dict]:
    chunks = []
    with path.open(newline="", encoding="utf-8") as f:
        for i, row in enumerate(csv.DictReader(f)):
            text = (
                f"Vendor {row['vendor']} offers an annual base price of ${row['annual_base_usd']}/year, "
                f"including {row['included_docs_per_month']} documents/month with an overage of "
                f"${row['overage_per_doc_usd']}/doc. Uptime SLA: {row['uptime_sla']}. "
                f"SOC2 status: {row['soc2_status']}. Data residency: {row['data_residency']}. "
                f"Notes: {row['notes']}."
            )
            chunks.append(
                {"text": text, "source_id": "source_C", "source_type": "csv", "chunk_index": i}
            )
    return chunks


def _load_txt(path: Path, source_id: str) -> list[dict]:
    text = path.read_text(encoding="utf-8")
    return [
        {"text": chunk, "source_id": source_id, "source_type": "txt", "chunk_index": i}
        for i, chunk in enumerate(_chunk_text(text))
    ]


def _load_pdf(path: Path, source_id: str) -> list[dict]:
    reader = PdfReader(str(path))
    chunks = []
    idx = 0
    for page in reader.pages:
        page_text = page.extract_text() or ""
        for chunk in _chunk_text(page_text):
            chunks.append(
                {"text": chunk, "source_id": source_id, "source_type": "pdf", "chunk_index": idx}
            )
            idx += 1
    return chunks


def load_all_sources() -> list[dict]:
    return [
        *_load_html(SOURCES_DIR / "source_A_vendor_brief_acmedoc_ai.html", "source_A"),
        *_load_html(SOURCES_DIR / "source_B_vendor_brief_papermind_ai.html", "source_B"),
        *_load_csv(SOURCES_DIR / "source_C_pricing_features.csv"),
        *_load_txt(SOURCES_DIR / "source_D_internal_stakeholder_notes.txt", "source_D"),
        *_load_pdf(SOURCES_DIR / "source_E_security_questionnaire_summary.pdf", "source_E"),
    ]
