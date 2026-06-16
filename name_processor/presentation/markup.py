"""GTK-free Pango markup and formatting helpers."""


def pango_escape(text: str) -> str:
    """Escapes XML special characters to prevent GTK Pango parsing crashes."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def generate_pango_diff(old_str: str, new_str: str) -> str:
    """
    Generates a simple before/after diff in Pango markup.
    Format: <current> -> <suggested>
    Example: Иванович -> Ивановна
    """
    old_esc = pango_escape(old_str)
    new_esc = pango_escape(new_str)

    if not old_esc and not new_esc:
        return ""
    if not old_esc:
        return f"<span weight='bold'>{new_esc}</span>"
    if not new_esc:
        return f"{old_esc}"

    return f"{old_esc} → <span weight='bold'>{new_esc}</span>"


def format_confidence(score: float) -> str:
    """Formats a confidence score (0.0-1.0) as a percentage string."""
    return f"{int(score * 100)}%"
