"""Conservative surface repetition detection, not a semantic error verifier."""
import argparse
from collections import defaultdict
import json
from pathlib import Path
import re

POLICY = dict(version=1, min_tokens=1024, check_every_tokens=128,
              window_words=600, phrase_words=32, min_occurrences=4,
              min_coverage=0.20, tail_words=80, confirmations=2)


class RepetitionGuard:
    def __init__(self, policy=None):
        self.policy = dict(POLICY if policy is None else policy)
        self.last_check = 0
        self.previous_last = -1
        self.confirmations = 0

    def check(self, text, generated_tokens):
        p = self.policy
        if generated_tokens < p["min_tokens"] or generated_tokens-self.last_check < p["check_every_tokens"]:
            return None
        self.last_check = generated_tokens
        words = re.findall(r"\w+", text.casefold())
        offset = max(0, len(words)-p["window_words"])
        window = words[offset:]
        n = p["phrase_words"]
        positions = defaultdict(list)
        for start in range(len(window)-n+1):
            phrase = tuple(window[start:start+n])
            if sum(word.isalpha() for word in phrase) < n // 2:
                continue
            seen = positions[phrase]
            if not seen or start-seen[-1] >= n:
                seen.append(start)
        candidates = []
        for phrase, starts in positions.items():
            coverage = len(starts)*n/max(1, len(window))
            if (len(starts) >= p["min_occurrences"] and coverage >= p["min_coverage"]
                    and len(window)-(starts[-1]+n) <= p["tail_words"]):
                candidates.append((starts[-1], len(starts), coverage, phrase, starts))
        if not candidates:
            self.confirmations = 0
            self.previous_last = -1
            return None
        last, count, coverage, phrase, starts = max(candidates)
        absolute_last = offset + last
        if absolute_last <= self.previous_last:
            return None  # Old repeated text alone cannot confirm a continuing loop.
        self.previous_last = absolute_last
        self.confirmations += 1
        if self.confirmations < p["confirmations"]:
            return None
        return dict(policy_version=p["version"], normalized_phrase=" ".join(phrase),
                    occurrences=count, coverage=coverage, word_offsets=[offset+s for s in starts],
                    confirmations=self.confirmations, observed_tokens=generated_tokens,
                    reason="long repeated surface phrase persists near output tail")


def aborted_judgment(row):
    if row.get("finish_reason") != "repetition_abort":
        return None
    return dict(question_id=row["question_id"], prediction=None, correct=False,
                gold=row["annotation"]["answer"], judge_skipped=True,
                error="repetition_abort", repetition_evidence=row.get("repetition_evidence"))


def replay(text):
    # CPU-only approximate prefix replay: word counts are NOT model token counts.
    spans = list(re.finditer(r"\w+", text))
    guard = RepetitionGuard()
    for count in range(128, len(spans)+1, 128):
        evidence = guard.check(text[:spans[count-1].end()], count)
        if evidence:
            evidence["observed_word_proxy"] = evidence.pop("observed_tokens")
            return dict(detected=True, prefix_words=count, total_words=len(spans), evidence=evidence)
    return dict(detected=False, total_words=len(spans))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("paths", nargs="+", type=Path)
    p.add_argument("--report", type=Path)
    args = p.parse_args()
    results = []
    for path in args.paths:
        raw = path.read_text(encoding="utf-8-sig")
        try:
            parsed = json.loads(raw)
            rows = parsed if isinstance(parsed, list) else [parsed]
        except json.JSONDecodeError:
            rows = [json.loads(line) for line in raw.splitlines() if line.strip()]
        for row in rows:
            value = row.get("result", {})
            text = value.get("gen_raw", value.get("gen"))
            if text is None:
                text = row.get("raw_response", row.get("response"))
            if not isinstance(text, str):
                raise ValueError(f"No recognized raw response field in {path}")
            results.append(dict(source=str(path), question_id=row.get("question_id", row.get("id")),
                                finish_reason=row.get("finish_reason"), **replay(text)))
    report = dict(policy=POLICY, replay_mode="approximate word-prefix replay; NOT exact token/time savings",
                  samples=len(results), detected=sum(r["detected"] for r in results), results=results)
    if args.report:
        with args.report.open("x", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
