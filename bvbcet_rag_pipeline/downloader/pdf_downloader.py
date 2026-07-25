"""PDF Downloader module downloading raw PDF files into knowledge_base/pdf/."""

from pathlib import Path
import requests
from config.config import PDF_DIR
from logger.logger import get_logger, log_pdf_download_status

logger = get_logger("pdf_downloader")


class PDFDownloader:
    """Handles HTTP download and storage of original PDF documents."""

    def __init__(self, output_dir: Path = PDF_DIR, timeout: int = 25) -> None:
        self.output_dir = output_dir
        self.timeout = timeout
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "BVBCET-KLETech-KnowledgeBaseBot/2.0"})

    def download(self, pdf_url: str) -> Path | None:
        """Download raw PDF to knowledge_base/pdf/."""
        try:
            filename = pdf_url.split("/")[-1].split("?")[0]
            if not filename.lower().endswith(".pdf"):
                filename += ".pdf"

            filename = "".join(c if c.isalnum() or c in "._-" else "_" for c in filename)
            local_path = self.output_dir / filename

            resp = self.session.get(pdf_url, timeout=self.timeout)
            if resp.status_code == 200:
                with open(local_path, "wb") as f:
                    f.write(resp.content)
                log_pdf_download_status(pdf_url, "SUCCESS", str(local_path))
                return local_path
            else:
                log_pdf_download_status(pdf_url, f"HTTP_{resp.status_code}")
        except Exception as err:
            logger.error(f"Failed to download PDF {pdf_url}: {err}")
            log_pdf_download_status(pdf_url, f"ERROR: {err}")
        return None
