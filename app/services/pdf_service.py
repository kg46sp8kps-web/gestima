"""GESTIMA - PDF generation service for quotes

Uses Chrome headless (--print-to-pdf) for pixel-perfect rendering.
Template: app/templates/quote_pdf.html.jinja2 (identical to quote-pdf-preview.html)
"""

import asyncio
import base64
import logging
import os
import shutil
import tempfile
from datetime import datetime
from itertools import groupby
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape

logger = logging.getLogger(__name__)

_TEMPLATE_DIR = Path(__file__).parent.parent / "templates"
_LOGO_PATH = Path(__file__).parent.parent / "static" / "logo.png"

# Chrome binary candidates (macOS + Linux)
_CHROME_CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/usr/bin/google-chrome",
    "/usr/bin/google-chrome-stable",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
    "/snap/bin/chromium",
]

_CHROME_BIN: Optional[str] = None


def _find_chrome() -> Optional[str]:
    global _CHROME_BIN
    if _CHROME_BIN is not None:
        return _CHROME_BIN
    for path in _CHROME_CANDIDATES:
        if os.path.isfile(path) and os.access(path, os.X_OK):
            _CHROME_BIN = path
            logger.info("Chrome found: %s", path)
            return path
    # Try PATH
    found = shutil.which("google-chrome") or shutil.which("chromium") or shutil.which("chromium-browser")
    if found:
        _CHROME_BIN = found
        logger.info("Chrome found in PATH: %s", found)
    return _CHROME_BIN


_jinja_env: Optional[Environment] = None


def _get_jinja_env() -> Environment:
    global _jinja_env
    if _jinja_env is None:
        _jinja_env = Environment(
            loader=FileSystemLoader(str(_TEMPLATE_DIR)),
            autoescape=select_autoescape(["html"]),
        )
        _jinja_env.filters["czk"] = _format_czk
        _jinja_env.filters["datecz"] = _format_date_cz
    return _jinja_env


def _format_czk(value: float) -> str:
    """Format float as Czech currency: 1 248,50 Kč"""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return "— Kč"
    int_part = int(v)
    dec_part = round((v - int_part) * 100)
    s = ""
    int_str = str(int_part)
    for i, ch in enumerate(reversed(int_str)):
        if i and i % 3 == 0:
            s = "\u00a0" + s
        s = ch + s
    return f"{s},{dec_part:02d}\u00a0Kč"


def _format_date_cz(value) -> str:
    if value is None:
        return "—"
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except ValueError:
            return value
    if hasattr(value, "day"):
        return f"{value.day}. {value.month}. {value.year}"
    return str(value)


def _load_logo_b64() -> Optional[str]:
    if not _LOGO_PATH.exists():
        return None
    try:
        data = _LOGO_PATH.read_bytes()
        b64 = base64.b64encode(data).decode("ascii")
        return f"data:image/png;base64,{b64}"
    except Exception as e:
        logger.warning("Could not load logo: %s", e)
        return None


def _group_items(items) -> list:
    def sort_key(item):
        return (item.part_id or 999_999_999, item.id)

    sorted_items = sorted(items, key=sort_key)
    groups = []
    idx = 1

    for _part_id, group_iter in groupby(sorted_items, key=lambda i: i.part_id):
        group_items = list(group_iter)
        first = group_items[0]
        # Sort batches by quantity ascending (lowest first)
        group_items.sort(key=lambda i: i.quantity)

        groups.append({
            "idx": idx,
            "article_number": first.article_number,
            "part_name": first.part_name,
            "part_number": first.part_number,
            "drawing_number": first.drawing_number,
            "notes": first.notes,
            "batches": [
                {"quantity": item.quantity, "unit_price": item.unit_price}
                for item in group_items
            ],
        })
        idx += 1

    return groups


def _render_html(quote, partner, items) -> str:
    """Render Jinja2 template to HTML string."""
    env = _get_jinja_env()
    template = env.get_template("quote_pdf.html.jinja2")
    return template.render(
        quote=quote,
        partner=partner,
        groups=_group_items(items),
        generated_at=_format_date_cz(datetime.now()),
        logo_data_uri=_load_logo_b64(),
    )


async def generate_quote_pdf(quote, partner, items) -> bytes:
    """Generate PDF bytes using Chrome headless --print-to-pdf."""
    chrome = _find_chrome()
    if not chrome:
        raise RuntimeError(
            "Chrome/Chromium not found. Install Google Chrome or Chromium."
        )

    html_content = _render_html(quote, partner, items)

    with tempfile.TemporaryDirectory() as tmpdir:
        html_path = os.path.join(tmpdir, "quote.html")
        pdf_path = os.path.join(tmpdir, "quote.pdf")

        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        cmd = [
            chrome,
            "--headless",
            "--disable-gpu",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--run-all-compositor-stages-before-draw",
            f"--print-to-pdf={pdf_path}",
            "--no-pdf-header-footer",
            "--print-to-pdf-no-header",
            f"file://{html_path}",
        ]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)

        if proc.returncode != 0:
            logger.error("Chrome PDF failed (rc=%d): %s", proc.returncode, stderr.decode())
            raise RuntimeError(f"Chrome PDF generation failed: {stderr.decode()[:200]}")

        if not os.path.exists(pdf_path):
            raise RuntimeError("Chrome ran but PDF file was not created")

        with open(pdf_path, "rb") as f:
            return f.read()
