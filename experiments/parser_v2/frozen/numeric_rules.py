"""Conservative scalar quantity equivalence, Python stdlib only.

No labels, IDs, judge verdicts, eval(), answer mining or item-specific exceptions.
Unsupported/ambiguous inputs return fallback, never a guessed numeric verdict.
This compares quantities, not compliance with a requested output-unit format.
"""
from dataclasses import dataclass, replace
from decimal import Decimal, InvalidOperation
from fractions import Fraction
import re

VERSION = "quantity-rules-v1"


class Unsupported(ValueError):
    pass


@dataclass(frozen=True)
class Unit:
    name: str
    dimension: str
    factor: Fraction


SYMBOLS = {}
WORDS = {}


def register(name, dimension, factor, symbols=(), words=()):
    unit = Unit(name, dimension, Fraction(factor))
    for value in symbols:
        SYMBOLS[value] = unit  # SI symbols are case sensitive: mg != Mg.
    for value in words:
        WORDS[value.lower()] = unit
    return unit


RATIO = register("ratio", "ratio", 1, words=("of the total", "of total", "of the whole"))
PERCENT = register("percent", "ratio", "1/100", symbols=("%",), words=("percent", "per cent", "percentage"))
register("permille", "ratio", "1/1000", symbols=("‰",), words=("per mille",))
for name, factor, symbols, words in [
    ("kg", "1", ("kg",), ("kilogram", "kilograms")),
    ("g", "1/1000", ("g",), ("gram", "grams")),
    ("mg", "1/1000000", ("mg",), ("milligram", "milligrams")),
    ("ug", "1/1000000000", ("ug", "µg", "μg"), ("microgram", "micrograms")),
    ("tonne", "1000", (), ("tonne", "tonnes", "metric ton", "metric tons")),
]:
    register(name, "mass", factor, symbols, words)
for name, factor, symbols, words in [
    ("m", "1", ("m",), ("meter", "meters", "metre", "metres")),
    ("km", "1000", ("km",), ("kilometer", "kilometers", "kilometre", "kilometres")),
    ("cm", "1/100", ("cm",), ("centimeter", "centimeters", "centimetre", "centimetres")),
    ("mm", "1/1000", ("mm",), ("millimeter", "millimeters", "millimetre", "millimetres")),
    ("um", "1/1000000", ("um", "µm", "μm"), ("micrometer", "micrometers", "micrometre", "micrometres")),
    ("inch", "127/5000", (), ("inch", "inches")),
    ("foot", "381/1250", (), ("foot", "feet")),
    ("mile", "201168/125", (), ("mile", "miles")),
]:
    register(name, "length", factor, symbols, words)
for name, factor, symbols, words in [
    ("L", "1", ("L", "l"), ("liter", "liters", "litre", "litres")),
    ("mL", "1/1000", ("mL", "ml"), ("milliliter", "milliliters", "millilitre", "millilitres")),
    ("uL", "1/1000000", ("uL", "µL", "μL"), ("microliter", "microliters", "microlitre", "microlitres")),
    ("m3", "1000", ("m3", "m^3", "m³"), ("cubic meter", "cubic meters", "cubic metre", "cubic metres")),
    ("cm3", "1/1000", ("cm3", "cm^3", "cm³"), ("cubic centimeter", "cubic centimeters", "cubic centimetre", "cubic centimetres")),
]:
    register(name, "volume", factor, symbols, words)
for symbol, factor, names in [
    ("m", "1", ("meter", "metre")), ("cm", "1/10000", ("centimeter", "centimetre")),
    ("mm", "1/1000000", ("millimeter", "millimetre")), ("km", "1000000", ("kilometer", "kilometre")),
]:
    register(symbol+"2", "area", factor, (symbol+"2", symbol+"^2", symbol+"²"),
             tuple("square "+n+s for n in names for s in ("", "s")))
for name, factor, symbols, words in [
    ("s", "1", ("s",), ("second", "seconds")),
    ("ms", "1/1000", ("ms",), ("millisecond", "milliseconds")),
    ("min", "60", ("min",), ("minute", "minutes")),
    ("h", "3600", ("h", "hr"), ("hour", "hours")),
    ("day", "86400", (), ("day", "days")),
    ("week", "604800", (), ("week", "weeks")),
]:
    register(name, "duration", factor, symbols, words)
# Calendar months/years, ambiguous gallons/tons, affine temperature and FX are unsupported.
for name, symbols, words in [
    ("USD", ("USD", "US$"), ("US dollar", "US dollars", "U.S. dollar", "U.S. dollars")),
    ("EUR", ("EUR", "€"), ("euro", "euros")),
    ("GBP", ("GBP", "£"), ("British pound", "British pounds", "pound sterling", "pounds sterling")),
    ("JPY", ("JPY",), ("Japanese yen",)),
    ("KRW", ("KRW",), ("South Korean won",)),
]:
    register(name, "currency:"+name, 1, symbols, words)
UNSPECIFIED_DOLLAR = register("unspecified_dollar", "currency:unspecified_dollar", 1, ("$",), ("dollar", "dollars"))


def clean(text):
    if not isinstance(text, str) or not text.strip() or len(text) > 512:
        raise Unsupported("empty_or_long_answer")
    text = text.strip().replace("−", "-").replace("\u00a0", " ")
    for _ in range(4):
        before = text
        for left, right in (("**", "**"), ("`", "`"), (r"\(", r"\)")):
            if text.startswith(left) and text.endswith(right) and len(text) > len(left)+len(right):
                text = text[len(left):-len(right)].strip()
                break
        if text == before:
            break
    # No stripping of currency, negation, bounds, units or arbitrary trailing words.
    return re.sub(r"\s+", " ", text)


def unit_for(text):
    text = re.sub(r"\s+", " ", text.strip())
    if text in SYMBOLS:
        return SYMBOLS[text]
    if text.lower() in WORDS:
        return WORDS[text.lower()]
    # A parenthesized identical unit alias is formatting, not a second quantity.
    match = re.fullmatch(r"([^()]+)\s*\(([^()]+)\)", text)
    if match:
        left, right = unit_for(match[1]), unit_for(match[2])
        if (left.dimension, left.factor) == (right.dimension, right.factor):
            return left
    raise Unsupported("unsupported_or_ambiguous_unit")


SMALL = dict(zip("zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split(), range(20)))
TENS = dict(zip("twenty thirty forty fifty sixty seventy eighty ninety".split(), range(20, 100, 10)))
SCALES = {"thousand": 1000, "million": 1000000, "billion": 1000000000, "trillion": 1000000000000}
DECIMAL = r"(?:\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?"
SIGNED = r"[+-]?" + DECIMAL
VALUE = re.compile(r"(?P<value>"+SIGNED+r"(?:\s*/\s*"+SIGNED+r")?)(?=$|[^\d.,+-])")
WORD_VALUE = re.compile(r"(?P<value>" + "|".join(sorted([*SMALL, *TENS], key=len, reverse=True)) + r")(?=$|\s|-)", re.I)


def exact_number(text):
    if "/" in text:
        parts = text.split("/")
        if len(parts) != 2:
            raise Unsupported("invalid_fraction")
        denominator = exact_number(parts[1].strip())
        if denominator == 0:
            raise Unsupported("zero_denominator")
        return exact_number(parts[0].strip()) / denominator
    text = text.strip()
    if not re.fullmatch(SIGNED, text) or len(re.sub(r"\D", "", text)) > 60:
        raise Unsupported("invalid_or_excessive_number")
    try:
        decimal = Decimal(text.replace(",", ""))
    except InvalidOperation as exc:
        raise Unsupported("invalid_number") from exc
    if abs(decimal.as_tuple().exponent) > 40 or not decimal.is_finite():
        raise Unsupported("numeric_exponent_limit")
    return Fraction(decimal)


def read_value(text):
    match = VALUE.match(text)
    if match:
        value, tail = exact_number(match["value"]), text[match.end():].strip()
    else:
        match = WORD_VALUE.match(text)
        if not match:
            raise Unsupported("not_a_supported_scalar")
        first = match["value"].lower()
        value = Fraction(SMALL[first] if first in SMALL else TENS[first])
        tail = text[match.end():].strip()
        if first in TENS:
            next_word = re.match(r"^-?\s*(one|two|three|four|five|six|seven|eight|nine)(?=$|\s)", tail, re.I)
            if next_word:
                value += SMALL[next_word[1].lower()]
                tail = tail[next_word.end():].strip()
    scale = re.match(r"^(thousand|million|billion|trillion)(?=$|\s)", tail, re.I)
    if scale:
        value *= SCALES[scale[1].lower()]
        tail = tail[scale.end():].strip()
    return value, tail


@dataclass(frozen=True)
class Quantity:
    value: Fraction
    unit: Unit | None
    unit_source: str
    literal: str


def parse_quantity(answer):
    text = clean(answer)
    # Complete simple LaTeX fractions are allowed; general formulas/CoT are not evaluated.
    fraction = re.fullmatch(r"\\(?:dfrac|frac)\{("+SIGNED+r")\}\{("+SIGNED+r")\}(.*)", text)
    if fraction:
        text = fraction[1] + "/" + fraction[2] + fraction[3]
    prefix = re.match(r"^([+-]?)\s*(US\$|USD|EUR|GBP|JPY|KRW|\$|€|£)\s*(.+)$", text)
    if prefix:
        signed_value = prefix[1] + prefix[3]
        value, suffix = read_value(signed_value)
        if suffix:
            raise Unsupported("extra_content_after_currency_amount")
        return Quantity(value, unit_for(prefix[2]), "explicit", answer)
    value, suffix = read_value(text)
    # Read a complete answer, never mine the first matching number from prose.
    unit = unit_for(suffix) if suffix else None
    return Quantity(value, unit, "explicit" if unit else "missing", answer)


UNIT_PATTERN = "|".join(re.escape(x) for x in sorted({*WORDS, *SYMBOLS}, key=len, reverse=True))
QUESTION_UNIT = re.compile(r"\b(?P<request>how many|expressed in|measured in|reported in|in)\s+(?P<unit>"+UNIT_PATTERN+r")(?![\w])", re.I)


def requested_unit(question):
    if not isinstance(question, str) or len(question) > 12000:
        raise Unsupported("invalid_question")
    found = []
    # These patterns name the requested dimensionless convention, not arbitrary % in context.
    if re.search(r"\b(?:what|which)\s+percent(?:age)?\b|\b(?:as|in)\s+(?:a\s+)?percent(?:age)?\b", question, re.I):
        found.append(PERCENT)
    elif re.search(r"\bwhat\s+fraction\b|\bwhat\s+proportion\b", question, re.I):
        found.append(RATIO)
    for m in QUESTION_UNIT.finditer(question):
        # 'in a liter of water' is context, not a request for liters in the answer.
        # The article form is excluded by QUESTION_UNIT; the plural form is below.
        if m["request"].lower() == "in" and re.match(r"\s+of\b", question[m.end():], re.I):
            raise Unsupported("incidental_unit_context")
        if re.match(r"\s*(?:/|per\b|or\b|and\b|squared\b|cubed\b|(?:a|each|every)\s+(?:second|minute|hour|day|week|month|year)\b)", question[m.end():], re.I):
            raise Unsupported("compound_or_alternative_requested_unit")
        found.append(unit_for(m["unit"]))
    found = list({(u.dimension, u.factor, u.name): u for u in found}.values())
    if len(found) > 1:
        raise Unsupported("multiple_requested_units")
    return found[0] if found else None


def resolve(q, context):
    if q.unit is None:
        return replace(q, unit=context, unit_source="question") if context else q
    if q.unit == UNSPECIFIED_DOLLAR and context and context.name == "USD":
        return replace(q, unit=context, unit_source="question_disambiguated_dollar")
    return q


def description(quantity):
    u = quantity.unit
    base_value = quantity.value * (u.factor if u else 1)
    return {"literal": quantity.literal, "value_fraction": str(quantity.value),
            "unit": u.name if u else None, "dimension": u.dimension if u else "bare_number",
            "unit_source": quantity.unit_source, "scale_to_base": str(u.factor) if u else "1",
            "base_value_fraction": str(base_value)}


def compare_quantities(question, reference, candidate):
    result = {"version": VERSION, "status": "fallback", "decision": None,
              "policy": "exact_quantity_equivalence_not_requested_output_format", "reason": None}
    try:
        if re.search(r"\bpercent(?:age)? points?\b", question, re.I):
            raise Unsupported("percentage_point_context_not_implemented")
        if re.search(r"\b(?:round(?:ed|ing)?|nearest|decimal places?|significant figures?|approximately|tolerance)\b", question, re.I):
            raise Unsupported("rounding_or_tolerance_not_implemented")
        if re.search(r"\b(?:what|which)\s+(?:year|date|article|chapter|page|version)\b|\b(?:phone|telephone|postcode|zip code|isbn|identifier|title|model number|serial number|flight number)\b", question, re.I):
            raise Unsupported("date_or_identifier_not_quantity")
        reference_q = parse_quantity(reference)
        candidate_q = parse_quantity(candidate)
        context = requested_unit(question)
        reference_q, candidate_q = resolve(reference_q, context), resolve(candidate_q, context)
        result.update(reference=description(reference_q), candidate=description(candidate_q),
                      requested_unit=context.name if context else None)
        a, b = reference_q.unit, candidate_q.unit
        if (a is None) != (b is None):
            raise Unsupported("missing_unit_not_established_by_question")
        if context and a and a.dimension != context.dimension:
            raise Unsupported("reference_conflicts_with_requested_dimension")
        if a and b and a.dimension != b.dimension:
            if "currency:unspecified_dollar" in {a.dimension, b.dimension}:
                raise Unsupported("dollar_currency_ambiguous")
            return {**result, "status": "decided", "decision": False, "reason": "dimension_or_currency_mismatch"}
        left = reference_q.value * (a.factor if a else 1)
        right = candidate_q.value * (b.factor if b else 1)
        equal = left == right
        return {**result, "status": "decided", "decision": equal,
                "reason": "exact_quantity_equivalent" if equal else "quantity_value_mismatch"}
    except (Unsupported, InvalidOperation, ZeroDivisionError) as exc:
        return {**result, "reason": str(exc)}


def hybrid_decide(question, reference, candidate, legacy_provider):
    """Provider is called ONLY on fallback; it gets no rule decision or target label.

    For this paired experiment, provider returns the already verified legacy record.
    A future live integration can call the unchanged legacy judge in this callback.
    """
    numeric = compare_quantities(question, reference, candidate)
    if numeric["status"] == "decided":
        return {"status": "judged", "decision": numeric["decision"], "route": "numeric_rules", "numeric": numeric}
    original = legacy_provider()
    if original["status"] not in {"judged", "invalid", "uncertain"} or type(original["decision"]) not in {bool, type(None)}:
        raise ValueError("Invalid legacy fallback")
    if (original["status"] == "judged") != (original["decision"] is not None):
        raise ValueError("Legacy status/decision mismatch")
    return {"status": original["status"], "decision": original["decision"],
            "route": "legacy", "numeric": numeric, "legacy_result": original}
