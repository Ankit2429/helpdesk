import os
import logging
from pathlib import Path
from typing import Dict, Tuple

logger = logging.getLogger(__name__)

class KBLoader:
    """Safely loads and parses markdown files containing YAML frontmatter."""

    @staticmethod
    def load_document(filepath: str | Path) -> Tuple[Dict, str]:
        """Read a markdown file and split into (metadata_dict, body_text)."""
        filepath = Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"Markdown document not found: {filepath}")
            
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception as e:
            logger.error(f"Failed to read file {filepath}: {e}")
            raise IOError(f"Failed to read file {filepath}: {e}")
            
        metadata = {}
        body = content
        
        if content.strip().startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                yaml_text = parts[1]
                body = parts[2]
                
                # Simple parsing of YAML frontmatter
                import yaml
                try:
                    metadata = yaml.safe_load(yaml_text) or {}
                except Exception as e:
                    logger.warning(f"Failed to parse YAML frontmatter in {filepath}: {e}")
                    # Fallback line-by-line parsing
                    for line in yaml_text.splitlines():
                        if ":" in line:
                            k, v = line.split(":", 1)
                            metadata[k.strip()] = v.strip().strip('"').strip("'")
                            
        return metadata, body
