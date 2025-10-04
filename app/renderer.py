"""
PDF rendering engine using ReportLab.

Handles document layout, pagination, and rendering of all content blocks
with deterministic, production-quality output.

License: MIT
"""

import io
import math
import os
import re
import tempfile
import urllib.request
from pathlib import Path
from typing import Dict, List, Tuple, Optional, List as ListType

import matplotlib
from matplotlib import mathtext, rcParams

matplotlib.use("Agg")
rcParams["mathtext.fontset"] = "stix"
rcParams["font.family"] = "STIXGeneral"

INLINE_MATH_PATTERN = re.compile(r"(?<!\\)\$(.+?)(?<!\\)\$")

from reportlab.lib.pagesizes import A4, LETTER
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from app.models import (
    Document, Block, Heading, Paragraph, Caption, ListBlock,
    Break, PageBreak, Code, Formula, Table, Image, ExerciseArea,
    RichText, ListItem, Meta
)
from app.styles import (
    fonts, font_sizes, colors, spacing, page_config,
    HIGHLIGHT_COLORS, TEXT_COLORS, LIST_MARKERS, LINE_WIDTHS, EXERCISE_AREA
)


def download_google_font(font_family: str, cache_dir: str = None) -> dict:
    """
    Download Google Font TTF files and return paths for different styles.
    
    Args:
        font_family: Google Font family name (e.g., 'Roboto', 'Open Sans')
        cache_dir: Directory to cache downloaded fonts (default: temp)
        
    Returns:
        Dictionary with paths to regular, bold, italic, bold-italic variants
    """
    if cache_dir is None:
        cache_dir = os.path.join(tempfile.gettempdir(), 'pdf_fonts')
    
    os.makedirs(cache_dir, exist_ok=True)
    
    # Replace spaces with plus signs for URL
    font_name_url = font_family.replace(' ', '+')
    
    # Google Fonts CSS API
    css_url = f"https://fonts.googleapis.com/css2?family={font_name_url}:ital,wght@0,400;0,700;1,400;1,700&display=swap"
    
    font_files = {}
    
    try:
        # Download CSS to get TTF URLs
        with urllib.request.urlopen(css_url) as response:
            css_content = response.read().decode('utf-8')
        
        # Parse CSS to find TTF URLs (simplified parser)
        import re
        ttf_urls = re.findall(r'url\(([^)]+\.ttf)\)', css_content)
        
        if not ttf_urls:
            raise ValueError(f"No TTF files found for font '{font_family}'")
        
        # Download each variant
        variants = ['regular', 'bold', 'italic', 'bold-italic']
        for i, ttf_url in enumerate(ttf_urls[:4]):  # Get up to 4 variants
            variant = variants[i] if i < len(variants) else 'regular'
            
            # Create safe filename
            font_filename = f"{font_family.replace(' ', '_')}_{variant}.ttf"
            font_path = os.path.join(cache_dir, font_filename)
            
            # Download if not cached
            if not os.path.exists(font_path):
                with urllib.request.urlopen(ttf_url) as response:
                    font_data = response.read()
                with open(font_path, 'wb') as f:
                    f.write(font_data)
            
            font_files[variant] = font_path
        
        # Ensure we have at least regular
        if 'regular' not in font_files and font_files:
            font_files['regular'] = list(font_files.values())[0]
        
        return font_files
        
    except Exception as e:
        print(f"Warning: Failed to download Google Font '{font_family}': {e}")
        return {}


class PDFRenderer:
    """
    Renders a structured document to PDF using ReportLab.
    
    Maintains cursor position, handles pagination, and renders all block types.
    """
    
    def __init__(self, document: Document):
        """
        Initialize renderer with document.
        
        Args:
            document: Document model containing meta and blocks
        """
        self.document = document
        self.buffer = io.BytesIO()

        # Math rendering utilities
        self._math_parser = mathtext.MathTextParser("agg")
        self._math_dpi = 300
        self._math_cache: Dict[Tuple[str, float, Tuple[float, float, float]], Tuple[bytes, float, float, float]] = {}
        self._math_metrics_cache: Dict[Tuple[str, float], Tuple[float, float, float]] = {}
        
        # Page configuration
        if document.meta.page_size == "A4":
            self.page_width = page_config.a4_width
            self.page_height = page_config.a4_height
        else:  # LETTER
            self.page_width = page_config.letter_width
            self.page_height = page_config.letter_height
        
        margin_pts = page_config.mm_to_points(document.meta.margin_mm)
        self.margin_left = margin_pts
        self.margin_right = margin_pts
        self.margin_top = margin_pts
        self.margin_bottom = margin_pts
        
        # Content area
        self.content_width = self.page_width - self.margin_left - self.margin_right
        self.content_height = self.page_height - self.margin_top - self.margin_bottom
        
        # Cursor position (y coordinate, grows downward from top)
        self.y = self.page_height - self.margin_top
        self.x = self.margin_left
        
        # Custom fonts
        self.custom_fonts = fonts  # Default fonts from styles
        
        # Download and register Google Font if specified
        if document.meta.font_family:
            try:
                font_files = download_google_font(document.meta.font_family)
                
                if font_files:
                    # Register fonts with ReportLab
                    font_base_name = document.meta.font_family.replace(' ', '')
                    
                    if 'regular' in font_files:
                        pdfmetrics.registerFont(TTFont(f'{font_base_name}-Regular', font_files['regular']))
                        self.custom_fonts.body = f'{font_base_name}-Regular'
                        self.custom_fonts.heading = f'{font_base_name}-Regular'
                    
                    if 'bold' in font_files:
                        pdfmetrics.registerFont(TTFont(f'{font_base_name}-Bold', font_files['bold']))
                        self.custom_fonts.bold = f'{font_base_name}-Bold'
                    elif 'regular' in font_files:
                        self.custom_fonts.bold = f'{font_base_name}-Regular'
                    
                    if 'italic' in font_files:
                        pdfmetrics.registerFont(TTFont(f'{font_base_name}-Italic', font_files['italic']))
                        self.custom_fonts.italic = f'{font_base_name}-Italic'
                        self.custom_fonts.caption = f'{font_base_name}-Italic'
                    elif 'regular' in font_files:
                        self.custom_fonts.italic = f'{font_base_name}-Regular'
                        self.custom_fonts.caption = f'{font_base_name}-Regular'
                    
                    if 'bold-italic' in font_files:
                        pdfmetrics.registerFont(TTFont(f'{font_base_name}-BoldItalic', font_files['bold-italic']))
                        self.custom_self.custom_fonts.bold_italic = f'{font_base_name}-BoldItalic'
                    elif 'bold' in font_files:
                        self.custom_self.custom_fonts.bold_italic = self.custom_fonts.bold
                    elif 'italic' in font_files:
                        self.custom_self.custom_fonts.bold_italic = self.custom_fonts.italic
                    else:
                        self.custom_self.custom_fonts.bold_italic = self.custom_fonts.body
                    
                    print(f"Successfully loaded Google Font: {document.meta.font_family}")
                else:
                    print(f"Warning: Could not load Google Font '{document.meta.font_family}', using defaults")
            
            except Exception as e:
                print(f"Error loading Google Font: {e}")
        
        # Canvas
        self.c = canvas.Canvas(self.buffer, pagesize=(self.page_width, self.page_height))
        
        # Set metadata
        if document.meta.title:
            self.c.setTitle(document.meta.title)
        if document.meta.author:
            self.c.setAuthor(document.meta.author)
        
        # List counters (for numbered lists)
        self.list_counter = 0
    
    def render(self) -> bytes:
        """
        Render the complete document to PDF.
        
        Returns:
            PDF bytes
        """
        # Render all blocks
        for block in self.document.blocks:
            self._render_block(block)
        
        # Finalize
        self.c.save()
        return self.buffer.getvalue()
    
    def _render_block(self, block: Block):
        """Render a single block based on its type."""
        if isinstance(block, Heading):
            self._render_heading(block)
        elif isinstance(block, Paragraph):
            self._render_paragraph(block)
        elif isinstance(block, Caption):
            self._render_caption(block)
        elif isinstance(block, ListBlock):
            self._render_list(block)
        elif isinstance(block, Break):
            self._render_break(block)
        elif isinstance(block, PageBreak):
            self._render_page_break()
        elif isinstance(block, Code):
            self._render_code(block)
        elif isinstance(block, Formula):
            self._render_formula(block)
        elif isinstance(block, Table):
            self._render_table(block)
        elif isinstance(block, Image):
            self._render_image(block)
        elif isinstance(block, ExerciseArea):
            self._render_exercise_area(block)
    
    def _check_page_break(self, required_height: float):
        """Check if we need a page break and create one if necessary."""
        if self.y - required_height < self.margin_bottom:
            self.c.showPage()
            self.y = self.page_height - self.margin_top
    
    def _render_heading(self, heading: Heading):
        """Render a heading block with rich text support."""
        # Map level to font size
        size_map = {1: font_sizes.h1, 2: font_sizes.h2, 3: font_sizes.h3}
        font_size = size_map[heading.level]
        
        # Check space (estimate max 3 lines for headings)
        self._check_page_break(font_size * 3 + spacing.section_gap)
        
        # Move down for spacing
        self.y -= spacing.section_gap
        
        # Render rich text with wrapping
        lines = self._wrap_rich_text(heading.text, self.content_width, font_size)
        
        for line_spans in lines:
            x_offset = self.x
            for span in line_spans:
                x_offset = self._render_rich_text_span(span, x_offset, self.y, font_size, use_black=True)
            self.y -= font_size + 4
        
        self.y -= spacing.paragraph_gap - 4
        
        # Reset color
        self.c.setFillColorRGB(*colors.text_primary)
    
    def _render_paragraph(self, paragraph: Paragraph):
        """Render a paragraph block with rich text support, wrapping, and justification."""
        # Estimate lines needed (conservative)
        self._check_page_break(font_sizes.body * 5)
        
        self.y -= spacing.paragraph_gap
        
        # Wrap rich text and render line by line with justification
        lines = self._wrap_rich_text(paragraph.text, self.content_width, font_sizes.body)
        
        for line_idx, line_spans in enumerate(lines):
            is_last_line = (line_idx == len(lines) - 1)
            
            # Calculate total text width for justification
            if len(lines) > 1 and not is_last_line:
                # Justify (except last line)
                total_text_width = 0.0
                for span in line_spans:
                    if getattr(span, "math", False):
                        total_text_width += self._measure_math_width(span.text, font_sizes.body)
                    else:
                        total_text_width += self.c.stringWidth(span.text, self._get_font_name(span), font_sizes.body)
                extra_space = (self.content_width - total_text_width) / max(len(line_spans) - 1, 1)
            else:
                # Left align for single-line or last line
                extra_space = 0
            
            x_offset = self.x
            for span_idx, span in enumerate(line_spans):
                x_offset = self._render_rich_text_span(span, x_offset, self.y, font_sizes.body)
                # Add extra space between words for justification
                if extra_space > 0 and span_idx < len(line_spans) - 1:
                    x_offset += extra_space
            
            self.y -= font_sizes.body + 4
        
        self.y -= spacing.paragraph_gap - 4
    
    def _get_font_name(self, span: RichText) -> str:
        """Get font name for a rich text span."""
        if span.code:
            return self.custom_fonts.code
        elif span.bold and span.italic:
            return self.custom_fonts.bold_italic
        elif span.bold:
            return self.custom_fonts.bold
        elif span.italic:
            return self.custom_fonts.italic
        else:
            return self.custom_fonts.body

    def _resolve_span_color(self, span: RichText, use_black: bool = False) -> Tuple[float, float, float]:
        """Determine the RGB color for a span."""
        if use_black:
            return (0.0, 0.0, 0.0)
        if span.color and span.color in TEXT_COLORS:
            return TEXT_COLORS[span.color]
        return colors.text_primary

    @staticmethod
    def _color_tuple_to_hex(color: Tuple[float, float, float]) -> str:
        """Convert an RGB tuple (0-1) to hex string."""
        r, g, b = [max(0, min(255, int(round(component * 255)))) for component in color]
        return f"#{r:02x}{g:02x}{b:02x}"

    def _expand_inline_spans(self, spans: ListType[RichText]) -> ListType[RichText]:
        """Expand spans to isolate inline math segments."""
        expanded: ListType[RichText] = []
        for span in spans:
            expanded.extend(self._split_span_for_inline_math(span))
        return expanded

    def _split_span_for_inline_math(self, span: RichText) -> ListType[RichText]:
        """Split a span into text and inline math segments."""
        if getattr(span, "math", False):
            return [span]

        text = span.text
        if not text or '$' not in text:
            return [span]

        placeholder = "\uF8FF"
        sanitized = text.replace("\\$", placeholder)

        segments: ListType[RichText] = []
        last_index = 0
        for match in INLINE_MATH_PATTERN.finditer(sanitized):
            start, end = match.span()
            if start > last_index:
                prefix = sanitized[last_index:start].replace(placeholder, '$')
                if prefix:
                    segments.append(span.model_copy(update={"text": prefix, "math": False}))
            formula = match.group(1)
            if formula:
                segments.append(span.model_copy(update={"text": formula.replace(placeholder, '$'), "math": True}))
            last_index = end

        if not segments:
            return [span]

        if last_index < len(sanitized):
            suffix = sanitized[last_index:].replace(placeholder, '$')
            if suffix:
                segments.append(span.model_copy(update={"text": suffix, "math": False}))

        return segments if segments else [span]

    def _format_math_expression(self, latex: str) -> str:
        """Ensure math expression is wrapped for MathText."""
        expr = latex.strip()
        if not expr:
            return ""
        if expr.startswith('$$') and expr.endswith('$$'):
            return expr
        if expr.startswith('$') and expr.endswith('$'):
            return expr
        if expr.startswith('\\[') and expr.endswith('\\]'):
            return f"$${expr[2:-2]}$$"
        if expr.startswith('\\(') and expr.endswith('\\)'):
            return f"${expr[2:-2]}$"
        return f"${expr}$"

    def _get_math_metrics(self, latex: str, font_size: float) -> Tuple[float, float, float]:
        """Get width, height, depth for math expression in points."""
        key = (latex, font_size)
        if key in self._math_metrics_cache:
            return self._math_metrics_cache[key]

        expr = self._format_math_expression(latex)
        if not expr:
            metrics = (0.0, 0.0, 0.0)
        else:
            buffer = io.BytesIO()
            try:
                width_px, height_px, depth_px = self._math_parser.to_png(
                    buffer,
                    expr,
                    dpi=self._math_dpi,
                    fontsize=font_size,
                    color='black'
                )
            except Exception as error:
                print(f"Warning: failed to measure math expression '{latex}': {error}")
                width_px = height_px = depth_px = 0
            finally:
                buffer.close()

            width_pt = width_px * 72.0 / self._math_dpi
            height_pt = height_px * 72.0 / self._math_dpi
            depth_pt = depth_px * 72.0 / self._math_dpi
            metrics = (width_pt, height_pt, depth_pt)

        self._math_metrics_cache[key] = metrics
        return metrics

    def _get_math_image(self, latex: str, font_size: float, color: Tuple[float, float, float]) -> Tuple[bytes, float, float, float]:
        """Render math expression to image bytes with metrics."""
        key = (latex, font_size, color)
        if key in self._math_cache:
            return self._math_cache[key]

        expr = self._format_math_expression(latex)
        if not expr:
            data = (b"", 0.0, 0.0, 0.0)
        else:
            buffer = io.BytesIO()
            hex_color = self._color_tuple_to_hex(color)
            try:
                width_px, height_px, depth_px = self._math_parser.to_png(
                    buffer,
                    expr,
                    dpi=self._math_dpi,
                    fontsize=font_size,
                    color=hex_color
                )
            except Exception as error:
                print(f"Warning: failed to render math expression '{latex}': {error}")
                buffer.close()
                self._math_cache[key] = (b"", 0.0, 0.0, 0.0)
                return self._math_cache[key]

            img_bytes = buffer.getvalue()
            buffer.close()

            width_pt = width_px * 72.0 / self._math_dpi
            height_pt = height_px * 72.0 / self._math_dpi
            depth_pt = depth_px * 72.0 / self._math_dpi
            data = (img_bytes, width_pt, height_pt, depth_pt)

            self._math_metrics_cache.setdefault((latex, font_size), (width_pt, height_pt, depth_pt))

        self._math_cache[key] = data
        return data

    def _measure_math_width(self, latex: str, font_size: float) -> float:
        """Measure inline math width in points."""
        width, _, _ = self._get_math_metrics(latex, font_size)
        return width

    def _render_inline_math_span(self, span: RichText, x: float, y: float,
                                  base_size: float, use_black: bool = False) -> float:
        """Render inline math and return new x position."""
        color_rgb = self._resolve_span_color(span, use_black)
        img_bytes, width_pt, height_pt, depth_pt = self._get_math_image(span.text, base_size, color_rgb)

        if not img_bytes or width_pt == 0:
            return x

        baseline_y = y - base_size
        bottom_y = baseline_y - depth_pt

        if span.highlight and span.highlight in HIGHLIGHT_COLORS:
            highlight_color = HIGHLIGHT_COLORS[span.highlight]
            padding = 1
            self.c.saveState()
            self.c.setFillColorRGB(highlight_color[0], highlight_color[1], highlight_color[2], alpha=0.35)
            self.c.roundRect(
                x - padding,
                bottom_y - padding,
                width_pt + padding * 2,
                height_pt + padding * 2,
                2,
                fill=1,
                stroke=0
            )
            self.c.restoreState()

        image_reader = ImageReader(io.BytesIO(img_bytes))
        self.c.drawImage(
            image_reader,
            x,
            bottom_y,
            width=width_pt,
            height=height_pt,
            mask='auto'
        )

        return x + width_pt

    def _render_inline_sequence(self, spans: ListType[RichText], x: float, y: float,
                                 base_size: float, use_black: bool = False) -> float:
        """Render a sequence of spans (with inline math support)."""
        for segment in self._expand_inline_spans(spans):
            x = self._render_rich_text_span(segment, x, y, base_size, use_black)
        return x
    
    def _render_caption(self, caption: Caption):
        """Render a caption block (small italic text)."""
        self._check_page_break(font_sizes.caption * 2)
        
        self.y -= spacing.caption_gap
        
        self.c.setFont(self.custom_fonts.caption, font_sizes.caption)
        self.c.setFillColorRGB(*colors.text_muted)
        
        text = "".join([span.text for span in caption.text])
        self.c.drawString(self.x, self.y - font_sizes.caption, text)
        
        self.y -= font_sizes.caption + spacing.caption_gap
        
        self.c.setFillColorRGB(*colors.text_primary)
    
    def _render_rich_text_span(self, span: RichText, x: float, y: float, 
                                base_size: float, use_black: bool = False) -> float:
        """
        Render a single rich text span and return new x position.
        
        Args:
            span: RichText span to render
            x: Current x position
            y: Current y position (baseline reference)
            base_size: Base font size
            use_black: Force black color (for headings)
        
        Returns:
            New x position after rendering
        """
        if not span.text:
            return x

        if getattr(span, "math", False):
            return self._render_inline_math_span(span, x, y, base_size, use_black)

        font_name = self._get_font_name(span)
        self.c.setFont(font_name, base_size)
        text_width = self.c.stringWidth(span.text, font_name, base_size)

        if text_width == 0:
            return x

        if span.highlight and span.highlight in HIGHLIGHT_COLORS:
            highlight_color = HIGHLIGHT_COLORS[span.highlight]
            padding = 1
            self.c.saveState()
            self.c.setFillColorRGB(highlight_color[0], highlight_color[1], highlight_color[2], alpha=0.35)
            self.c.roundRect(
                x - padding,
                y - base_size - padding,
                text_width + padding * 2,
                base_size + padding * 2,
                2,
                fill=1,
                stroke=0
            )
            self.c.restoreState()

        color_rgb = self._resolve_span_color(span, use_black)
        self.c.setFillColorRGB(*color_rgb)
        self.c.drawString(x, y - base_size, span.text)

        return x + text_width
    
    def _wrap_rich_text(self, spans: ListType[RichText], max_width: float,
                        font_size: float) -> ListType[ListType[RichText]]:
        """Wrap rich text spans across multiple lines (with inline math)."""
        lines: ListType[ListType[RichText]] = []
        current_line: ListType[RichText] = []
        current_width = 0.0

        for span in self._expand_inline_spans(spans):
            if span.text == "":
                continue

            if getattr(span, "math", False):
                tokens = [span]
            else:
                parts = re.split(r'(\s+)', span.text)
                tokens = [span.model_copy(update={"text": part}) for part in parts if part]

            for token in tokens:
                token_text = token.text
                if token_text == "":
                    continue

                is_math = getattr(token, "math", False)
                is_space = token_text.isspace()

                if is_math:
                    token_width = self._measure_math_width(token.text, font_size)
                else:
                    font_name = self._get_font_name(token)
                    token_width = self.c.stringWidth(token_text, font_name, font_size)

                if token_width == 0:
                    continue

                if current_width + token_width > max_width and current_line and not (is_space and len(current_line) == 0):
                    lines.append(current_line)
                    current_line = []
                    current_width = 0.0

                    if is_space:
                        continue

                    if not is_math and token_text.startswith(' '):
                        trimmed = token_text.lstrip()
                        if not trimmed:
                            continue
                        token = token.model_copy(update={"text": trimmed})
                        font_name = self._get_font_name(token)
                        token_width = self.c.stringWidth(token.text, font_name, font_size)

                if is_space and not current_line:
                    continue

                current_line.append(token)
                current_width += token_width

        if current_line:
            lines.append(current_line)

        return lines if lines else [[RichText(text="")]]
    
    def _render_list(self, list_block: ListBlock):
        """Render a list block (bullet, number, task, toggle)."""
        self._check_page_break(font_sizes.body * 3)
        
        self.y -= spacing.section_gap
        
        # Reset counter for numbered lists
        if list_block.variant == "number":
            self.list_counter = 1
        
        for item in list_block.items:
            self._render_list_item(item, list_block.variant, 0)
        
        self.y -= spacing.paragraph_gap
    
    def _render_list_item(self, item: ListItem, variant: str, indent_level: int):
        """Render a single list item."""
        indent = self.x + (indent_level * spacing.list_indent)
        
        self._check_page_break(font_sizes.body * 2)
        
        # Render marker
        marker = ""
        marker_color = colors.text_primary
        
        if variant == "bullet":
            marker = LIST_MARKERS["bullet"]
        elif variant == "number":
            marker = f"{self.list_counter}."
            self.list_counter += 1
        elif variant == "task":
            # Draw custom checkboxes with better styling
            box_size = 10
            box_y = self.y - font_sizes.body + 2
            
            # Draw checkbox outline (lighter color)
            self.c.setStrokeColorRGB(*colors.line_light)
            self.c.setLineWidth(1)
            self.c.roundRect(indent, box_y, box_size, box_size, 2, stroke=1, fill=0)
            
            # If checked, draw checkmark
            if item.checked:
                self.c.setStrokeColorRGB(*colors.brand_brown)
                self.c.setLineWidth(1.5)
                # Draw checkmark
                self.c.line(indent + 2, box_y + 5, indent + 4, box_y + 2)
                self.c.line(indent + 4, box_y + 2, indent + 8, box_y + 8)
            
            marker = ""  # Don't use text marker
        elif variant == "toggle":
            marker = LIST_MARKERS["toggle_expanded"] if item.children else LIST_MARKERS["toggle_collapsed"]
            marker_color = colors.text_muted
        
        # Draw text marker if present
        if marker:
            self.c.setFont(self.custom_fonts.body, font_sizes.body)
            self.c.setFillColorRGB(*marker_color)
            self.c.drawString(indent, self.y - font_sizes.body, marker)
        
        # Render item text
        if item.text:
            self._render_inline_sequence(item.text, indent + spacing.list_indent, self.y, font_sizes.body)
        
        self.y -= font_sizes.body + spacing.list_item_gap
        
        # Render children (with slightly more indent for nested items)
        if item.children:
            for child in item.children:
                self._render_list_item(child, variant, indent_level + 1)
    
    def _render_break(self, break_block: Break):
        """Render an ornamental break (only rounded dots style)."""
        self._check_page_break(30)
        
        self.y -= spacing.section_gap
        
        center_x = self.x + self.content_width / 2
        
        # Always use delicate dots pattern (rounded style)
        self.c.setFillColorRGB(*colors.line_light)
        
        # Three small circles
        for i in range(3):
            x_pos = center_x - 10 + i * 10
            self.c.circle(x_pos, self.y - 5, 1.5, stroke=0, fill=1)
        
        self.y -= 20 + spacing.section_gap
    
    def _render_page_break(self):
        """Force a new page."""
        self.c.showPage()
        self.y = self.page_height - self.margin_top
    
    def _render_code(self, code_block: Code):
        """Render a code block."""
        lines = code_block.content.split('\n')
        line_height = font_sizes.code + 4
        block_height = len(lines) * line_height + spacing.code_padding * 2
        
        self._check_page_break(block_height + spacing.section_gap)
        
        self.y -= spacing.section_gap
        
        # Background with rounded corners
        self.c.setFillColorRGB(*colors.code_bg)
        self.c.setStrokeColorRGB(*colors.code_border)
        self.c.setLineWidth(0.5)
        self.c.roundRect(self.x, self.y - block_height, self.content_width, block_height,
                        6, fill=1, stroke=1)  # 6pt corner radius
        
        # Code text
        self.c.setFillColorRGB(*colors.text_primary)
        self.c.setFont(self.custom_fonts.code, font_sizes.code)
        
        text_y = self.y - spacing.code_padding - font_sizes.code
        for line in lines:
            self.c.drawString(self.x + spacing.code_padding, text_y, line)
            text_y -= line_height
        
        self.y -= block_height + spacing.section_gap
    
    def _render_formula(self, formula: Formula):
        """Render a math formula using matplotlib's mathtext engine."""
        latex = formula.latex.strip()
        if not latex:
            return

        font_size = font_sizes.body * 1.1
        _, height_pt, _ = self._get_math_metrics(latex, font_size)
        required_height = height_pt + spacing.section_gap * 2
        self._check_page_break(required_height)

        self.y -= spacing.section_gap

        color_rgb = colors.text_primary
        img_bytes, width_pt, height_pt, _ = self._get_math_image(latex, font_size, color_rgb)

        if not img_bytes or width_pt == 0:
            # Fallback: render plain text
            self.c.setFont(self.custom_fonts.body, font_sizes.body)
            self.c.setFillColorRGB(*color_rgb)
            self.c.drawString(self.x, self.y - font_sizes.body, latex)
            self.y -= font_sizes.body + spacing.section_gap
            return

        x_centered = self.x + (self.content_width - width_pt) / 2
        y_bottom = self.y - height_pt

        image_reader = ImageReader(io.BytesIO(img_bytes))
        self.c.drawImage(
            image_reader,
            x_centered,
            y_bottom,
            width=width_pt,
            height=height_pt,
            mask='auto'
        )

        self.y = y_bottom - spacing.section_gap
    
    def _render_table(self, table: Table):
        """Render a table with improved styling."""
        # Calculate column widths
        if table.widths:
            total_ratio = sum(table.widths)
            col_widths = [(w / total_ratio) * self.content_width for w in table.widths]
        else:
            col_width = self.content_width / table.columns
            col_widths = [col_width] * table.columns
        
        # Estimate row heights (increased padding for better readability)
        row_height = font_sizes.body + spacing.table_cell_padding * 3
        table_height = len(table.rows) * row_height
        
        self._check_page_break(table_height + spacing.section_gap)
        
        self.y -= spacing.section_gap
        
        # Draw table with outer rounded rectangle
        start_y = self.y
        current_y = self.y
        
        # Draw outer border with rounded corners
        self.c.setStrokeColorRGB(*colors.line_light)
        self.c.setLineWidth(1.0)
        self.c.roundRect(self.x, current_y - table_height, self.content_width, table_height,
                        4, fill=0, stroke=1)
        
        # Draw rows
        for row_idx, row in enumerate(table.rows):
            current_x = self.x
            
            # Header row background (first row)
            if row_idx == 0:
                self.c.setFillColorRGB(0.97, 0.97, 0.97)  # Very light gray
                self.c.rect(self.x, current_y - row_height, self.content_width, row_height,
                           fill=1, stroke=0)
            
            # Draw cells
            for col_idx, cell in enumerate(row.cells):
                # Draw vertical separators (except first and last)
                if col_idx > 0:
                    self.c.setStrokeColorRGB(*colors.line_light)
                    self.c.setLineWidth(0.5)
                    self.c.line(current_x, current_y, current_x, current_y - row_height)
                
                # Cell text with rich text support
                if cell:
                    x_offset = current_x + spacing.table_cell_padding
                    text_y = current_y - row_height / 2 - font_sizes.body / 2 + 2
                    self._render_inline_sequence(cell, x_offset, text_y + font_sizes.body, font_sizes.body)
                
                current_x += col_widths[col_idx]
            
            # Draw horizontal separator (except last row)
            if row_idx < len(table.rows) - 1:
                self.c.setStrokeColorRGB(*colors.line_light)
                self.c.setLineWidth(0.5)
                self.c.line(self.x, current_y - row_height, self.x + self.content_width, current_y - row_height)
            
            current_y -= row_height
        
        self.y = current_y - spacing.section_gap
    
    def _render_image(self, image: Image):
        """Render an embedded image."""
        try:
            # Download or open image
            if image.src.startswith(('http://', 'https://')):
                with urllib.request.urlopen(image.src) as response:
                    img_data = response.read()
                    img = ImageReader(io.BytesIO(img_data))
            else:
                img = ImageReader(image.src)
            
            # Get image dimensions
            img_width, img_height = img.getSize()
            
            # Calculate display size
            if image.width_mm and image.height_mm:
                display_width = page_config.mm_to_points(image.width_mm)
                display_height = page_config.mm_to_points(image.height_mm)
            elif image.width_mm:
                display_width = page_config.mm_to_points(image.width_mm)
                display_height = display_width * (img_height / img_width)
            elif image.height_mm:
                display_height = page_config.mm_to_points(image.height_mm)
                display_width = display_height * (img_width / img_height)
            else:
                # Default: fit to content width
                display_width = min(self.content_width, img_width)
                display_height = display_width * (img_height / img_width)
            
            self._check_page_break(display_height + spacing.section_gap)
            
            self.y -= spacing.section_gap
            
            # Center image
            x_centered = self.x + (self.content_width - display_width) / 2
            
            self.c.drawImage(img, x_centered, self.y - display_height,
                           width=display_width, height=display_height,
                           preserveAspectRatio=True, mask='auto')
            
            self.y -= display_height + spacing.section_gap
        
        except Exception as e:
            # Fallback: render error message
            self.c.setFont(self.custom_fonts.italic, font_sizes.caption)
            self.c.setFillColorRGB(*colors.text_muted)
            self.c.drawString(self.x, self.y - font_sizes.caption, 
                            f"[Image error: {str(e)}]")
            self.y -= font_sizes.caption + spacing.paragraph_gap
    
    def _render_exercise_area(self, exercise: ExerciseArea):
        """Render an exercise area (ruled, dotgrid, square, blank)."""
        height = page_config.mm_to_points(exercise.height_mm)
        
        self._check_page_break(height + spacing.section_gap)
        
        self.y -= spacing.section_gap
        
        # Draw rounded rectangle border
        self.c.setStrokeColorRGB(*colors.line_light)
        self.c.setLineWidth(0.5)
        self.c.roundRect(self.x, self.y - height, self.content_width, height,
                        EXERCISE_AREA["corner_radius"], stroke=1, fill=0)
        
        # Draw pattern
        if exercise.variant == "ruled":
            # Horizontal lines
            self.c.setStrokeColorRGB(*colors.line_light)
            self.c.setLineWidth(0.3)
            
            y_pos = self.y - EXERCISE_AREA["ruled_spacing"]
            while y_pos > self.y - height:
                self.c.line(self.x + 5, y_pos, self.x + self.content_width - 5, y_pos)
                y_pos -= EXERCISE_AREA["ruled_spacing"]
        
        elif exercise.variant == "dotgrid":
            # Dot grid
            self.c.setFillColorRGB(*colors.line_light)
            
            spacing_val = EXERCISE_AREA["dotgrid_spacing"]
            x_pos = self.x + spacing_val
            while x_pos < self.x + self.content_width:
                y_pos = self.y - spacing_val
                while y_pos > self.y - height:
                    self.c.circle(x_pos, y_pos, EXERCISE_AREA["dot_radius"], 
                                 stroke=0, fill=1)
                    y_pos -= spacing_val
                x_pos += spacing_val
        
        elif exercise.variant == "square":
            # Square grid
            self.c.setStrokeColorRGB(*colors.line_light)
            self.c.setLineWidth(0.3)
            
            spacing_val = EXERCISE_AREA["square_spacing"]
            
            # Vertical lines
            x_pos = self.x + spacing_val
            while x_pos < self.x + self.content_width:
                self.c.line(x_pos, self.y, x_pos, self.y - height)
                x_pos += spacing_val
            
            # Horizontal lines
            y_pos = self.y - spacing_val
            while y_pos > self.y - height:
                self.c.line(self.x, y_pos, self.x + self.content_width, y_pos)
                y_pos -= spacing_val
        
        # blank: no pattern needed
        
        self.y -= height + spacing.section_gap


def render_document(document: Document) -> bytes:
    """
    Render a document to PDF bytes.
    
    Args:
        document: Document model
        
    Returns:
        PDF bytes
    """
    renderer = PDFRenderer(document)
    return renderer.render()
