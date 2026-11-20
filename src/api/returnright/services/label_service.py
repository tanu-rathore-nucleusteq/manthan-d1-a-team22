"""Builds the mock return label: the return code as a QR code (SVG) and the warehouse address."""

import segno


def qr_svg(return_code: str) -> str:
    """An inline SVG document the browser can draw and print."""
    return segno.make(return_code, error="m", micro=False).svg_inline(scale=4, border=2)
