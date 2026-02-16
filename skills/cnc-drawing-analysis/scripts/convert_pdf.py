#!/usr/bin/env python3
"""Convert PDF technical drawing to high-resolution PNG for vision analysis.

Uses pypdfium2 (pre-installed in Claude VM) for rendering.
Outputs PNG at 200 DPI — optimal for reading dimensions and title blocks.

Usage:
    python convert_pdf.py input.pdf output.png [--dpi 200] [--page 0]
"""
import sys
import argparse

def convert_pdf_to_png(pdf_path: str, output_path: str, dpi: int = 200, page_num: int = 0):
    """Convert a single PDF page to PNG at specified DPI."""
    import pypdfium2 as pdfium

    pdf = pdfium.PdfDocument(pdf_path)
    if page_num >= len(pdf):
        print(f"ERROR: Page {page_num} does not exist. PDF has {len(pdf)} pages.", file=sys.stderr)
        sys.exit(1)

    page = pdf[page_num]
    # Render at specified DPI (default 72 DPI in PDF, scale up)
    scale = dpi / 72
    bitmap = page.render(scale=scale)
    pil_image = bitmap.to_pil()
    pil_image.save(output_path, format="PNG")

    w, h = pil_image.size
    print(f"OK: {pdf_path} page {page_num} -> {output_path} ({w}x{h}px, {dpi} DPI)")
    pdf.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert PDF to PNG")
    parser.add_argument("input", help="Input PDF file path")
    parser.add_argument("output", help="Output PNG file path")
    parser.add_argument("--dpi", type=int, default=200, help="Resolution (default: 200)")
    parser.add_argument("--page", type=int, default=0, help="Page number (default: 0)")
    args = parser.parse_args()

    convert_pdf_to_png(args.input, args.output, dpi=args.dpi, page_num=args.page)
