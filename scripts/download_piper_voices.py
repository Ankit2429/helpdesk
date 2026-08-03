"""Utility script to download Piper ONNX voice models for English and Hindi into data/piper/."""

import logging
from pathlib import Path
import httpx

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("download_piper_voices")

PIPER_MODELS_DIR = Path("data/piper")

VOICE_URLS = {
    # English (US Female / Medium)
    "en_US-lessac-medium.onnx": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx",
    "en_US-lessac-medium.onnx.json": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json",
    # Hindi (Male / Medium)
    "hi_IN-pratham-medium.onnx": "https://huggingface.co/rhasspy/piper-voices/resolve/main/hi/hi_IN/pratham/medium/hi_IN-pratham-medium.onnx",
    "hi_IN-pratham-medium.onnx.json": "https://huggingface.co/rhasspy/piper-voices/resolve/main/hi/hi_IN/pratham/medium/hi_IN-pratham-medium.onnx.json",
}


def download_file(url: str, dest_path: Path) -> None:
    if dest_path.exists() and dest_path.stat().st_size > 0:
        logger.info(f"File already exists: {dest_path} ({dest_path.stat().st_size / 1024 / 1024:.2f} MB). Skipping.")
        return

    logger.info(f"Downloading {url} -> {dest_path}...")
    with httpx.stream("GET", url, follow_redirects=True, timeout=60.0) as response:
        response.raise_for_status()
        with open(dest_path, "wb") as f:
            for chunk in response.iter_bytes(chunk_size=65536):
                f.write(chunk)
    logger.info(f"Downloaded {dest_path} ({dest_path.stat().st_size / 1024 / 1024:.2f} MB).")


def main() -> None:
    PIPER_MODELS_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(f"Target directory: {PIPER_MODELS_DIR.resolve()}")

    for filename, url in VOICE_URLS.items():
        dest = PIPER_MODELS_DIR / filename
        try:
            download_file(url, dest)
        except Exception as err:
            logger.error(f"Failed to download {filename}: {err}")

    logger.info("\nPiper voice download process complete.")


if __name__ == "__main__":
    main()
