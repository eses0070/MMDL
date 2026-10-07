"""Print lengths and answer tails without loading models or calling APIs."""
import argparse
import json
from pathlib import Path

from checkpointing import summarize


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    path = args.directory / "predictions.jsonl"
    rows = [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
    config = json.loads((args.directory / "run_config.json").read_text(encoding="utf-8"))
    print(json.dumps(summarize(rows, config["expected"]), indent=2))
    for row in sorted(rows, key=lambda x: x["generated_tokens"], reverse=True)[:5]:
        print(f"\nID: {row['question_id']} tokens={row['generated_tokens']} "
              f"seconds={row.get('elapsed_seconds', 0):.1f} finish={row['finish_reason']}")
        print("Answer tail:", row["result"]["gen_raw"][-1500:])


if __name__ == "__main__":
    main()
