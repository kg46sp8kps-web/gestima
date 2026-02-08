#!/usr/bin/env python3
"""
Import all PDF and STEP drawings from uploads/drawings/ into database.

Creates Part records for each unique drawing pair (PDF + STEP).
Handles file naming patterns:
- JR 810663.ipt.step + JR 810663.idw_Gelso.pdf
- 0347039_D00114455_000_000.step + 0347039_D00114455_000_000_Gelso.pdf
- PDM-249322_03.stp + PDM-249322_03_Gelso.pdf
"""

import asyncio
import hashlib
import random
import re
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import async_session
from app.models.part import Part
from app.models.drawing import Drawing


async def generate_unique_part_number(db: AsyncSession) -> str:
    """Generate unique 8-digit part number (10XXXXXX format)."""
    for _ in range(100):  # Max 100 attempts
        part_number = f"10{random.randint(0, 999999):06d}"
        stmt = select(Part).where(Part.part_number == part_number)
        result = await db.execute(stmt)
        if not result.scalars().first():
            return part_number
    raise ValueError("Failed to generate unique part number after 100 attempts")


def extract_base_name(filename: str) -> str:
    """
    Extract base part number from filename.

    Examples:
    - "JR 810663.ipt.step" → "JR 810663"
    - "JR 810663.idw_Gelso.pdf" → "JR 810663"
    - "0347039_D00114455_000_000.step" → "0347039_D00114455_000_000"
    - "PDM-249322_03.stp" → "PDM-249322_03"
    """
    # Remove extensions (IMPORTANT: longer patterns first!)
    name = filename
    for ext in ['.ipt.step', '.idw_Gelso.pdf', '_Gelso.pdf', '.idw', '.step', '.stp', '.pdf', '_Gelso']:
        name = name.replace(ext, '')

    return name.strip()


async def find_drawing_pairs(drawings_dir: Path) -> dict[str, dict]:
    """
    Find PDF + STEP pairs in drawings directory.

    Returns:
        dict: {base_name: {'pdf': Path, 'step': Path}}
    """
    pairs = {}

    for file_path in drawings_dir.iterdir():
        if not file_path.is_file():
            continue

        filename = file_path.name
        base_name = extract_base_name(filename)

        # Determine file type
        file_type = None
        if filename.endswith('.pdf'):
            file_type = 'pdf'
        elif filename.endswith(('.step', '.stp')):
            file_type = 'step'
        else:
            continue

        # Initialize pair entry
        if base_name not in pairs:
            pairs[base_name] = {'pdf': None, 'step': None}

        pairs[base_name][file_type] = file_path

    # Filter only complete pairs
    complete_pairs = {
        name: files
        for name, files in pairs.items()
        if files['pdf'] and files['step']
    }

    return complete_pairs


async def import_drawing_pair(
    db: AsyncSession,
    base_name: str,
    pdf_path: Path,
    step_path: Path
) -> tuple[Part, Drawing, Drawing]:
    """
    Import PDF + STEP pair as Part with 2 Drawing records.

    Returns:
        (Part, Drawing(pdf), Drawing(step))
    """
    # Check if part already exists
    stmt = select(Part).where(Part.part_number == base_name)
    result = await db.execute(stmt)
    part = result.scalars().first()

    if not part:
        # Create new part with unique 8-digit number
        part_number = await generate_unique_part_number(db)
        part = Part(
            part_number=part_number,
            article_number=base_name,  # Original filename as article number
            name=f"Imported: {base_name}",
            status="active"
        )
        db.add(part)
        await db.flush()  # Get part.id
        print(f"✓ Created Part: {base_name} (ID: {part.id})")
    else:
        print(f"○ Part exists: {base_name} (ID: {part.id})")

    # Check existing drawings
    stmt = select(Drawing).where(Drawing.part_id == part.id)
    result = await db.execute(stmt)
    existing_drawings = {d.file_type: d for d in result.scalars().all()}

    # Helper to compute file hash
    def compute_hash(file_path: Path) -> str:
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                sha256.update(chunk)
        return sha256.hexdigest()

    # Import PDF
    if 'pdf' not in existing_drawings:
        pdf_drawing = Drawing(
            part_id=part.id,
            filename=pdf_path.name,
            file_path=str(pdf_path),
            file_type='pdf',
            file_hash=compute_hash(pdf_path),
            file_size=pdf_path.stat().st_size,
            is_primary=(len(existing_drawings) == 0)  # First drawing is primary
        )
        db.add(pdf_drawing)
        print(f"  + PDF: {pdf_path.name}")
    else:
        pdf_drawing = existing_drawings['pdf']
        print(f"  ○ PDF exists: {pdf_path.name}")

    # Import STEP
    if 'step' not in existing_drawings:
        step_drawing = Drawing(
            part_id=part.id,
            filename=step_path.name,
            file_path=str(step_path),
            file_type='step',
            file_hash=compute_hash(step_path),
            file_size=step_path.stat().st_size,
            is_primary=False  # STEP is secondary to PDF
        )
        db.add(step_drawing)
        print(f"  + STEP: {step_path.name}")
    else:
        step_drawing = existing_drawings['step']
        print(f"  ○ STEP exists: {step_path.name}")

    return part, pdf_drawing, step_drawing


async def import_all_drawings():
    """Import all drawing pairs from uploads/drawings/."""
    drawings_dir = Path("uploads/drawings")

    if not drawings_dir.exists():
        print(f"Error: {drawings_dir} does not exist")
        return

    # Find pairs
    print(f"Scanning {drawings_dir}...")
    pairs = await find_drawing_pairs(drawings_dir)
    print(f"Found {len(pairs)} complete pairs (PDF + STEP)\n")

    if not pairs:
        print("No drawing pairs found!")
        return

    # Import to database
    async with async_session() as db:
        try:
            imported_count = 0

            for base_name, files in pairs.items():
                await import_drawing_pair(
                    db,
                    base_name,
                    files['pdf'],
                    files['step']
                )
                imported_count += 1

            # Commit all changes
            await db.commit()
            print(f"\n✓ Successfully imported {imported_count} drawing pairs")

        except Exception as e:
            await db.rollback()
            print(f"\n✗ Import failed: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(import_all_drawings())
