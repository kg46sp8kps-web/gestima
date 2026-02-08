"""
PDF-STEP Annotator — Overlay STEP geometry annotations on PDF drawings.

Creates colored bounding boxes and dimension labels on PDF drawings
to help Vision API spatially map geometry features to drawing elements.

ADR-TBD: Vision Hybrid Pipeline
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING
import tempfile

logger = logging.getLogger(__name__)

# PDF imports (conditional)
try:
    from pypdf import PdfReader, PdfWriter
    from reportlab.pdfgen import canvas
    from reportlab.lib.colors import Color
    from reportlab.lib.pagesizes import letter
    import io

    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    logger.warning("PDF libraries not available - pdf_step_annotator disabled")

    # Type stubs for when libraries unavailable
    if TYPE_CHECKING:
        from pypdf import PdfReader, PdfWriter
    else:
        PdfReader = object
        PdfWriter = object


if PDF_AVAILABLE:
    # Color scheme for feature types (only if reportlab available)
    FEATURE_COLORS = {
        'shaft': Color(0, 0.7, 0, alpha=0.3),  # Green
        'groove': Color(0.9, 0, 0, alpha=0.3),  # Red
        'bore': Color(0, 0.5, 1, alpha=0.3),  # Blue
        'taper': Color(1, 0.6, 0, alpha=0.3),  # Orange
    }
else:
    FEATURE_COLORS = {}


class PdfStepAnnotator:
    """Annotate PDF drawings with STEP geometry overlays."""

    def __init__(self, scale_factor: float = 10.0):
        """
        Initialize annotator.

        Args:
            scale_factor: PDF points per mm (initial heuristic, refined later)
                         Typical: 10 points/mm for A4 technical drawings
        """
        if not PDF_AVAILABLE:
            raise ImportError("PDF libraries not available (pypdf, reportlab)")

        self.scale_factor = scale_factor

    def annotate_pdf_with_step(
        self,
        pdf_path: Path,
        waterline_data: Dict,
        output_path: Optional[Path] = None
    ) -> Optional[Path]:
        """
        Create annotated PDF with STEP geometry overlays.

        Args:
            pdf_path: Path to original PDF drawing
            waterline_data: Dict from WaterlineExtractor with 'segments' key
            output_path: Optional output path (default: temp file)

        Returns:
            Path to annotated PDF or None on failure
        """
        if not pdf_path.exists():
            logger.error(f"PDF not found: {pdf_path}")
            return None

        try:
            # Read original PDF
            reader = PdfReader(str(pdf_path))

            if len(reader.pages) == 0:
                logger.error(f"PDF has no pages: {pdf_path}")
                return None

            # Use first page (technical drawings typically single page)
            page = reader.pages[0]
            page_width = float(page.mediabox.width)
            page_height = float(page.mediabox.height)

            logger.info(
                f"PDF page size: {page_width:.1f} × {page_height:.1f} points"
            )

            # Create annotation overlay
            overlay_pdf = self._create_annotation_overlay(
                waterline_data,
                page_width,
                page_height
            )

            if not overlay_pdf:
                logger.error("Failed to create annotation overlay")
                return None

            # Merge overlay with original
            page.merge_page(overlay_pdf.pages[0])

            # Write output
            if output_path is None:
                # Create temp file
                fd, output_path = tempfile.mkstemp(suffix='_annotated.pdf')
                import os
                os.close(fd)
                output_path = Path(output_path)

            writer = PdfWriter()
            writer.add_page(page)

            with open(output_path, 'wb') as f:
                writer.write(f)

            logger.info(f"Annotated PDF saved: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"PDF annotation failed: {e}", exc_info=True)
            return None

    def _create_annotation_overlay(
        self,
        waterline_data: Dict,
        page_width: float,
        page_height: float
    ) -> Optional[PdfReader]:
        """
        Create transparent PDF overlay with colored boxes and labels.

        Returns PdfReader object for merging.
        """
        try:
            segments = waterline_data.get('segments', [])

            if not segments:
                logger.warning("No segments to annotate")
                return None

            # Create in-memory PDF canvas
            packet = io.BytesIO()
            c = canvas.Canvas(packet, pagesize=(page_width, page_height))

            # Set transparency
            c.setFillAlpha(0.3)
            c.setStrokeAlpha(0.5)

            # Draw each segment as colored box with label
            for i, seg in enumerate(segments):
                seg_type = seg.get('type', 'shaft')
                z_start = seg.get('z_start', 0)
                z_end = seg.get('z_end', 0)
                diameter = seg.get('diameter', 0)
                length = seg.get('length', 0)

                # Map STEP coordinates to PDF coordinates
                # Heuristic: place annotations in left margin area
                # Vertical position proportional to z_start
                x = 50  # Left margin
                y = page_height - 100 - (i * 60)  # Stack vertically

                # Clamp to page bounds
                if y < 50:
                    break  # Stop if running out of space

                w = diameter * self.scale_factor * 0.5  # Scale down for visibility
                h = length * self.scale_factor * 0.3

                # Clamp dimensions
                w = min(w, 150)
                h = min(h, 40)

                # Draw colored rectangle
                color = FEATURE_COLORS.get(seg_type, FEATURE_COLORS['shaft'])
                c.setFillColor(color)
                c.setStrokeColor(color)
                c.rect(x, y, w, h, fill=1, stroke=1)

                # Draw label
                c.setFillAlpha(1.0)
                c.setFillColor('black')
                c.setFont("Helvetica-Bold", 8)

                label = self._format_label(seg_type, diameter, length)
                c.drawString(x + 5, y + h + 5, label)

            c.save()

            # Convert to PdfReader
            packet.seek(0)
            return PdfReader(packet)

        except Exception as e:
            logger.error(f"Overlay creation failed: {e}", exc_info=True)
            return None

    def _format_label(self, seg_type: str, diameter: float, length: float) -> str:
        """Format annotation label text."""
        type_names = {
            'shaft': 'SHAFT',
            'groove': 'GROOVE',
            'bore': 'BORE',
            'taper': 'TAPER',
        }

        type_name = type_names.get(seg_type, seg_type.upper())
        return f"{type_name} Ø{diameter:.2f} L={length:.2f}"

    def update_scale_factor(self, new_scale: float) -> None:
        """Update scale factor for coordinate refinement iterations."""
        self.scale_factor = new_scale
        logger.info(f"Scale factor updated: {new_scale:.2f} points/mm")
