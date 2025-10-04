"""Catalog models"""
from typing import List, Literal
from pydantic import BaseModel


class FontFace(BaseModel):
    """Font face information"""
    family: str
    weights: List[int]
    styles: List[Literal["normal", "italic"]]
    source: Literal["builtin", "google", "upload"]
