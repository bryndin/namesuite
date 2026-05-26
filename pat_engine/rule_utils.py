# -*- coding: utf-8 -*-
"""
engine/rule_utils.py

Utility functions for the linter validation engine.
"""

import difflib


def pango_escape(text: str) -> str:
    """Escapes XML special characters to prevent GTK Pango parsing crashes."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def generate_pango_diff(old_str: str, new_str: str) -> str:
    """
    Generates a Pango markup diff showing additions in green and deletions in red.
    Example: Ивано<span foreground='red'><s>чи</s></span><span foreground='green'>на</span>
    """
    old_esc = pango_escape(old_str)
    new_esc = pango_escape(new_str)

    if not old_esc:
        return f"<span foreground='green'>{new_esc}</span>" if new_esc else ""
    if not new_esc:
        return f"<span foreground='red'><s>{old_esc}</s></span>" if old_esc else ""

    matcher = difflib.SequenceMatcher(None, old_str, new_str)
    markup_parts = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            markup_parts.append(pango_escape(old_str[i1:i2]))
        elif tag == "replace":
            markup_parts.append(
                f"<span foreground='red'><s>{pango_escape(old_str[i1:i2])}</s></span>"
            )
            markup_parts.append(
                f"<span foreground='green'>{pango_escape(new_str[j1:j2])}</span>"
            )
        elif tag == "delete":
            markup_parts.append(
                f"<span foreground='red'><s>{pango_escape(old_str[i1:i2])}</s></span>"
            )
        elif tag == "insert":
            markup_parts.append(
                f"<span foreground='green'>{pango_escape(new_str[j1:j2])}</span>"
            )

    return "".join(markup_parts)


def swap_patronymic_gender(
    patronymic: str, to_male: bool, pre_reform: bool = False
) -> str:
    """Swaps the grammatical gender of an existing patronymic suffix."""
    if not patronymic:
        return patronymic

    if to_male:
        # Female to Male
        if patronymic.endswith("инична"):
            return patronymic[:-6] + "ич"
        elif patronymic.endswith("ична"):
            return patronymic[:-4] + "ич"
        elif patronymic.endswith("овна"):
            return patronymic[:-4] + "ович"
        elif patronymic.endswith("евна"):
            return patronymic[:-4] + "евич"
        elif patronymic.endswith("ова"):
            return patronymic[:-3] + ("овъ" if pre_reform else "ов")
        elif patronymic.endswith("ева"):
            return patronymic[:-3] + ("евъ" if pre_reform else "ев")
        elif patronymic.endswith("ина"):
            return patronymic[:-3] + ("инъ" if pre_reform else "ин")
    else:
        # Male to Female
        if patronymic.endswith("ович"):
            return patronymic[:-4] + "овна"
        elif patronymic.endswith("евич"):
            return patronymic[:-4] + "евна"
        elif patronymic.endswith("ич"):
            # Check soft contracted stem (Илья -> Ильинична)
            base = patronymic[:-2]
            if base.endswith("ь") or base.lower() in ("иль", "кузьм", "фом"):
                return base + "инична"
            return base + "ична"
        elif patronymic.endswith("овъ"):
            return patronymic[:-3] + "ова"
        elif patronymic.endswith("евъ"):
            return patronymic[:-3] + "ева"
        elif patronymic.endswith("инъ"):
            return patronymic[:-3] + "ина"
        elif patronymic.endswith("ов"):
            return patronymic[:-2] + "ова"
        elif patronymic.endswith("ев"):
            return patronymic[:-2] + "ева"
        elif patronymic.endswith("ин"):
            return patronymic[:-2] + "ина"

    return patronymic


def modern_to_archaic(patronymic: str, is_male: bool, pre_reform: bool = False) -> str:
    """Converts a modern formal patronymic to an archaic possessive genitive."""
    if not patronymic:
        return patronymic

    if is_male:
        if patronymic.endswith("ович"):
            return patronymic[:-4] + ("овъ" if pre_reform else "ов")
        elif patronymic.endswith("евич"):
            return patronymic[:-4] + ("евъ" if pre_reform else "ев")
        elif patronymic.endswith("ич"):
            return patronymic[:-2] + ("инъ" if pre_reform else "ин")
    else:
        if patronymic.endswith("овна"):
            return patronymic[:-4] + "ова"
        elif patronymic.endswith("евна"):
            return patronymic[:-4] + "ева"
        elif patronymic.endswith("ична"):
            return patronymic[:-4] + "ина"
        elif patronymic.endswith("инична"):
            return patronymic[:-6] + "ина"

    return patronymic


def archaic_to_modern(patronymic: str, is_male: bool) -> str:
    """Converts an archaic possessive genitive to a modern formal patronymic."""
    if not patronymic:
        return patronymic

    from pat_engine.morphology import normalize_to_modern

    # Strip terminal hard sign ъ
    pat = normalize_to_modern(patronymic)
    if is_male:
        if pat.endswith("ов"):
            return pat[:-2] + "ович"
        elif pat.endswith("ев"):
            return pat[:-2] + "евич"
        elif pat.endswith("ин"):
            return pat[:-2] + "ич"
    else:
        if pat.endswith("ова"):
            return pat[:-3] + "овна"
        elif pat.endswith("ева"):
            return pat[:-3] + "евна"
        elif pat.endswith("ина"):
            return pat[:-3] + "ична"

    return patronymic
