# PDF Generator - Study Notes

> A production-ready FastAPI service for generating beautifully formatted PDF documents with rich text, custom fonts, and automatic text wrapping.

## ✨ Features

- **🎨 Rich Text Formatting** - Bold, italic, code, 9 highlight colors, 6 text colors
- **📝 Automatic Text Wrapping** - Long text wraps intelligently to prevent cropping
- **🔤 Custom Google Fonts** - Use any font from [Google Fonts](https://fonts.google.com) library
- **📑 Multiple Content Types** - Headings, paragraphs, lists, tables, code blocks, formulas
- **🎯 Task Lists** - Checkbox lists with visual completion states
- **🎨 Ornamental Breaks** - Four artistic separator styles
- **📐 Exercise Areas** - Ruled lines, dot grids, square grids, blank spaces
- **🖼️ Image Support** - Embed local files or URLs
- **📄 Smart Pagination** - Automatic page breaks with content-aware layout

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- pip package manager

### Installation

1. **Install dependencies:**
```bash
./setup.sh
```
*Or manually:*
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

2. **Start the server:**
```bash
source venv/bin/activate
uvicorn app.app:app --reload
```

The API will be available at `http://127.0.0.1:8000`

### Generate Your First PDF

```bash
curl -X POST http://127.0.0.1:8000/render \
  -H "Content-Type: application/json" \
  --data @example.json \
  -o output.pdf
```

Open `output.pdf` to see all features in action!

## 📚 API Documentation

**Interactive Swagger UI:** http://127.0.0.1:8000/docs  
**ReDoc:** http://127.0.0.1:8000/redoc  
**OpenAPI Spec:** http://127.0.0.1:8000/openapi.json

### Endpoints

#### `POST /render`
Generate a PDF from JSON payload (returns binary PDF).

**Request:** `application/json`  
**Response:** `application/pdf`

#### `POST /render-url`
Generate a PDF and get a temporary download URL (perfect for ChatGPT).

**Request:** `application/json`  
**Response:** JSON with `pdf_url` field (hosted for 1 hour)

#### `POST /render-base64`
Generate a PDF and get base64-encoded JSON response.

**Request:** `application/json`  
**Response:** JSON with `pdf_base64` field

#### `GET /health`
Health check endpoint.

**Response:** `{"status": "ok"}`

## 📖 Document Structure

### Meta Configuration

```json
{
  "meta": {
    "title": "My Document",
    "author": "Your Name",
    "page_size": "A4",
    "margin_mm": 20,
    "font_family": "Open Sans"
  }
}
```

**Fields:**
- `title` (optional) - PDF metadata title
- `author` (optional) - PDF metadata author
- `page_size` - `"A4"` (210×297mm) or `"LETTER"` (8.5×11in), default: `"A4"`
- `margin_mm` - Page margins in millimeters (0-50), default: `20`
- `font_family` (optional) - Any [Google Font](https://fonts.google.com) name (e.g., "Roboto", "Lora", "Montserrat")

**Custom Fonts:**
The system automatically downloads, caches, and embeds Google Fonts with all variants (regular, bold, italic, bold-italic). Popular choices:
- **Sans-serif:** Roboto, Open Sans, Lato, Montserrat, Source Sans Pro
- **Serif:** Lora, Merriweather, Playfair Display, Crimson Text
- **Monospace:** Roboto Mono, Source Code Pro, Fira Code

### Content Blocks

Documents consist of an array of content blocks rendered sequentially.

#### Heading

```json
{
  "type": "heading",
  "level": 1,
  "text": [
    {"text": "Black ", "bold": false},
    {"text": "Heading", "bold": true, "highlight": "yellow"}
  ]
}
```

- `level`: 1 (largest), 2, or 3
- `text`: Array of rich text spans
- Headings are rendered in black and support full rich text formatting

#### Paragraph

```json
{
  "type": "paragraph",
  "text": [
    {"text": "Regular text with "},
    {"text": "bold", "bold": true},
    {"text": " and "},
    {"text": "highlights", "highlight": "yellow"}
  ]
}
```

Automatically wraps long text across multiple lines.

#### Caption

```json
{
  "type": "caption",
  "text": [{"text": "Small italic text for image captions"}]
}
```

#### Lists

```json
{
  "type": "list",
  "variant": "bullet",
  "items": [
    {
      "text": [{"text": "First item"}],
      "checked": false,
      "children": []
    }
  ]
}
```

**Variants:**
- `"bullet"` - Bullet points
- `"number"` - Numbered list (1, 2, 3...)
- `"task"` - Checkbox list (use `checked: true/false`)
- `"toggle"` - Collapsible markers

**Fields:**
- `text`: Rich text array
- `checked` (task lists only): `true` or `false`
- `children`: Nested list items

#### Code Block

```json
{
  "type": "code",
  "language": "python",
  "content": "def hello():\\n    print('Hello, World!')"
}
```

Monospace font with rounded corners and syntax highlighting hints.

#### Math Formula

```json
{
  "type": "formula",
  "latex": "E = mc^2"
}
```

LaTeX notation converted to readable Unicode symbols (∫, ∞, √, π).

#### Table

```json
{
  "type": "table",
  "columns": 3,
  "widths": [2, 2, 1],
  "rows": [
    {
      "cells": [
        [{"text": "Header 1", "bold": true}],
        [{"text": "Header 2", "bold": true}],
        [{"text": "Header 3", "bold": true}]
      ]
    },
    {
      "cells": [
        [{"text": "Cell 1"}],
        [{"text": "Cell 2"}],
        [{"text": "✓", "color": "blue"}]
      ]
    }
  ]
}
```

- `columns`: Number of columns
- `widths` (optional): Relative column widths (e.g., `[2, 2, 1]`)
- `rows`: Array of rows, each with `cells` array
- First row automatically styled as header with gray background
- Cells support full rich text formatting

#### Ornamental Break

```json
{
  "type": "break",
  "strength": "regular"
}
```

**Strengths:**
- `"extra_light"` - Subtle dots
- `"light"` - Gentle curve
- `"regular"` - Smooth flowing wave
- `"strong"` - Thick artistic separator

#### Page Break

```json
{
  "type": "page_break"
}
```

Forces a new page.

#### Image

```json
{
  "type": "image",
  "src": "https://example.com/image.jpg",
  "alt": "Description",
  "width_mm": 100,
  "height_mm": 80,
  "fit": "contain"
}
```

- `src`: Local file path or URL (http://, https://)
- `alt` (optional): Alt text description
- `width_mm`, `height_mm` (optional): Dimensions in millimeters
- `fit`: `"contain"` (maintain aspect ratio) or `"cover"` (fill dimensions)

#### Exercise Area

```json
{
  "type": "exercise",
  "variant": "ruled",
  "height_mm": 50
}
```

**Variants:**
- `"ruled"` - Horizontal lines for writing
- `"dotgrid"` - Dot grid pattern
- `"square"` - Square grid
- `"blank"` - Empty space

`height_mm`: 10-200 millimeters

### Rich Text Formatting

Rich text spans support multiple formatting options that can be combined:

```json
{
  "text": "formatted text",
  "bold": true,
  "italic": true,
  "code": true,
  "highlight": "yellow",
  "color": "blue",
  "emoji": false
}
```

**Highlight Colors (9):**
`yellow`, `green`, `aqua`, `blue`, `cornflower`, `lavender`, `pink`, `peach`, `gray`

**Text Colors (6):**
`blue`, `purple`, `magenta`, `orange`, `gold`, `teal`

**Examples:**
```json
{"text": "bold text", "bold": true}
{"text": "italic text", "italic": true}
{"text": "bold italic", "bold": true, "italic": true}
{"text": "highlighted", "highlight": "yellow"}
{"text": "colored", "color": "purple"}
{"text": "code", "code": true}
{"text": "complex", "bold": true, "highlight": "aqua", "color": "blue"}
```

## 🏗️ Project Structure

```
Sketchnote/
├── app/
│   ├── __init__.py
│   ├── app.py           # FastAPI application & routes
│   ├── models.py        # Pydantic data models
│   ├── renderer.py      # PDF rendering engine
│   ├── styles.py        # Design tokens & configuration
│   └── catalogs.py      # Reserved for future use
├── example.json         # Complete feature demonstration
├── openapi.yaml         # OpenAPI 3.1 specification
├── requirements.txt     # Python dependencies
├── setup.sh             # Quick setup script
└── README.md            # This file
```

## 🎨 Design Features

### Text Wrapping
Long text automatically wraps across multiple lines, preventing cropping. Works in:
- Headings
- Paragraphs
- List items
- Table cells

### Custom Fonts
Specify any Google Font in the `meta.font_family` field. The system:
1. Queries Google Fonts API
2. Downloads TTF files for all variants
3. Caches locally for fast subsequent renders
4. Embeds fonts directly in PDF

### Highlights
Highlights render behind text with 35% opacity and rounded corners for a modern look.

### Tables
- Rounded outer borders (4pt radius)
- First row styled as header with light gray background
- Rich text support in all cells
- Customizable column widths

### Code Blocks
- Monospace font
- Rounded corners (6pt radius)
- Light gray background

### Task Lists
- Custom checkbox drawing
- Visual checkmarks for completed tasks
- Lighter colors for pending items

## 🛠️ Development

### Dependencies

- **FastAPI** ≥0.104.1 - Modern web framework
- **Pydantic** ≥2.5.0 - Data validation
- **ReportLab** ≥4.0.7 - PDF generation
- **Uvicorn** ≥0.24.0 - ASGI server

### Testing

Generate a test PDF:

```bash
curl -X POST http://127.0.0.1:8000/render \
  -H "Content-Type: application/json" \
  --data '{
    "meta": {"title": "Test", "font_family": "Roboto"},
    "blocks": [
      {
        "type": "heading",
        "level": 1,
        "text": [{"text": "Hello World", "bold": true}]
      }
    ]
  }' \
  -o test.pdf
```

### Error Handling

The API returns appropriate HTTP status codes:
- `200` - PDF generated successfully
- `422` - Validation error (invalid JSON schema)
- `500` - Server error (rendering failed)

Error responses include detailed messages:
```json
{
  "detail": "Rendering error: <error message>"
}
```

## 📝 Examples

### Minimal Document

```json
{
  "meta": {},
  "blocks": [
    {
      "type": "paragraph",
      "text": [{"text": "Hello, World!"}]
    }
  ]
}
```

### Study Notes with Custom Font

```json
{
  "meta": {
    "title": "Python Study Notes",
    "font_family": "Lora",
    "margin_mm": 25
  },
  "blocks": [
    {
      "type": "heading",
      "level": 1,
      "text": [
        {"text": "Python ", "bold": false},
        {"text": "Basics", "bold": true, "highlight": "yellow"}
      ]
    },
    {
      "type": "paragraph",
      "text": [
        {"text": "Python is a "},
        {"text": "high-level", "bold": true, "color": "blue"},
        {"text": " programming language."}
      ]
    },
    {
      "type": "code",
      "language": "python",
      "content": "print('Hello, World!')"
    }
  ]
}
```

## 🤝 Contributing

This is a production-ready system. Feel free to extend it with:
- Additional block types
- More styling options
- Export formats (HTML, Markdown, etc.)
- Template system
- Batch processing

## 📄 License

MIT License - See source files for details.

## 🔗 Resources

- [Google Fonts](https://fonts.google.com) - Browse thousands of free fonts
- [ReportLab Documentation](https://www.reportlab.com/docs/reportlab-userguide.pdf)
- [FastAPI Documentation](https://fastapi.tiangolo.com)
- [OpenAPI Specification](https://spec.openapis.org/oas/v3.1.0)

---

**Made with ❤️ for beautiful PDF generation**
