"""Dataset Writer Module.

Formats validated QA pairs into schema-compliant records and updates/writes JSON files
in evaluation/datasets/*.json.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Tuple

from evaluation.dataset_generator.config import GeneratorConfig
from evaluation.dataset_generator.question_generator import GeneratedQuestionCandidate
from evaluation.dataset_generator.reader import MarkdownDocument

logger = logging.getLogger(__name__)


class DatasetWriter:
    """Writes and merges dataset records into JSON files."""

    def __init__(self, config: GeneratorConfig):
        self.config = config
        self.output_dir = Path(config.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _get_target_file(self, category: str) -> Path:
        """Resolves target JSON filename for a category."""
        filename = self.config.category_file_map.get(category, "misc.json")
        return self.output_dir / filename

    def load_existing_records(self, file_path: Path) -> List[Dict[str, Any]]:
        """Loads existing records from a dataset JSON file."""
        if not file_path.exists():
            return []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except Exception as e:
            logger.error(f"Error loading existing dataset file {file_path}: {e}")
            return []

    def format_record(
        self,
        record_id: int,
        candidate: GeneratedQuestionCandidate,
        doc: MarkdownDocument,
        category: str,
    ) -> Dict[str, Any]:
        """Formats a candidate into the required dataset JSON schema."""
        return {
            "id": record_id,
            "question": candidate.question,
            "expected_answer": candidate.expected_answer,
            "expected_document": doc.filename,
            "category": category,
            "section": candidate.section_heading,
            "source_heading": candidate.section_heading,
            "keywords": candidate.keywords,
            "difficulty": candidate.difficulty,
            "perspective": candidate.perspective,
        }

    def write_records(
        self,
        category: str,
        new_items: List[Tuple[GeneratedQuestionCandidate, MarkdownDocument]],
    ) -> int:
        """Appends/merges new records into category dataset JSON file.

        Args:
            category: Domain category string.
            new_items: List of (candidate, doc) tuples.

        Returns:
            Number of newly written records.
        """
        if not new_items:
            return 0

        target_file = self._get_target_file(category)
        existing_data = [] if self.config.overwrite_existing else self.load_existing_records(target_file)

        start_id = len(existing_data) + 1
        records_to_add = []

        for idx, (cand, doc) in enumerate(new_items, start=start_id):
            record = self.format_record(idx, cand, doc, category)
            records_to_add.append(record)

        combined_data = existing_data + records_to_add

        try:
            with open(target_file, "w", encoding="utf-8") as f:
                json.dump(combined_data, f, indent=2, ensure_ascii=False)
            logger.info(
                f"Wrote {len(records_to_add)} records to {target_file.name} (Total: {len(combined_data)})"
            )
            return len(records_to_add)
        except Exception as e:
            logger.error(f"Failed to write dataset file {target_file}: {e}")
            return 0
