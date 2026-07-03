from typing import Optional
from pymorphy2 import MorphAnalyzer

morph = MorphAnalyzer()


def parse_full_name(full_name: str) -> dict:
    parts = full_name.strip().split()
    result = {"last": "", "first": "", "patronymic": ""}
    if len(parts) == 1:
        result["first"] = parts[0]
    elif len(parts) == 2:
        result["last"] = parts[0]
        result["first"] = parts[1]
    elif len(parts) >= 3:
        result["last"] = parts[0]
        result["first"] = parts[1]
        result["patronymic"] = parts[2]
    return result


def detect_gender(full_name: str) -> Optional[str]:
    parsed = parse_full_name(full_name)
    patronymic = parsed["patronymic"]
    if not patronymic:
        first = parsed["first"]
        if first:
            parsed_word = morph.parse(first)[0]
            if "femn" in parsed_word.tag:
                return "female"
            if "masc" in parsed_word.tag:
                return "male"
        return None
    parsed_word = morph.parse(patronymic)[0]
    if "femn" in parsed_word.tag:
        return "female"
    if "masc" in parsed_word.tag:
        return "male"
    return None


def get_display_name(full_name: str) -> str:
    parsed = parse_full_name(full_name)
    if parsed["first"] and parsed["patronymic"]:
        return f"{parsed['first']} {parsed['patronymic']}"
    return parsed["first"] or full_name
