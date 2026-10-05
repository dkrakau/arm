import argparse
import json
import time
from pathlib import Path

import requests
from tqdm import tqdm

GROBID_URL = "http://localhost:8070/api/processFulltextDocument"
TIMEOUT_SECONDS = 300


def load_status(status_file: Path) -> dict:
    if status_file.exists():
        return json.loads(status_file.read_text(encoding="utf-8"))
    return {}


def save_status(status_file: Path, status: dict) -> None:
    status_file.write_text(
        json.dumps(status, indent=2, ensure_ascii=False), encoding="utf-8"
    )


# sending pdf file to grobid and returns tei-xml string as response
def process_pdf(pdf_path: Path, include_raw_citations: bool = False) -> str:
    with open(pdf_path, "rb") as f:
        files = {"input": (pdf_path.name, f, "application/pdf")}
        data = {
            "consolidateHeader": "0",  # disable online checks
            "consolidateCitations": "0",
            "includeRawCitations": "1" if include_raw_citations else "0",
            "teiCoordinates": "0",
        }
        response = requests.post(
            GROBID_URL, files=files, data=data, timeout=TIMEOUT_SECONDS
        )

    if response.status_code != 200:
        raise RuntimeError(f"GROBID HTTP {response.status_code}: {response.text[:300]}")

    return response.text


def main():
    parser = argparse.ArgumentParser(description="Batch-Processing of PDFs for GROBID")
    parser.add_argument("--input", required=True, help="Folder with PDF files")
    parser.add_argument("--output", required=True, help="Folder for TEI-XML-Output")
    parser.add_argument("--retries", type=int, default=1, help="Repeat on error")
    args = parser.parse_args()

    input_dir = Path(args.input)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    status_file = output_dir / "status.json"
    failed_file = output_dir / "failed.json"

    status = load_status(status_file)
    failed = load_status(failed_file)

    pdf_files = sorted(input_dir.glob("*.pdf"))
    if not pdf_files:
        print(f"No PDFs found in {input_dir}")
        return

    # check connection
    try:
        alive = requests.get("http://localhost:8070/api/isalive", timeout=5)
        if alive.text.strip().lower() != "true":
            raise RuntimeError("GROBID is available, but not ready yet.")
    except requests.exceptions.ConnectionError:
        print("ERROR: GROBID not available on localhost:8070.")
        return

    to_process = [p for p in pdf_files if status.get(p.name) != "done"]
    print(
        f"{len(pdf_files)} PDFs found, {len(to_process)} left to process "
        f"({len(pdf_files) - len(to_process)} already processed)."
    )

    for pdf_path in tqdm(to_process, desc="GROBID-Processing"):
        out_path = output_dir / f"{pdf_path.stem}.tei.xml"
        attempt = 0
        last_error = None

        while attempt <= args.retries:
            try:
                tei_xml = process_pdf(pdf_path)
                out_path.write_text(tei_xml, encoding="utf-8")
                status[pdf_path.name] = "done"
                failed.pop(pdf_path.name, None)
                break
            except Exception as e:
                last_error = str(e)
                attempt += 1
                time.sleep(2)
        else:
            status[pdf_path.name] = "failed"
            failed[pdf_path.name] = last_error
            print(f"\n  Failed: {pdf_path.name} -> {last_error}")

        # save files
        save_status(status_file, status)
        save_status(failed_file, failed)

    done_count = sum(1 for v in status.values() if v == "done")
    failed_count = sum(1 for v in status.values() if v == "failed")
    print(f"\nDone. Successed: {done_count}, Failed: {failed_count}.")
    if failed_count:
        print(f"Details for Errors in: {failed_file}")


if __name__ == "__main__":
    main()

# py grobid_process_pdfs.py --input ../pdf/open_access --output open_access
# py grobid_process_pdfs.py --input ../pdf/not_open_access --output not_open_access
