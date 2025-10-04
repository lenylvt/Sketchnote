"""
Style tokens and design configuration for PDF rendering.

This module defines all design tokens including fonts, colors, sizes, spacing,
and other styling parameters used throughout the PDF generation system.

License: MIT
"""

from typing import Dict, Tuple
from dataclasses import dataclass


@dataclass
class FontConfig:
    """Font configuration with fallbacks."""
    heading: str = "Helvetica-Bold"  # Fallback: IBM Plex Sans not always available
    body: str = "Helvetica"  # Fallback: Inter not always available
    caption: str = "Helvetica-Oblique"
    code: str = "Courier"
    bold: str = "Helvetica-Bold"
    italic: str = "Helvetica-Oblique"
    bold_italic: str = "Helvetica-BoldOblique"


@dataclass
class FontSizes:
    """Font sizes in points."""
    h1: int = 32
    h2: int = 24
    h3: int = 18
    strong: int = 12
    body: int = 12
    caption: int = 10
    code: int = 10


@dataclass
class Colors:
    """Color palette in RGB tuples (0-1 range for ReportLab)."""
    
    # Brand
    brand_brown: Tuple[float, float, float] = (0.431, 0.388, 0.275)  # #6E6346
    
    # Text
    text_primary: Tuple[float, float, float] = (0.169, 0.169, 0.169)  # #2B2B2B
    text_muted: Tuple[float, float, float] = (0.416, 0.416, 0.416)  # #6A6A6A
    
    # Code
    code_bg: Tuple[float, float, float] = (0.961, 0.961, 0.961)  # #F5F5F5
    code_border: Tuple[float, float, float] = (0.898, 0.898, 0.898)  # #E5E5E5
    
    # Highlights
    highlight_yellow: Tuple[float, float, float] = (1.0, 0.961, 0.616)  # #FFF59D
    highlight_green: Tuple[float, float, float] = (0.725, 0.965, 0.792)  # #B9F6CA
    highlight_aqua: Tuple[float, float, float] = (0.655, 1.0, 0.922)  # #A7FFEB
    highlight_blue: Tuple[float, float, float] = (0.702, 0.898, 0.988)  # #B3E5FC
    highlight_cornflower: Tuple[float, float, float] = (0.816, 0.886, 1.0)  # #D0E2FF
    highlight_lavender: Tuple[float, float, float] = (0.882, 0.745, 0.906)  # #E1BEE7
    highlight_pink: Tuple[float, float, float] = (0.973, 0.733, 0.816)  # #F8BBD0
    highlight_peach: Tuple[float, float, float] = (1.0, 0.8, 0.737)  # #FFCCBC
    highlight_gray: Tuple[float, float, float] = (0.878, 0.878, 0.878)  # #E0E0E0
    
    # Colored text
    color_blue: Tuple[float, float, float] = (0.118, 0.533, 0.898)  # #1E88E5
    color_purple: Tuple[float, float, float] = (0.494, 0.341, 0.761)  # #7E57C2
    color_magenta: Tuple[float, float, float] = (0.925, 0.251, 0.478)  # #EC407A
    color_orange: Tuple[float, float, float] = (0.984, 0.549, 0.0)  # #FB8C00
    color_gold: Tuple[float, float, float] = (0.984, 0.753, 0.176)  # #FBC02D
    color_teal: Tuple[float, float, float] = (0.0, 0.537, 0.482)  # #00897B
    
    # Lines
    line_light: Tuple[float, float, float] = (0.839, 0.827, 0.808)  # #D6D3CE
    line_strong: Tuple[float, float, float] = (0.431, 0.388, 0.275)  # #6E6346
    
    # White and black
    white: Tuple[float, float, float] = (1.0, 1.0, 1.0)
    black: Tuple[float, float, float] = (0.0, 0.0, 0.0)


@dataclass
class Spacing:
    """Spacing values in points (base unit 8pt)."""
    base: int = 8
    small: int = 4
    medium: int = 8
    large: int = 16
    xlarge: int = 24
    
    # Specific use cases
    section_gap: int = 16
    paragraph_gap: int = 12
    list_indent: int = 20
    list_item_gap: int = 6
    code_padding: int = 8
    table_cell_padding: int = 6
    caption_gap: int = 4


@dataclass
class PageConfig:
    """Page size configurations in points (1 pt = 1/72 inch)."""
    
    # A4: 210 × 297 mm
    a4_width: float = 595.27  # 210mm in points
    a4_height: float = 841.89  # 297mm in points
    
    # LETTER: 8.5 × 11 inches
    letter_width: float = 612.0
    letter_height: float = 792.0
    
    default_margin_mm: float = 20.0
    
    @staticmethod
    def mm_to_points(mm: float) -> float:
        """Convert millimeters to points."""
        return mm * 2.83465
    
    @staticmethod
    def points_to_mm(points: float) -> float:
        """Convert points to millimeters."""
        return points / 2.83465


# Highlight color mapping
HIGHLIGHT_COLORS: Dict[str, Tuple[float, float, float]] = {
    "yellow": Colors.highlight_yellow,
    "green": Colors.highlight_green,
    "aqua": Colors.highlight_aqua,
    "blue": Colors.highlight_blue,
    "cornflower": Colors.highlight_cornflower,
    "lavender": Colors.highlight_lavender,
    "pink": Colors.highlight_pink,
    "peach": Colors.highlight_peach,
    "gray": Colors.highlight_gray,
}

# Text color mapping
TEXT_COLORS: Dict[str, Tuple[float, float, float]] = {
    "blue": Colors.color_blue,
    "purple": Colors.color_purple,
    "magenta": Colors.color_magenta,
    "orange": Colors.color_orange,
    "gold": Colors.color_gold,
    "teal": Colors.color_teal,
}

# List markers
LIST_MARKERS = {
    "bullet": "•",
    "task_unchecked": "☐",
    "task_checked": "☑",
    "toggle_collapsed": "▶",
    "toggle_expanded": "▼",
}

# Line widths
LINE_WIDTHS = {
    "thin": 0.5,
    "regular": 1.0,
    "thick": 2.0,
}

# Exercise area constants
EXERCISE_AREA = {
    "ruled_spacing": 12,  # points between lines
    "dotgrid_spacing": 10,  # points between dots
    "square_spacing": 14.17,  # 5mm in points
    "corner_radius": 4,  # rounded corner radius
    "dot_radius": 0.75,  # dot size for dotgrid
}


# Global style instances (singletons)
fonts = FontConfig()
font_sizes = FontSizes()
colors = Colors()
spacing = Spacing()
page_config = PageConfig()
