"""General Asset Downloader module."""

from pathlib import Path
import requests
from logger.logger import get_logger

logger = get_logger("asset_downloader")


class AssetDownloader:
    """Downloads general web assets (documents, images, static files)."""

    def __init__(self, timeout: int = 25) -> None:
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "BVBCET-KLETech-KnowledgeBaseBot/2.0"})

    def download_asset(self, url: str, destination_path: Path) -> bool:
        """Download asset URL to target destination path."""
        try:
            destination_path.parent.mkdir(parents=True, exist_ok=True)
            resp = self.session.get(url, timeout=self.timeout)
            if resp.status_code == 200:
                with open(destination_path, "wb") as f:
                    f.write(resp.content)
                return True
        except Exception as e:
            logger.error(f"Error downloading asset from {url}: {e}")
        return False
