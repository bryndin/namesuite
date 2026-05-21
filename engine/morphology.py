# -*- coding: utf-8 -*-
"""
engine/morphology.py

Provides morphological generation of East Slavic patronymics (Russian, Ukrainian,
Belarusian) based on the father's given name, gender, reference year, and
orthographic script preferences.
"""

import re
from typing import Optional, Union, Tuple

# Sibilant characters that trigger -evich/-evna instead of -ovich/-ovna
SIBILANTS = set("жшчщцЖШЧЩЦ")

# Hard consonants for pre-reform terminal hard sign 'ъ' mapping
HARD_CONSONANTS = set("бвгджзклмнпрстфхцчшщБВГДЖЗКЛМНПРСТФХЦЧШЩ")

# Cyrillic vowels for pre-reform decimal 'і' replacement rules
CYRILLIC_VOWELS = set("аеиоуыэюяѣАЕИОУЫЭЮЯѢіІ")

# Slavic surname regex markers (Cyrillic and Latin transliterated)
# Expanded to include feminine Latin suffixes (ova, eva, ina, yna) and Cyrillic adjectival endings (ский, ская, цкий, цкая)
# Note: Intentionally excludes Polish endings like "ska" (e.g. Skladowska) to avoid false matches.
SLAVIC_SURNAME_PATTERN = re.compile(
    r"(ов|ев|ин|ын|енко|чук|ко|ова|ева|ина|ына|ский|ская|цкий|цкая|ov|ova|ev|eva|in|ina|yn|yna|enko|chuk|sky|skiy|skaya)$",
    re.IGNORECASE,
)


def apply_pre_reform_orthography(text: str) -> str:
    """
    Applies historical pre-1918 orthography rules to Cyrillic text:
    1. Replaces 'и' with 'і' if immediately followed by another vowel (e.g., Дмитріевичъ).
    2. Appends terminal hard sign 'ъ' to any word ending in a hard consonant (e.g., сынъ, Петровъ).
    """
    if not text:
        return text

    chars = list(text)
    # 1. Replace 'и' with 'і' before vowels
    for i in range(len(chars) - 1):
        if chars[i].lower() == "и" and chars[i + 1].lower() in CYRILLIC_VOWELS:
            chars[i] = "І" if chars[i].isupper() else "і"

    text = "".join(chars)

    # 2. Append terminal hard sign 'ъ' to words ending in hard consonants
    words = text.split(" ")
    reformed_words = []
    for word in words:
        if word and word[-1] in HARD_CONSONANTS:
            word = word + "ъ"
        reformed_words.append(word)

    return " ".join(reformed_words)


def normalize_to_modern(text: str) -> str:
    """
    Normalizes pre-reform Cyrillic text to modern characters to ensure
    consistent morphological stem parsing.
    """
    if not text:
        return text
    # Strip terminal pre-reform hard sign if present, as it is an orthographic artifact
    text = text.strip()
    while text.endswith(("ъ", "Ъ")):
        text = text[:-1].strip()

    # Replace pre-reform characters with modern equivalents
    replacements = {
        "і": "и",
        "І": "И",
        "ѣ": "е",
        "Ѣ": "Е",
        "ѳ": "ф",
        "Ѳ": "Ф",
        "ѵ": "и",
        "Ѵ": "И",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def parse_stem(father_name: str) -> Tuple[str, str, str]:
    """
    Analyzes the father's given name ending to classify the linguistic stem.

    Returns a tuple of:
        (stem_type, genitive_base, modern_formal_base)

    Stem Types:
        - "hard": Ends in standard hard consonant (e.g., Иван, Петр)
        - "sibilant": Ends in ж, ш, ч, щ, ц (e.g., Жорж)
        - "soft": Ends in ь (e.g., Игорь)
        - "yod_ii": Ends in -ий (e.g., Дмитрий, Василий)
        - "yod_ej": Ends in -ей, -ай, -ой (e.g., Сергей, Николай)
        - "contracted_ya": Ends in -ья (e.g., Илья)
        - "contracted_a": Ends in standard -а, -я (e.g., Никита, Фома)
    """
    name = father_name.strip()
    if not name:
        return ("hard", "", "")

    # Normalize pre-reform script characters for robust stem analysis
    name = normalize_to_modern(name)

    # Normalize case (Title Case)
    name = name[0].upper() + name[1:].lower() if len(name) > 1 else name.upper()

    # 1. Contracted soft vowel stems (e.g., Илья)
    if name.endswith("ья"):
        base = name[:-1]  # Strip "я" -> "Иль"
        return ("contracted_ya", base + "ин", base)

    # 2. Contracted hard vowel stems (e.g., Никита, Савва, Фома, Лука)
    elif name.endswith(("а", "я")) and not name.endswith("ия"):
        base = name[:-1]  # "Никит", "Савв", "Фом"
        return ("contracted_a", base + "ин", base)

    # 3. Yod stems ending in -ий (e.g., Дмитрий, Василий, Григорий)
    elif name.endswith("ий"):
        base_stem = name[:-2]  # Strip "ий"
        # Handle soft-yod shifts historically used in records
        if name.endswith(("лий", "рий", "ний", "тий", "сий")) and name != "Дмитрий":
            # Василий -> Василь-, Григорий -> Григорь-
            genitive_base = base_stem + "ьев"
            formal_base = base_stem + "ь"
        else:
            # Дмитрий -> Дмитри-
            genitive_base = base_stem + "иев"
            formal_base = base_stem + "и"
        return ("yod_ii", genitive_base, formal_base)

    # 4. Yod stems ending in other diphthongs (e.g., Сергей, Николай)
    elif name.endswith(("ей", "ай", "ой")):
        base = name[:-1]  # Strip "й" -> "Серге", "Никола"
        return ("yod_ej", base + "ев", base)

    # 5. Soft consonant stems (e.g., Игорь)
    elif name.endswith("ь"):
        base = name[:-1]  # Strip "ь" -> "Игор"
        return ("soft", base + "ев", base)

    # 6. Sibilant stems (e.g., Жорж, Фриц)
    elif name[-1] in SIBILANTS:
        return ("sibilant", name + "ев", name)

    # 7. Standard hard consonant stems (e.g., Иван, Михаил)
    else:
        return ("hard", name + "ов", name)


def generate_east_slavic_patronymic(
    father_name: str,
    gender: Union[str, int],
    year: Optional[int] = None,
    pre_reform_script: bool = False,
) -> Optional[str]:
    """
    Generates a patronymic name from the father's given name according to the
    specified epoch and orthography.

    Args:
        father_name (str): Given name of the father (e.g., "Иван", "Дмитрий").
        gender (str|int): Target's gender.
                          Supported: 'male', 'female', or Gramps constants (1=male, 0=female).
        year (int, optional): Reference year (Y_ref) calculated via resolution hierarchy.
                              Defaults to modern standard (Post-1917) if None.
        pre_reform_script (bool): If True, re-enables pre-1918 Cyrillic spelling rules.

    Returns:
        str: Correctly generated patronymic, or None if generation is impossible.
    """
    if not father_name or not father_name.strip():
        return None

    # Resolve gender string representation
    if isinstance(gender, int):
        if gender == 1:
            is_male = True
        elif gender == 0:
            is_male = False
        else:
            return None  # Unknown/undetermined gender cannot be safely morphed
    else:
        g_lower = gender.lower()
        if g_lower.startswith("m") or g_lower == "1":
            is_male = True
        elif g_lower.startswith("f") or g_lower == "0":
            is_male = False
        else:
            return None

    # Parse stem and bases
    stem_type, genitive_base, formal_base = parse_stem(father_name)

    # Determine Chronological Epoch (Pivot Windows)
    # Default to Post-1917 if year is unrecorded or metadata is missing
    epoch = "post_1917"
    if year is not None:
        if year < 1861:
            epoch = "pre_1861"
        elif 1861 <= year < 1917:
            epoch = "1861_1917"

    # Apply Epoch Strategies
    result = ""

    # 1. Pre-1861: Possessive Genitive with Status Relationship Clue
    if epoch == "pre_1861":
        base_part = genitive_base if is_male else genitive_base + "а"
        rel_word = "сын" if is_male else "дочь"
        result = f"{base_part} {rel_word}"

    # 2. 1861-1917: Direct Class-Agnostic Genitive Suffix (e.g. Иван Сергеев Коваль)
    elif epoch == "1861_1917":
        result = genitive_base if is_male else genitive_base + "а"

    # 3. Post-1917: Modern Formal Gender Suffix (-ovich / -ovna)
    else:
        if stem_type == "contracted_ya":
            # Илья -> Ильич / Ильинична
            result = formal_base + "ич" if is_male else formal_base + "инична"
        elif stem_type == "contracted_a":
            # Никита -> Никитич / Никитична
            # Фома -> Фомич / Фоминична
            if father_name.strip().lower() in ("фома", "лука"):
                result = formal_base + "ич" if is_male else formal_base + "инична"
            else:
                result = formal_base + "ич" if is_male else formal_base + "ична"
        elif stem_type in ("soft", "yod_ii", "yod_ej", "sibilant"):
            # Игорь -> Игоревич / Игоревна
            # Дмитрий -> Дмитриевич / Дмитриевна
            # Сергей -> Сергеевич / Сергеевна
            # Жорж -> Жоржевич / Жоржевна
            result = formal_base + "евич" if is_male else formal_base + "евна"
        else:  # hard stems (Иван)
            result = formal_base + "ович" if is_male else formal_base + "овна"

    # Apply historical orthography replacements if requested (Only valid pre-1918)
    if pre_reform_script and epoch != "post_1917":
        result = apply_pre_reform_orthography(result)

    return result
