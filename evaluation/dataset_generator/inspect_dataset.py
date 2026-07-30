"""Dataset Inspector Utility.

Allows easy manual inspection of 20–30 sample records from each category dataset
file in evaluation/datasets/.
"""

import argparse
import json
from pathlib import Path
from typing import List, Dict, Any


def inspect_category(file_path: Path, num_samples: int = 20) -> None:
    """Prints formatted sample entries from a dataset JSON file."""
    if not file_path.exists():
        print(f"❌ Dataset file not found: {file_path}")
        return

    with open(file_path, "r", encoding="utf-8") as f:
        records: List[Dict[str, Any]] = json.load(f)

    category_name = file_path.stem.capitalize()
    total_records = len(records)
    print("\n" + "=" * 75)
    print(f"  DATASET CATEGORY INSPECTION: {category_name.upper()} ({file_path.name})")
    print(f"  Total Records: {total_records} | Showing First {min(num_samples, total_records)} Samples")
    print("=" * 75)

    samples = records[:num_samples]
    for idx, item in enumerate(samples, start=1):
        print(f"\n--- [Sample #{idx} | ID: {item.get('id')}] ---")
        print(f"  Question     : {item.get('question')}")
        print(f"  Answer       : {item.get('expected_answer')[:120].strip()}...")
        print(f"  Document     : {item.get('expected_document')}")
        print(f"  Section      : {item.get('section')}")
        print(f"  Category     : {item.get('category')} | Difficulty: {item.get('difficulty')} | Perspective: {item.get('perspective', 'N/A')}")
        print(f"  Keywords     : {', '.join(item.get('keywords', []))}")

    print("\n" + "=" * 75 + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect generated evaluation datasets.")
    parser.add_argument(
        "--dataset-dir",
        type=str,
        default="evaluation/datasets",
        help="Path to datasets directory.",
    )
    parser.add_argument(
        "--category",
        type=str,
        default=None,
        help="Specific category to inspect (e.g. admission, fees, departments). If omitted, inspects all.",
    )
    parser.add_argument(
        "--samples",
        type=int,
        default=20,
        help="Number of samples to display per category (default: 20).",
    )
    args = parser.parse_args()

    dataset_dir = Path(args.dataset_dir)
    if args.category:
        target_file = dataset_dir / f"{args.category.lower()}.json"
        inspect_category(target_file, num_samples=args.samples)
    else:
        for json_file in sorted(dataset_dir.glob("*.json")):
            inspect_category(json_file, num_samples=args.samples)


if __name__ == "__main__":
    main()
