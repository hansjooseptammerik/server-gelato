from __future__ import annotations

from reportlab.pdfbase import pdfmetrics



def fit_font_size(
    text: str,
    font_name: str,
    start_font_size: float,
    max_width: float,
    min_font_size: float = 8.0,
) -> float:
    current = float(start_font_size)
    if not text:
        return current
    while current > min_font_size:
        width = pdfmetrics.stringWidth(text, font_name, current)
        if width <= max_width:
            return current
        current -= 0.25
    return min_font_size
