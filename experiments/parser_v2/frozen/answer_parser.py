"""GT-blind extraction and conservative comparison. No per-item exceptions.

None means the rule cannot decide, not that the model's answer is false.
Only surface form, explicit answer-type words and structured labels/formulae
are handled. This is not a semantic equivalence or reasoning model.
"""
import re
import unicodedata
from collections import Counter

VERSION = "general-text-v4.1"
MARKER = re.compile(r"(?im)^[ \t>#✅✔]*(?:\*\*)?(?:final\s+answer|answer)(?:\*\*)?\s*(?::|\n)")
UNSAFE = re.compile(r"\b(?:not|neither|nor|or|but|except|instead|maybe|perhaps|because|rather|possibly|probably|guess)\b|[!?;=/]", re.I)
ELEMENTS = set("H He Li Be B C N O F Ne Na Mg Al Si P S Cl Ar K Ca Sc Ti V Cr Mn Fe Co Ni Cu Zn Ga Ge As Se Br Kr Rb Sr Y Zr Nb Mo Tc Ru Rh Pd Ag Cd In Sn Sb Te I Xe Cs Ba La Ce Pr Nd Pm Sm Eu Gd Tb Dy Ho Er Tm Yb Lu Hf Ta W Re Os Ir Pt Au Hg Tl Pb Bi Po At Rn Fr Ra Ac Th Pa U Np Pu Am Cm Bk Cf Es Fm Md No Lr Rf Db Sg Bh Hs Mt Ds Rg Cn Nh Fl Mc Lv Ts Og".split())


def normalize(text):
    """Layout only. Preserve case, digits, negation, punctuation and modifiers."""
    text = unicodedata.normalize("NFC", str(text)).strip()
    for _ in range(6):
        before = text
        for left, right in [("**", "**"), ("__", "__"), ("`", "`"), ('"', '"'), ("'", "'"), (r"\(", r"\)")]:
            if text.startswith(left) and text.endswith(right) and len(text) > len(left) + len(right):
                text = text[len(left):-len(right)].strip()
                break
        if before == text:
            break
    return re.sub(r"\s+", " ", text)


def extract_final(response):
    """Extract a whole short terminal answer. Does not receive GT, ID or question."""
    if not isinstance(response, str):
        raise ValueError("Response must be text")
    markers = list(MARKER.finditer(response))
    if len(markers) > 1:
        return {"status": "review", "reason": "multiple_answer_markers"}
    start = markers[0].end() if markers else 0
    odd_bold = bool(markers and markers[0][0].count("**") % 2)
    if odd_bold and response[start:].startswith("**"):
        start += 2
        odd_bold = False
    fragment = response[start:].strip()
    if not markers and ("\n" in fragment or len(fragment) > 100):
        return {"status": "review", "reason": "no_explicit_short_terminal_answer"}
    # A separator alone is formatting; arbitrary trailing prose is never dropped.
    fragment = re.sub(r"(?:\n\s*[-_]{3,}\s*)+$", "", fragment).strip()
    if "\n" in fragment:
        return {"status": "review", "reason": "multiline_or_trailing_text"}
    if not fragment or len(fragment) > 200:
        return {"status": "review", "reason": "answer_length"}
    answer = fragment[:-2] if odd_bold and fragment.endswith("**") and fragment.count("**") == 1 else fragment
    answer = normalize(answer)
    if not answer:
        return {"status": "review", "reason": "empty_answer"}
    offset = response.find(fragment, start)
    assert offset >= 0
    return {"status": "parsed", "answer_text": answer, "evidence_quote": fragment,
            "span": [offset, offset + len(fragment)],
            "method": "explicit_terminal_answer" if markers else "whole_short_response"}


def formula_counts(text):
    matches = list(re.finditer(r"([A-Z][a-z]?)([1-9]\d*)?", text))
    if not matches or "".join(m[0] for m in matches) != text:
        return None
    counts = Counter()
    for m in matches:
        if m[1] not in ELEMENTS:
            return None
        counts[m[1]] += int(m[2] or 1)
    return dict(counts)


def ordinary_words(text):
    # Do not case-fold symbols, all-caps abbreviations, chemical locants or numbers.
    if not re.fullmatch(r"[A-Za-z]+(?:[ '\-][A-Za-z]+)*", text):
        return False
    return all(len(w) > 1 and not w.isupper() and formula_counts(w) is None
               for w in re.findall(r"[A-Za-z]+", text))


def text_form(text):
    text = normalize(text)
    if text.endswith(".") and ordinary_words(text[:-1]):
        text = text[:-1]
    return text.casefold() if ordinary_words(text) else text


def requested_heads(question):
    """Require a requested/blank answer type, not merely a noun in the context."""
    q = question.casefold()
    heads = set()
    for head in ("stage", "phase", "step", "region", "point", "part", "label"):
        if re.search(r"\b(?:which|what)\s+(?:[a-z]+\s+){0,3}" + head + r"s?\b", q) or re.search(r"_+\s*" + head + r"\b", q):
            heads.add(head)
    return heads


def explicit_type(question):
    q = question.casefold()
    if re.search(r"\b(?:chemical|molecular|empirical)\s+formula\b|\bformula\b.*\bchemical symbols\b", q):
        return "formula"
    heads = [w for w in ("stage", "phase") if w in requested_heads(question)]
    return heads[0] if len(heads) == 1 else "text"


def label(text, question):
    requested = requested_heads(question)
    m = re.fullmatch(r"(?:(step|region|point|part|label)\s+)?([A-Z]|\d{1,3})", normalize(text))
    if not m:
        m = re.fullmatch(r"(?:(Step|Region|Point|Part|Label)\s+)([A-Z]|\d{1,3})", normalize(text))
    if not m:
        return None
    if m[1] and m[1].casefold() not in requested:
        return None
    if not requested.intersection({"step", "region", "point", "part", "label"}):
        return None
    return m[2]


def compare_one(answer, target, question=""):
    candidate, gold = normalize(answer), normalize(target)
    # GT may legitimately contain a phrase or negation; exact full equality is safe.
    if candidate == gold and candidate:
        return True, "whole_answer_exact"
    if UNSAFE.search(candidate) or UNSAFE.search(gold):
        return None, "qualified_or_alternative_answer"
    mode = explicit_type(question)
    if mode == "formula":
        # Dollar/math wrappers are accepted only under explicit formula context.
        def math_wrapper(value):
            if "$" not in value:
                return value
            if value.startswith("$") and value.endswith("$") and value.count("$") == 2 and len(value) > 2:
                return value[1:-1]
            return ""
        c, g = math_wrapper(candidate), math_wrapper(gold)
        cc, gc = formula_counts(c), formula_counts(g)
        if cc and gc:
            if c == g:
                return True, "same_formula"
            if cc != gc:
                return False, "different_formula_composition"
            return None, "formula_order_or_isomerism_not_resolved"
        return None, "unsupported_formula"
    c_label, g_label = label(candidate, question), label(gold, question)
    if c_label is not None and g_label is not None:
        return c_label == g_label, "explicit_label_comparison"
    if text_form(candidate) == text_form(gold):
        return True, "whole_text_format_normalized"
    if mode in {"stage", "phase"}:
        # Remove only the requested type word, never adjectives or arbitrary suffixes.
        def without_head(value):
            form = text_form(value)
            return re.sub(r"\s+" + mode + r"$", "", form)
        if ordinary_words(candidate.rstrip(".")) and ordinary_words(gold.rstrip(".")):
            if without_head(candidate) == without_head(gold):
                return True, "explicit_type_word_wrapper"
    return None, "semantic_equivalence_not_established"


def compare_text(answer, accepted, question=""):
    checks = []
    for target in accepted:
        correct, method = compare_one(answer, str(target), question)
        checks.append({"target": str(target), "correct": correct, "method": method})
    correct = True if any(c["correct"] is True for c in checks) else (
        False if checks and all(c["correct"] is False for c in checks) else None)
    return {"correct": correct, "checks": checks, "substring_matching_used": False}


def extract_mc(response, options, question=""):
    """Map final answer to an actual option. GT is deliberately not an argument."""
    result = extract_final(response)
    if result["status"] != "parsed":
        return result
    answer = result["answer_text"]
    letter = re.fullmatch(r"(?:[Oo]ption\s+)?\(?([A-Z])\)?[.!]?", answer)
    pair = re.fullmatch(r"(?:[Oo]ption\s+)?\(?([A-Z])\)?[.:)]\s*(.+)", answer)
    if letter or pair:
        key = (letter or pair)[1]
        if key not in options:
            return {**result, "status": "review", "reason": "invalid_option_key"}
        if pair:
            comparison = compare_text(pair[2], [str(options[key])], question)
            if comparison["correct"] is not True:
                return {**result, "status": "review", "reason": "letter_content_agreement_unconfirmed", "comparison": comparison}
        return {**result, "prediction": key, "reason": "explicit_actual_option"}
    matched = [key for key, value in options.items() if compare_text(answer, [str(value)], question)["correct"] is True]
    if len(matched) == 1:
        return {**result, "prediction": matched[0], "reason": "unique_whole_option_text"}
    return {**result, "status": "review", "reason": "ambiguous_options" if matched else "no_matching_whole_option"}
