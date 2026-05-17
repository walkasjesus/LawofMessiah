import os
try:
    import pymupdf as fitz  # PyMuPDF
except ImportError:  # pragma: no cover
    import fitz  # PyMuPDF fallback
import logging
import json
from pathlib import Path

# === CONFIGURATION ===
# Single source PDF from volume 3.
REPO_ROOT = Path(__file__).resolve().parent.parent
SOURCE_PDF = REPO_ROOT / "volume_3_files" / "law_of_Messiah_volume_3.pdf"

# Page ranges are 1-based (as shown in the PDF/book).
# Adjust end pages here if the actual section ends earlier or later.
SECTIONS = [
    {
        "output_file": "Mitzvah_Title_List.json",
        "page_from": 9,    # first page of Mitzvah Title List
        "page_to": 23,     # last page  of Mitzvah Title List
    },
    {
        "output_file": "NT_Scripture_Index.json",
        "page_from": 566,  # first page of NT Scripture Index
        "page_to": 592,    # last page  of NT Scripture Index
    },
    {
        "output_file": "OT_Scripture_Index.json",
        "page_from": 593,  # first page of OT Scripture Index
        "page_to": 607,    # last page  of OT Scripture Index  ← adjust if needed
    },
]

structured_output_dir = REPO_ROOT / "volume_3_output" / "appendix_output"
structured_output_dir.mkdir(parents=True, exist_ok=True)

# Setup logging
log_dir = REPO_ROOT / "logs"
log_dir.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    filename=log_dir / "0_parse_appendix_files_to_json.log",
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


def extract_pages_to_json(pdf_path, page_from, page_to):
    """
    Extracts content from page_from to page_to (both inclusive, 1-based) from
    the given PDF into a structured list. Includes all spans with text, font,
    size, color, and flags (bbox removed).
    """
    structured_data = []

    with fitz.open(pdf_path) as pdf:
        total = pdf.page_count
        # Convert 1-based page numbers to 0-based indices; clamp to valid range.
        start_idx = max(0, page_from - 1)
        end_idx = min(total - 1, page_to - 1)

        logging.info(
            f"Extracting pages {page_from}–{page_to} "
            f"(indices {start_idx}–{end_idx}) from {os.path.basename(pdf_path)}"
        )

        for page_idx in range(start_idx, end_idx + 1):
            page_num_1based = page_idx + 1
            logging.debug(f"Processing page {page_num_1based}")
            page = pdf[page_idx]
            blocks = page.get_text("dict")["blocks"]

            page_data = {
                "page": page_num_1based,
                "width": page.rect.width,
                "height": page.rect.height,
                "blocks": []
            }

            for block in blocks:
                block_entry = {"lines": []}

                for line in block.get("lines", []):
                    line_entry = {"spans": []}

                    for span in line.get("spans", []):
                        line_entry["spans"].append({
                            "text": span["text"],
                            "font": span["font"],
                            "size": span["size"],
                            "color": span["color"],
                            "flags": span["flags"]
                        })

                    if line_entry["spans"]:
                        block_entry["lines"].append(line_entry)

                if block_entry["lines"]:
                    page_data["blocks"].append(block_entry)

            structured_data.append(page_data)

    return structured_data


if __name__ == "__main__":
    if not SOURCE_PDF.is_file():
        print(f"ERROR: Source PDF not found: {SOURCE_PDF}")
        logging.error(f"Source PDF not found: {SOURCE_PDF}")
        raise SystemExit(1)

    try:
        for section in SECTIONS:
            output_file = section["output_file"]
            page_from = section["page_from"]
            page_to = section["page_to"]

            logging.info(f"Processing section '{output_file}' pages {page_from}–{page_to}")
            print(f"Extracting '{output_file}' (pages {page_from}–{page_to})...")

            structured_data = extract_pages_to_json(SOURCE_PDF, page_from, page_to)

            output_path = structured_output_dir / output_file
            with open(output_path, "w", encoding="utf-8") as json_file:
                json.dump(structured_data, json_file, indent=4, ensure_ascii=False)

            logging.info(f"Saved {len(structured_data)} pages to {output_path}")
            print(f"  → Saved {len(structured_data)} pages to {output_path}")

        logging.info("All sections processed successfully.")
        print("Done.")

    except Exception as e:
        logging.error(f"An error occurred: {e}")
        raise
