"""Download Manager orchestrating PDF and web asset retrieval."""

from pathlib import Path
from downloader.pdf_downloader import PDFDownloader
from downloader.asset_downloader import AssetDownloader


class DownloadManager:
    """Orchestrates asset downloads and PDF handling."""

    def __init__(self) -> None:
        self.pdf_downloader = PDFDownloader()
        self.asset_downloader = AssetDownloader()

    def download_pdf(self, pdf_url: str) -> Path | None:
        """Download PDF using PDFDownloader."""
        return self.pdf_downloader.download(pdf_url)

    def download_asset(self, url: str, target_path: Path) -> bool:
        """Download web asset using AssetDownloader."""
        return self.asset_downloader.download_asset(url, target_path)
