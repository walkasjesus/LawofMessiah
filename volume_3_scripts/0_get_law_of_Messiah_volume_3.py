import os
import requests
import fitz  # PyMuPDF
import logging
import json

# Setup logging
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(log_dir, '0_get_law_of_Messiah_volume_3.log'),
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Define the URL and output paths
url = "https://www.genesisobservatory.us/ohev/Documents/Mitzvot%20in%20the%20New%20Testament/Vol%203.pdf"
output_dir = "volume_3_files"
output_file = os.path.join(output_dir, "law_of_Messiah_volume_3.pdf")
structured_output_dir = "volume_3_output"
os.makedirs(output_dir, exist_ok=True)
os.makedirs(structured_output_dir, exist_ok=True)

# Define the page range to parse
start_page = 24  # Start parsing from page 24
end_page = 514   # End parsing at page 514

# Function to download the PDF
def download_file(url, output_file):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    try:
        logging.info(f"Starting download from {url}")
        response = requests.get(url, headers=headers, stream=True)
        response.raise_for_status()
        with open(output_file, "wb") as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)
        logging.info(f"File downloaded successfully: {output_file}")
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to download file: {e}")
        raise

# Function to extract text with styles from the PDF
def extract_pdf_with_styles(pdf_path, output_path, start_page, end_page):
    """
    Extracts text from a PDF along with font, size, and other style information.
    Skips headers and footers and outputs the data in a structured JSON format.
    """
    structured_data = []

    with fitz.Document(pdf_path) as pdf:
        for page_num in range(start_page - 1, end_page):  # Adjust for 0-based indexing
            logging.info(f"Processing page {page_num + 1}")
            page = pdf[page_num]
            blocks = page.get_text("dict")["blocks"]  # Extract text as a dictionary
            page_data = {"page": page_num + 1, "content": []}

            previous_span = None  # Keep track of the previous span

            for block in blocks:
                if "lines" in block:  # Ensure the block contains text lines
                    for line in block["lines"]:
                        for span in line["spans"]:
                            # Extract text, font, size, and other attributes
                            text = span["text"].strip()
                            bbox = span["bbox"]

                            # Log details about the current span
                            logging.debug(f"Span Text: {text}, Font: {span['font']}, Size: {span['size']}, BBox: {bbox}")

                            # Skip only page numbers in the footer
                            if bbox[1] > page.rect.height - 100 and text.isdigit():  # Footer area and numeric text
                                logging.debug(f"Skipping footer page number: {text}")
                                continue

                            # Check if the span is an ID (e.g., "AA1.")
                            if span["size"] == 25.92 and re.match(r"^[A-Z]{2}[0-9]{1,2}\.$", text):
                                logging.info(f"Detected ID: {text}")
                                page_data["content"].append({
                                    "id": text,
                                    "font": span["font"],
                                    "size": span["size"],
                                    "color": span["color"],
                                    "bbox": bbox,
                                    "flags": span["flags"]
                                })
                                continue

                            # Check if the span is a title (e.g., "Aspiring to Godliness and Holiness.")
                            if span["size"] < 25.92 and text:
                                logging.info(f"Detected Title: {text}")
                                page_data["content"].append({
                                    "title": text,
                                    "font": span["font"],
                                    "size": span["size"]
                                })
                                continue

                            # Add other spans as-is
                            if text:
                                page_data["content"].append({
                                    "text": text,
                                    "font": span["font"],
                                    "size": span["size"]
                                })
                                
            if page_data["content"]:  # Only add pages with content
                structured_data.append(page_data)
            logging.info(f"Finished processing page {page_num + 1}")

    # Save the structured data to a JSON file
    with open(output_path, "w", encoding="utf-8") as json_file:
        json.dump(structured_data, json_file, indent=4, ensure_ascii=False)
    logging.info(f"Structured data saved to {output_path}")
       
if __name__ == "__main__":
    try:
        # Step 1: Download the PDF
        download_file(url, output_file)

        # Step 2: Extract text with styles and save as JSON
        structured_output_file = os.path.join(structured_output_dir, "law_of_Messiah_volume_3_structured.json")
        extract_pdf_with_styles(output_file, structured_output_file, start_page, end_page)

        logging.info("Processing completed successfully.")
    except Exception as e:
        logging.error(f"An error occurred: {e}")