"""
Pydantic models for PDF document structure.

These models define the JSON schema for the document payload and provide
validation for all content blocks and rich text formatting.

License: MIT
"""

from typing import List as ListType, Optional, Union, Literal
from pydantic import BaseModel, Field, field_validator


class RichText(BaseModel):
    """
    Rich text span with inline formatting.
    
    Supports bold, italic, code, highlighting, colored text, and emoji hints.
    """
    text: str = Field(..., description="Text content")
    bold: bool = Field(default=False, description="Bold formatting")
    italic: bool = Field(default=False, description="Italic formatting")
    code: bool = Field(default=False, description="Monospace code formatting")
    highlight: Optional[Literal["yellow", "green", "aqua", "blue", "cornflower", 
                                  "lavender", "pink", "peach", "gray"]] = Field(
        default=None, description="Background highlight color"
    )
    color: Optional[Literal["blue", "purple", "magenta", "orange", "gold", "teal"]] = Field(
        default=None, description="Text color"
    )
    emoji: bool = Field(default=False, description="Hint for emoji rendering")


class Meta(BaseModel):
    """Document metadata."""
    title: Optional[str] = Field(default=None, description="Document title")
    author: Optional[str] = Field(default=None, description="Document author")
    page_size: Literal["A4", "LETTER"] = Field(default="A4", description="Page size")
    margin_mm: float = Field(default=20.0, ge=0, le=50, description="Page margin in millimeters")
    font_family: Optional[str] = Field(default=None, description="Google Font family name (e.g., 'Roboto', 'Open Sans', 'Lora')")


class ListItem(BaseModel):
    """List item with optional nesting."""
    text: Optional[ListType[RichText]] = Field(default=None, description="Item content")
    checked: Optional[bool] = Field(default=False, description="For task lists, whether item is checked")
    children: Optional[ListType['ListItem']] = Field(default=None, description="Nested list items")


class Heading(BaseModel):
    """Heading block (H1, H2, H3)."""
    type: Literal["heading"] = "heading"
    level: Literal[1, 2, 3] = Field(..., description="Heading level (1=largest)")
    text: ListType[RichText] = Field(..., description="Heading text")


class Paragraph(BaseModel):
    """Paragraph block."""
    type: Literal["paragraph"] = "paragraph"
    text: ListType[RichText] = Field(..., description="Paragraph text")


class Caption(BaseModel):
    """Caption block (smaller, italic text)."""
    type: Literal["caption"] = "caption"
    text: ListType[RichText] = Field(..., description="Caption text")


class ListBlock(BaseModel):
    """List block (bullet, numbered, task, toggle)."""
    type: Literal["list"] = "list"
    variant: Literal["bullet", "number", "task", "toggle"] = Field(..., description="List style")
    items: ListType[ListItem] = Field(..., description="List items")


class Break(BaseModel):
    """Ornamental break (decorative separator)."""
    type: Literal["break"] = "break"
    strength: Literal["extra_light", "light", "regular", "strong"] = Field(
        ..., description="Break visual strength"
    )


class PageBreak(BaseModel):
    """Force a page break."""
    type: Literal["page_break"] = "page_break"


class Code(BaseModel):
    """Code block with optional language hint."""
    type: Literal["code"] = "code"
    language: Optional[str] = Field(default=None, description="Programming language")
    content: str = Field(..., description="Code content")


class Formula(BaseModel):
    """Math formula (LaTeX)."""
    type: Literal["formula"] = "formula"
    latex: str = Field(..., description="LaTeX formula")


class TableRow(BaseModel):
    """Table row."""
    cells: ListType[ListType[RichText]] = Field(..., description="Cell contents (each cell is list of RichText)")


class Table(BaseModel):
    """Table block."""
    type: Literal["table"] = "table"
    columns: int = Field(..., ge=1, description="Number of columns")
    rows: ListType[TableRow] = Field(..., description="Table rows")
    widths: Optional[ListType[float]] = Field(default=None, description="Column width ratios")
    
    @field_validator('widths')
    @classmethod
    def validate_widths(cls, v, info):
        """Ensure widths match column count if provided."""
        if v is not None and 'columns' in info.data:
            if len(v) != info.data['columns']:
                raise ValueError(f"widths length must match columns count ({info.data['columns']})")
        return v


class Image(BaseModel):
    """Image block."""
    type: Literal["image"] = "image"
    src: str = Field(..., description="Image source (file path or URL)")
    alt: Optional[str] = Field(default=None, description="Alt text")
    width_mm: Optional[float] = Field(default=None, ge=0, description="Width in millimeters")
    height_mm: Optional[float] = Field(default=None, ge=0, description="Height in millimeters")
    fit: Literal["contain", "cover"] = Field(default="contain", description="Image fit mode")


class ExerciseArea(BaseModel):
    """Exercise area (ruled, dotgrid, square, blank)."""
    type: Literal["exercise"] = "exercise"
    variant: Literal["ruled", "dotgrid", "square", "blank"] = Field(..., description="Exercise area style")
    height_mm: float = Field(..., ge=10, le=200, description="Height in millimeters")


# Union type for all block types
Block = Union[
    Heading,
    Paragraph,
    Caption,
    ListBlock,
    Break,
    PageBreak,
    Code,
    Formula,
    Table,
    Image,
    ExerciseArea,
]


class Document(BaseModel):
    """Complete document with metadata and content blocks."""
    meta: Meta = Field(default_factory=Meta, description="Document metadata")
    blocks: ListType[Block] = Field(..., description="Content blocks")
    
    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "meta": {
                    "title": "Study Notes",
                    "author": "Jane Doe",
                    "page_size": "A4",
                    "margin_mm": 20
                },
                "blocks": [
                    {
                        "type": "heading",
                        "level": 1,
                        "text": [{"text": "Introduction"}]
                    },
                    {
                        "type": "paragraph",
                        "text": [
                            {"text": "This is "},
                            {"text": "important", "bold": True},
                            {"text": " information."}
                        ]
                    }
                ]
            }
        }


# Update forward references
ListItem.model_rebuild()
