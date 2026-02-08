"""
PDF Contour Annotator — Draw contour line on PDF for validation.

Draws:
- Red contour line (what Vision extracted)
- Blue bounding box (polotovar)
- Green STEP points (reference)
"""

import logging
import tempfile
from pathlib import Path
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# PDF imports
try:
    from pypdf import PdfReader, PdfWriter
    from reportlab.pdfgen import canvas
    from reportlab.lib.colors import Color
    import io

    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    logger.warning("PDF libraries not available")


def annotate_pdf_with_contour(
    pdf_path: Path,
    contour: List[Dict],
    step_geometry: Dict
) -> Optional[Path]:
    """
    Annotate PDF with contour line.

    Args:
        pdf_path: Original PDF
        contour: Vision-extracted contour [{"z": ..., "r": ...}]
        step_geometry: STEP data for reference

    Returns:
        Path to annotated PDF or None if failed
    """
    if not PDF_AVAILABLE:
        logger.error("PDF libraries not available")
        return None

    if len(contour) < 2:
        logger.error(f"Contour has only {len(contour)} points")
        return None

    try:
        # Read PDF
        reader = PdfReader(pdf_path)
        if len(reader.pages) == 0:
            logger.error("PDF has no pages")
            return None

        page = reader.pages[0]
        page_width = float(page.mediabox.width)
        page_height = float(page.mediabox.height)

        logger.info(f"PDF page: {page_width} × {page_height} points")

        # Create overlay
        overlay_pdf = _create_contour_overlay(
            contour,
            step_geometry,
            page_width,
            page_height
        )

        if not overlay_pdf:
            return None

        # Merge
        page.merge_page(overlay_pdf.pages[0])

        # Write output
        fd, output_path_str = tempfile.mkstemp(suffix='_contour.pdf')
        import os
        os.close(fd)
        output_path = Path(output_path_str)

        writer = PdfWriter()
        writer.add_page(page)

        with open(output_path, 'wb') as f:
            writer.write(f)

        logger.info(f"Annotated PDF created: {output_path}")
        return output_path

    except Exception as e:
        logger.error(f"PDF annotation failed: {e}", exc_info=True)
        return None


def _create_contour_overlay(
    contour: List[Dict],
    step_geometry: Dict,
    page_width: float,
    page_height: float
) -> Optional[PdfReader]:
    """
    Create contour overlay.

    For now: Simple mapping - assume part is centered.
    TODO: Better coordinate mapping (Vision should provide pdf_bbox)
    """
    try:
        # Extract contour bounds
        z_values = [p["z"] for p in contour]
        r_values = [p["r"] for p in contour]

        z_min, z_max = min(z_values), max(z_values)
        r_min, r_max = 0, max(r_values)

        z_span = z_max - z_min
        r_span = r_max

        # Simple mapping: center on page
        # Scale to fit 60% of page
        scale_x = (page_width * 0.6) / z_span if z_span > 0 else 1
        scale_y = (page_height * 0.6) / r_span if r_span > 0 else 1
        scale = min(scale_x, scale_y)

        offset_x = page_width * 0.2
        offset_y = page_height * 0.5

        def map_to_pdf(z, r):
            """Map (z, r) → (pdf_x, pdf_y)"""
            x = offset_x + (z - z_min) * scale
            y = offset_y - r * scale  # Flip Y
            return x, y

        # Create canvas
        packet = io.BytesIO()
        c = canvas.Canvas(packet, pagesize=(page_width, page_height))

        # Draw bounding box (polotovar)
        c.setStrokeColor(Color(0, 0, 1, alpha=0.3))
        c.setFillColor(Color(0, 0, 1, alpha=0.1))
        bb_x1, bb_y1 = map_to_pdf(z_min, r_max)
        bb_x2, bb_y2 = map_to_pdf(z_max, 0)
        c.rect(bb_x1, bb_y2, bb_x2 - bb_x1, bb_y1 - bb_y2, stroke=1, fill=1)

        # Draw contour line
        c.setStrokeColor(Color(1, 0, 0, alpha=0.8))  # Red
        c.setLineWidth(2)

        path = c.beginPath()
        first_point = True
        for point in contour:
            x, y = map_to_pdf(point["z"], point["r"])
            if first_point:
                path.moveTo(x, y)
                first_point = False
            else:
                path.lineTo(x, y)

        c.drawPath(path, stroke=1, fill=0)

        # Draw contour points
        c.setFillColor(Color(1, 0, 0))
        for point in contour:
            x, y = map_to_pdf(point["z"], point["r"])
            c.circle(x, y, 2, stroke=0, fill=1)

        # Draw STEP reference points
        c.setFillColor(Color(0, 0.7, 0, alpha=0.5))  # Green
        step_z = step_geometry.get("z_values", [])
        step_r = step_geometry.get("r_values", [])
        for z, r in zip(step_z, step_r):
            x, y = map_to_pdf(z, r)
            c.circle(x, y, 3, stroke=1, fill=1)

        c.save()

        # Convert to PdfReader
        packet.seek(0)
        return PdfReader(packet)

    except Exception as e:
        logger.error(f"Overlay creation failed: {e}", exc_info=True)
        return None
