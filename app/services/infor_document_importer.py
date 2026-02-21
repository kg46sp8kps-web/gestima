"""GESTIMA - Infor Document Importer

Import PDF drawings from Infor Document Management (IDO: SLDocumentObjects_Exts).

Architecture:
- list_documents()     — paginated metadata fetch (NO binary content)
- download_document()  — single-document binary fetch (base64 decode)
- match_documents_to_parts() — pure matching logic (no DB, testable in isolation)
- preview_import()     — match + duplicate check against DB
- execute_import()     — download + store_from_bytes + link + Part.file_id update

Does NOT extend InforImporterBase (custom pagination + binary download required).
Transaction: single commit after ALL rows (L-008).
"""

import asyncio
import base64
import logging
import re
from typing import Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.file_record import FileLink, FileRecord
from app.models.part import Part
from app.services.file_service import file_service
from app.services.infor_api_client import InforAPIClient

logger = logging.getLogger(__name__)

# Safety guard: maximum pages for paginated metadata fetch
_MAX_PAGES = 500


class InforDocumentImporter:
    """Import PDF drawings from Infor Document Management via IDO API.

    Flow:
        1. list_documents()            — fetch document metadata from Infor (paginated)
        2. preview_import()            — match docs to Parts, flag duplicates
        3. execute_import()            — download + store bytes + link to Part
    """

    IDO_NAME = "SLDocumentObjects_Exts"

    METADATA_PROPERTIES = [
        "DocumentName",
        "DocumentExtension",
        "DocumentType",
        "RowPointer",
        "Sequence",
        "Description",
        "StorageMethod",
    ]

    DEFAULT_FILTER = "DocumentType IN ('Výkres-platný', 'PDF', 'Výkres')"

    # Batch page size for metadata listing
    _PAGE_SIZE = 200

    # ==================== PUBLIC API ====================

    async def list_documents(
        self,
        client: InforAPIClient,
        filter_str: Optional[str] = None,
        record_cap: int = 0,
    ) -> list[dict]:
        """Load document metadata from Infor IDO without binary content.

        Uses bookmark-based pagination so large result sets are handled safely.
        Binary content (DocumentObject) is intentionally excluded — call
        download_document() per-row only for rows the user selects.

        Args:
            client: Authenticated InforAPIClient instance.
            filter_str: Optional IDO WHERE clause. Defaults to DEFAULT_FILTER.
            record_cap: Max total records to return (0 = unlimited up to safety cap).

        Returns:
            List of metadata dicts with keys matching METADATA_PROPERTIES.
        """
        effective_filter = filter_str if filter_str is not None else self.DEFAULT_FILTER
        all_rows: list[dict] = []
        seen_bookmarks: set[str] = set()
        bookmark: Optional[str] = None
        page = 0

        logger.info(
            f"[list_documents] Starting fetch from {self.IDO_NAME} "
            f"(filter='{effective_filter}', record_cap={record_cap})"
        )

        while page < _MAX_PAGES:
            # How many rows to request this page?
            if record_cap > 0:
                remaining = record_cap - len(all_rows)
                if remaining <= 0:
                    break
                page_size = min(self._PAGE_SIZE, remaining)
            else:
                page_size = self._PAGE_SIZE

            result = await client.load_collection(
                ido_name=self.IDO_NAME,
                properties=self.METADATA_PROPERTIES,
                filter=effective_filter,
                record_cap=page_size,
                load_type="NEXT" if bookmark else None,
                bookmark=bookmark,
            )

            data = result.get("data", [])
            new_bookmark = result.get("bookmark")
            has_more = result.get("has_more", False)

            all_rows.extend(data)

            logger.info(
                f"[list_documents] Page {page}: got {len(data)} rows "
                f"(total={len(all_rows)}, has_more={has_more})"
            )

            # Bookmark loop guard (same bookmark repeated = infinite loop)
            if new_bookmark and new_bookmark in seen_bookmarks:
                logger.warning(
                    f"[list_documents] Bookmark loop detected on page {page} "
                    f"(total {len(all_rows)} rows). Stopping."
                )
                break
            if new_bookmark:
                seen_bookmarks.add(new_bookmark)

            bookmark = new_bookmark

            if not has_more or not bookmark or not data:
                break

            # Hard cap reached
            if record_cap > 0 and len(all_rows) >= record_cap:
                break

            page += 1

        logger.info(f"[list_documents] Done — {len(all_rows)} documents fetched.")
        return all_rows

    async def download_document(
        self,
        client: InforAPIClient,
        row_pointer: str,
    ) -> tuple[bytes, str, str]:
        """Download a single PDF from Infor by loading the DocumentObject binary property.

        The DocumentObject property returns a base64-encoded PDF string.  This
        method decodes it to raw bytes so the caller can pass them directly to
        file_service.store_from_bytes().

        Args:
            client: Authenticated InforAPIClient instance.
            row_pointer: RowPointer value that uniquely identifies the document row.

        Returns:
            Tuple of (pdf_bytes, document_name, document_extension).

        Raises:
            ValueError: If document is not found or DocumentObject is empty.
        """
        result = await client.load_collection(
            ido_name=self.IDO_NAME,
            properties=["DocumentObject", "DocumentName", "DocumentExtension"],
            filter=f"RowPointer = '{row_pointer}'",
            record_cap=1,
        )

        if not result["data"]:
            raise ValueError(f"Document not found: row_pointer={row_pointer!r}")

        row = result["data"][0]
        base64_data = row.get("DocumentObject")

        if not base64_data:
            raise ValueError(
                f"Document has no binary content: row_pointer={row_pointer!r}"
            )

        pdf_bytes = base64.b64decode(base64_data)
        document_name: str = row.get("DocumentName", "unknown")
        document_extension: str = row.get("DocumentExtension") or "pdf"

        logger.info(
            f"[download_document] Downloaded {len(pdf_bytes)} bytes "
            f"for '{document_name}' (ext={document_extension})"
        )

        return pdf_bytes, document_name, document_extension

    def match_documents_to_parts(
        self,
        documents: list[dict],
        parts: list[Part],
    ) -> list[dict]:
        """Match documents to Parts via article_number in DocumentName.

        Matching strategy:
        1. Build case-insensitive lookup: {article_number_lower: Part}.
        2. For each document, normalise DocumentName (lowercase, strip .pdf suffix).
        3. Prefer EXACT match (identifier == normalised_name) over token match.
        4. When multiple identifiers match the same document → WARNING (ambiguous).
        5. When no identifier matches → error row (is_valid=False).

        This is a pure function — no DB access, making it unit-testable in isolation.

        Args:
            documents: List of metadata dicts from list_documents().
            parts: All active Part ORM instances loaded from DB.

        Returns:
            List of staged-row dicts ready for preview_import() / execute_import().
        """
        # Build lookup: article_number_lower -> Part
        # Only article_number is used — drawing_number is an internal Gestima reference,
        # NOT the DMS document name used in Infor DocumentName field.
        lookup: dict[str, Part] = {}
        for part in parts:
            if part.article_number:
                key = part.article_number.lower().strip()
                if key and key not in lookup:
                    lookup[key] = part

        staged_rows: list[dict] = []

        for idx, doc in enumerate(documents):
            document_name: str = doc.get("DocumentName") or ""
            document_extension: str = doc.get("DocumentExtension") or "pdf"
            row_pointer: str = doc.get("RowPointer") or ""
            sequence: str = doc.get("Sequence") or ""
            description: Optional[str] = doc.get("Description")

            errors: list[str] = []
            warnings: list[str] = []

            # Normalise: lowercase + strip .pdf suffix
            normalised = document_name.lower().strip()
            if normalised.endswith(".pdf"):
                normalised = normalised[:-4]

            # --- Find matches ---
            # identifier must appear in document name as a WHOLE TOKEN:
            #   - exact match: document name == identifier
            #   - token match: identifier bordered by non-alphanumeric or start/end
            # Separators: _ - . ~ / ( ) space and ANY other non-alnum char
            # NO loose substring — "35126" must NOT match "52083512611"
            exact_matches: list[tuple[str, Part]] = []
            token_matches: list[tuple[str, Part]] = []

            for identifier_lower, part in lookup.items():
                if not identifier_lower:
                    continue
                if identifier_lower == normalised:
                    exact_matches.append((identifier_lower, part))
                elif identifier_lower in normalised:
                    # Check word-boundary: identifier must be bordered by
                    # ANY non-alphanumeric char or start/end of string.
                    # Covers: _ - . ~ / ( ) space and all other separators
                    # used in Infor DocumentName patterns.
                    pattern = (
                        r'(?:^|[^a-zA-Z0-9])'
                        + re.escape(identifier_lower)
                        + r'(?:$|[^a-zA-Z0-9])'
                    )
                    if re.search(pattern, normalised):
                        token_matches.append((identifier_lower, part))

            # Choose best match (priority: exact > longest token)
            matched_part: Optional[Part] = None
            matched_identifier: Optional[str] = None

            if exact_matches:
                if len(exact_matches) > 1:
                    warnings.append(
                        f"Ambiguous exact match: multiple parts match '{document_name}'. "
                        f"Using first: {exact_matches[0][0]!r}"
                    )
                matched_identifier, matched_part = exact_matches[0]

            elif token_matches:
                # Prefer longest token match (most specific)
                token_matches.sort(key=lambda m: len(m[0]), reverse=True)
                if len(token_matches) > 1:
                    candidates = [m[0] for m in token_matches]
                    warnings.append(
                        f"Multiple token matches for '{document_name}': "
                        f"{candidates!r}. Using longest: {token_matches[0][0]!r}"
                    )
                matched_identifier, matched_part = token_matches[0]

            # Validate
            if not row_pointer:
                errors.append("Missing RowPointer — cannot download document.")

            if matched_part is None:
                errors.append(
                    f"No matching Part found for DocumentName='{document_name}'."
                )

            is_valid = len(errors) == 0

            # Resolve the original-case identifier for display
            matched_article_number: Optional[str] = None
            if matched_part is not None and matched_identifier is not None:
                # Recover original-case value from Part
                if (
                    matched_part.article_number
                    and matched_part.article_number.lower().strip() == matched_identifier
                ):
                    matched_article_number = matched_part.article_number
                elif (
                    matched_part.drawing_number
                    and matched_part.drawing_number.lower().strip() == matched_identifier
                ):
                    matched_article_number = matched_part.drawing_number

            staged_rows.append(
                {
                    "row_index": idx,
                    "document_name": document_name,
                    "document_extension": document_extension,
                    "row_pointer": row_pointer,
                    "sequence": sequence,
                    "description": description,
                    "matched_article_number": matched_article_number,
                    "matched_part_id": matched_part.id if matched_part else None,
                    "matched_part_number": matched_part.part_number if matched_part else None,
                    "is_valid": is_valid,
                    "is_duplicate": False,  # filled in by preview_import()
                    "errors": errors,
                    "warnings": warnings,
                    "duplicate_action": "skip",
                }
            )

        logger.info(
            f"[match_documents_to_parts] {len(staged_rows)} docs staged — "
            f"valid={sum(1 for r in staged_rows if r['is_valid'])}, "
            f"invalid={sum(1 for r in staged_rows if not r['is_valid'])}"
        )

        return staged_rows

    async def preview_import(
        self,
        raw_rows: list[dict],
        db: AsyncSession,
    ) -> list[dict]:
        """Preview import: match documents to Parts and check for existing FileLinks.

        Steps:
        1. Batch-load ALL active Parts from DB (single query).
        2. Call match_documents_to_parts() (pure matching, no DB).
        3. For matched rows: check whether a FileLink (entity_type='part',
           link_type='drawing') already exists for the matched part → is_duplicate.

        Args:
            raw_rows: Metadata rows returned by list_documents().
            db: Async database session.

        Returns:
            List of staged-row dicts with is_duplicate populated.
        """
        # 1. Batch load all active Parts
        result = await db.execute(
            select(Part).where(Part.deleted_at.is_(None))
        )
        all_parts: list[Part] = list(result.scalars().all())
        logger.info(f"[preview_import] Loaded {len(all_parts)} parts from DB.")

        # 2. Match documents to parts (pure function, no DB)
        staged_rows = self.match_documents_to_parts(raw_rows, all_parts)

        # 3. Collect part IDs that have a match so we can batch-check duplicates
        matched_part_ids: set[int] = {
            row["matched_part_id"]
            for row in staged_rows
            if row["matched_part_id"] is not None
        }

        # Batch-load existing FileLinks for all matched parts
        existing_links: set[int] = set()
        if matched_part_ids:
            link_result = await db.execute(
                select(FileLink.entity_id).where(
                    and_(
                        FileLink.entity_type == "part",
                        FileLink.link_type == "drawing",
                        FileLink.entity_id.in_(matched_part_ids),
                        FileLink.deleted_at.is_(None),
                    )
                )
            )
            existing_links = {row[0] for row in link_result.all()}

        # Mark duplicates
        for row in staged_rows:
            part_id = row.get("matched_part_id")
            if part_id is not None and part_id in existing_links:
                row["is_duplicate"] = True

        duplicate_count = sum(1 for r in staged_rows if r["is_duplicate"])
        logger.info(
            f"[preview_import] Preview complete — "
            f"valid={sum(1 for r in staged_rows if r['is_valid'])}, "
            f"duplicates={duplicate_count}"
        )

        return staged_rows

    # Max concurrent Infor HTTP downloads (avoid overwhelming the API)
    _DOWNLOAD_CONCURRENCY = 10
    # Commit batch size — commit to DB every N successful rows to avoid
    # accumulating too many dirty objects in the SQLAlchemy session.
    _COMMIT_BATCH = 100

    async def execute_import(
        self,
        staged_rows: list[dict],
        client: InforAPIClient,
        db: AsyncSession,
        created_by: str = "system",
    ) -> dict:
        """Execute import for valid staged rows with parallel downloads.

        Strategy:
        1. Filter valid rows, skip invalid/duplicate.
        2. Download PDFs in parallel (semaphore-limited concurrency).
        3. Store to disk + DB sequentially (SQLite single-writer).
        4. Commit every _COMMIT_BATCH rows for memory safety.

        Args:
            staged_rows: Output of preview_import() (or manually built staged rows).
            client: Authenticated InforAPIClient instance.
            db: Async database session.
            created_by: Username for audit fields.

        Returns:
            Dict with keys: created_count, updated_count, skipped_count, errors.
        """
        created_count = 0
        updated_count = 0
        skipped_count = 0
        row_errors: list[str] = []
        row_warnings: list[str] = []

        # Pre-load affected Parts into identity map so we can update Part.file_id
        part_ids_needed: set[int] = {
            row["matched_part_id"]
            for row in staged_rows
            if row.get("is_valid") and row.get("matched_part_id") is not None
        }

        parts_by_id: dict[int, Part] = {}
        if part_ids_needed:
            parts_result = await db.execute(
                select(Part).where(
                    and_(
                        Part.id.in_(part_ids_needed),
                        Part.deleted_at.is_(None),
                    )
                )
            )
            for part in parts_result.scalars().all():
                parts_by_id[part.id] = part

        # --- Phase 1: Filter valid rows ---
        valid_rows: list[dict] = []
        for row in staged_rows:
            document_name = row.get("document_name", "")
            row_pointer = row.get("row_pointer", "")
            part_id = row.get("matched_part_id")

            is_valid = row.get("is_valid")
            if is_valid is None:
                is_valid = bool(row_pointer and part_id is not None)
            if not is_valid:
                skipped_count += 1
                continue

            if row.get("is_duplicate") and row.get("duplicate_action") == "skip":
                skipped_count += 1
                continue

            part = parts_by_id.get(part_id) if part_id is not None else None
            if part is None:
                msg = (
                    f"Part id={part_id} not found at execution time "
                    f"(document='{document_name}'). Skipping."
                )
                logger.warning(f"[execute_import] {msg}")
                row_errors.append(msg)
                skipped_count += 1
                continue

            valid_rows.append({**row, "_part": part})

        logger.info(
            f"[execute_import] {len(valid_rows)} valid rows to process "
            f"({skipped_count} skipped), concurrency={self._DOWNLOAD_CONCURRENCY}"
        )

        # --- Phase 2: Download PDFs in parallel, store sequentially ---
        semaphore = asyncio.Semaphore(self._DOWNLOAD_CONCURRENCY)

        async def _download_one(
            row_pointer: str, document_name: str
        ) -> tuple[bytes, str, str] | None:
            """Download a single PDF with concurrency limit."""
            async with semaphore:
                try:
                    return await self.download_document(client, row_pointer)
                except Exception as exc:
                    msg = f"Download failed for '{document_name}': {exc}"
                    logger.error(f"[execute_import] {msg}")
                    row_errors.append(msg)
                    return None

        # Process in batches for memory + commit safety
        batch_size = self._COMMIT_BATCH
        for batch_start in range(0, len(valid_rows), batch_size):
            batch = valid_rows[batch_start:batch_start + batch_size]

            # Parallel download for this batch
            download_tasks = [
                _download_one(r["row_pointer"], r.get("document_name", ""))
                for r in batch
            ]
            download_results = await asyncio.gather(*download_tasks)

            # Sequential store + link (SQLite single-writer)
            batch_stored = 0
            for row, dl_result in zip(batch, download_results):
                document_name = row.get("document_name", "")
                article_number = row.get("matched_article_number") or "unknown"
                part: Part = row["_part"]

                if dl_result is None:
                    skipped_count += 1
                    continue

                pdf_bytes, infor_name, infor_ext = dl_result

                # Build safe filename
                safe_ext = infor_ext.lstrip(".").lower() or "pdf"
                filename = f"{infor_name}.{safe_ext}" if "." not in infor_name else infor_name

                # Store bytes → FileRecord
                try:
                    dir_name = article_number if article_number != "unknown" else (part.part_number or str(part.id))
                    directory = f"parts/{dir_name}"
                    file_record = await file_service.store_from_bytes(
                        content=pdf_bytes,
                        filename=filename,
                        directory=directory,
                        db=db,
                        allowed_types=["pdf"],
                        created_by=created_by,
                    )
                except Exception as exc:
                    msg = f"store_from_bytes failed for '{document_name}': {exc}"
                    logger.error(f"[execute_import] {msg}", exc_info=True)
                    row_errors.append(msg)
                    skipped_count += 1
                    continue

                # Check for duplicate hash — same content already stored for a DIFFERENT part
                try:
                    dup_result = await db.execute(
                        select(FileRecord.id, FileLink.entity_id).
                        join(FileLink, FileRecord.id == FileLink.file_id).
                        where(
                            and_(
                                FileRecord.file_hash == file_record.file_hash,
                                FileRecord.id != file_record.id,
                                FileRecord.deleted_at.is_(None),
                                FileLink.entity_type == "part",
                                FileLink.entity_id != part.id,
                                FileLink.deleted_at.is_(None),
                            )
                        )
                    )
                    dup_rows = dup_result.all()
                    if dup_rows:
                        other_part_ids = [r[1] for r in dup_rows]
                        warn_msg = (
                            f"DUPLICATE HASH: '{document_name}' for part "
                            f"{article_number} (id={part.id}) has identical content "
                            f"as file(s) already linked to part id(s) {other_part_ids}. "
                            f"Possible wrong drawing assignment in Infor."
                        )
                        logger.warning(f"[execute_import] {warn_msg}")
                        row_warnings.append(warn_msg)
                except Exception as exc:
                    logger.debug(f"Duplicate hash check failed (non-fatal): {exc}")

                # Create FileLink (part → drawing)
                try:
                    await file_service.link(
                        file_id=file_record.id,
                        entity_type="part",
                        entity_id=part.id,
                        db=db,
                        is_primary=True,
                        link_type="drawing",
                        created_by=created_by,
                    )
                except Exception as exc:
                    msg = (
                        f"link() failed for '{document_name}' "
                        f"→ part_id={part.id}: {exc}"
                    )
                    logger.error(f"[execute_import] {msg}", exc_info=True)
                    row_errors.append(msg)
                    skipped_count += 1
                    continue

                # Update Part.file_id
                is_update = part.file_id is not None
                part.file_id = file_record.id

                if is_update:
                    updated_count += 1
                else:
                    created_count += 1
                batch_stored += 1

            # Commit after each batch (L-008: transaction boundary per batch)
            try:
                await db.commit()
                logger.info(
                    f"[execute_import] Batch {batch_start // batch_size + 1} committed: "
                    f"{batch_stored} stored (running total: created={created_count}, "
                    f"updated={updated_count})"
                )
            except Exception as exc:
                await db.rollback()
                logger.error(
                    f"[execute_import] Batch commit failed, rolled back: {exc}",
                    exc_info=True,
                )
                raise

        summary = {
            "created_count": created_count,
            "updated_count": updated_count,
            "skipped_count": skipped_count,
            "errors": row_errors,
            "warnings": row_warnings,
        }

        logger.info(
            f"[execute_import] Complete — created={created_count}, "
            f"updated={updated_count}, skipped={skipped_count}, "
            f"errors={len(row_errors)}, warnings={len(row_warnings)}"
        )

        return summary
