"""GT/ID/question-blind terminal extraction for long MMMU responses.

Reuse general-v4 extraction; add only whole terminal math/boxed formatting.
No numeric mining, reasoning completion or per-item correction.
"""
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "frozen"))
from answer_parser import extract_final, MARKER, normalize

VERSION = "mmmu-terminal-v1"


def boxed_end(text, start):
    match = re.match(r"\\boxed\s*\{", text[start:])
    if not match:
        return None
    inner_start = start + match.end()
    depth = 1
    for i in range(inner_start, len(text)):
        depth += (text[i] == "{") - (text[i] == "}")
        if depth > 16:
            return None
        if depth == 0:
            return inner_start, i, i+1
    return None


def format_only(text):
    """Keep the full content, including signs, units, words and alternatives."""
    text = normalize(text)
    for _ in range(8):
        before = text
        for left, right in (("$$", "$$"), (r"\[", r"\]"), (r"\(", r"\)"), ("$", "$")):
            if text.startswith(left) and text.endswith(right) and len(text) > len(left)+len(right):
                # A single balanced outer math span only, not '$3$ or $4$'.
                inner = text[len(left):-len(right)].strip()
                if left in ("$", "$$") and "$" in inner:
                    continue
                text = inner
                break
        box = boxed_end(text, 0)
        if box and box[2] == len(text):
            text = text[box[0]:box[1]].strip()
        text = normalize(text)
        if text == before:
            break
    # Standard presentation commands retain their entire literal contents.
    text = re.sub(r"\\(?:text|mathrm)\{([^{}]*)\}", lambda m: m[1], text)
    for spacing in (r"\,", r"\!", r"\;", r"\ "):
        text = text.replace(spacing, " ")
    return re.sub(r"\s+", " ", text.replace(r"\%", "%")).strip()


def record(response, start, end, method):
    while start < end and response[start].isspace(): start += 1
    while end > start and response[end-1].isspace(): end -= 1
    quote = response[start:end]
    if not quote or len(quote) > 512:
        return {"status": "review", "reason": "terminal_answer_length"}
    return {"status": "parsed", "method": method, "evidence_quote": quote,
        "span": [start, end], "answer_text": format_only(quote), "gt_used": False}


def extract_terminal(response):
    if not isinstance(response, str):
        raise ValueError("Response must be text")
    markers = list(MARKER.finditer(response))
    if len(markers) > 1:
        return {"status": "review", "reason": "multiple_answer_markers"}
    original = extract_final(response)
    if original["status"] == "parsed":
        return {**original, "answer_text": format_only(original["answer_text"]), "gt_used": False}
    if markers:
        start = markers[0].end()
        tail = response[start:].strip()
        # Multi-line math is allowed only as one complete terminal math block.
        if any(tail.startswith(left) and tail.endswith(right) for left,right in
               (("$$", "$$"), (r"\[", r"\]"), (r"\(", r"\)"))):
            return record(response, start, len(response), "explicit_terminal_math_block")
        return original
    boxes = list(re.finditer(r"\\boxed\s*\{", response))
    if len(boxes) != 1:
        return {"status": "review", "reason": "no_unique_terminal_box_or_answer_marker"}
    match = boxes[0]
    box = boxed_end(response, match.start())
    if box is None:
        return {"status": "review", "reason": "unbalanced_box"}
    # Standalone last line/block, not 'not \\boxed{3}' or 'x = \\boxed{3}'.
    line_start = response.rfind("\n", 0, match.start()) + 1
    before = response[line_start:match.start()].strip()
    after = response[box[2]:].strip()
    matching_wrappers = {"": "", "$": "$", "$$": "$$", r"\[": r"\]", r"\(": r"\)"}
    if before not in matching_wrappers or after != matching_wrappers[before]:
        return {"status": "review", "reason": "box_not_a_whole_standalone_terminal_answer"}
    return record(response, line_start, len(response), "standalone_terminal_box")
