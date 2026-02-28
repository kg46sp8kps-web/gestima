"""GESTIMA - Drawing Import Service

Business logic for importing drawings from either:
- local filesystem path (legacy mode)
- remote SSH source (no mounted SMB drive required)

2-step workflow:
1. scan_share() + preview_import() -> show what matches
2. execute_import() -> copy files, create records, link to parts
"""

import asyncio
import logging
import os
import posixpath
import shlex
import subprocess
import tempfile
from pathlib import Path
from typing import Optional
from urllib.parse import unquote, urlparse

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.file_record import FileLink
from app.models.part import Part
from app.schemas.drawing_import import (
    DrawingImportExecuteResponse,
    DrawingImportPreviewResponse,
    ImportFolderRequest,
    ShareFileInfo,
    ShareFolderPreview,
    ShareStatusResponse,
)
from app.services.file_service import file_service

logger = logging.getLogger(__name__)

# Folder name prefixes to skip (not real parts),
# UNLESS the folder name contains a dot (e.g. "470100.28" is a valid part).
SKIP_PREFIXES = ("46", "47")


def _should_skip_folder(folder_name: str) -> bool:
    """Skip 46*/47* folders unless the name contains a dot (valid part codes)."""
    if not folder_name.startswith(SKIP_PREFIXES):
        return False
    return "." not in folder_name

# File extensions to import
PDF_EXTENSIONS = {".pdf"}
STEP_EXTENSIONS = {".step", ".stp"}


def _detect_share_file_type(filename: str) -> Optional[str]:
    """Detect supported file type from extension."""
    ext = Path(filename).suffix.lower()
    if ext in PDF_EXTENSIONS:
        return "pdf"
    if ext in STEP_EXTENSIONS:
        return "step"
    return None


def _scan_local_share_sync(share_path: Path) -> list[dict]:
    """
    Synchronous scan of local folder source.

    Returns list of dicts with:
    - folder_name
    - pdf_files
    - step_files
    """
    if not share_path.exists() or not share_path.is_dir():
        return []

    results = []
    for entry in sorted(share_path.iterdir(), key=lambda p: p.name):
        if not entry.is_dir():
            continue

        folder_name = entry.name
        if _should_skip_folder(folder_name):
            continue

        pdf_files = []
        step_files = []

        try:
            folder_entries = list(entry.iterdir())
        except PermissionError:
            logger.warning("Permission denied while scanning folder: %s", entry)
            continue

        for file_entry in folder_entries:
            if not file_entry.is_file():
                continue

            file_type = _detect_share_file_type(file_entry.name)
            if not file_type:
                continue

            file_size = file_entry.stat().st_size
            data = {
                "filename": file_entry.name,
                "file_size": file_size,
                "file_type": file_type,
            }
            if file_type == "pdf":
                pdf_files.append(data)
            else:
                step_files.append(data)

        pdf_files.sort(key=lambda f: f["filename"])
        step_files.sort(key=lambda f: f["filename"])
        results.append(
            {
                "folder_name": folder_name,
                "pdf_files": pdf_files,
                "step_files": step_files,
            }
        )

    return results


def _list_local_folder_files_sync(folder_path: Path) -> list[dict]:
    """List supported files inside one local folder."""
    if not folder_path.exists() or not folder_path.is_dir():
        return []

    files = []
    for file_entry in sorted(folder_path.iterdir(), key=lambda p: p.name):
        if not file_entry.is_file():
            continue
        file_type = _detect_share_file_type(file_entry.name)
        if not file_type:
            continue
        files.append(
            {
                "filename": file_entry.name,
                "file_size": file_entry.stat().st_size,
                "file_type": file_type,
                "source_path": file_entry,
            }
        )
    return files


class DrawingImportService:
    """
    Import drawings from local path or remote SSH source to FileRecord system.

    Source selection:
    - local path: "/Volumes/Dokumenty/TPV-dokumentace/Vykresy"
    - ssh URI: "ssh://user@host:22/absolute/path"
    """

    def __init__(self, share_path: str):
        self.share_path_raw = (share_path or "").strip()
        self.share_path = Path(self.share_path_raw) if self.share_path_raw else Path("")
        self.source_mode = "local"
        self._last_scan_skipped = 0
        self._init_error: Optional[str] = None

        self._ssh_user = ""
        self._ssh_host = ""
        self._ssh_port = 22
        self._ssh_base_path = ""

        if self.share_path_raw.startswith("ssh://"):
            self.source_mode = "ssh"
            self._parse_ssh_uri()

    def _parse_ssh_uri(self) -> None:
        """Parse ssh://user@host:port/path format."""
        try:
            parsed = urlparse(self.share_path_raw)
            if parsed.scheme.lower() != "ssh":
                raise ValueError("Unsupported URI scheme (expected ssh://)")
            if not parsed.hostname:
                raise ValueError("Missing host in ssh:// URI")
            if not parsed.path:
                raise ValueError("Missing remote path in ssh:// URI")

            remote_path = unquote(parsed.path)
            if not remote_path.startswith("/"):
                raise ValueError("Remote path must be absolute (start with '/')")

            self._ssh_user = parsed.username or ""
            self._ssh_host = parsed.hostname
            self._ssh_port = parsed.port or 22
            self._ssh_base_path = remote_path.rstrip("/")
        except ValueError as exc:
            self._init_error = f"Invalid DRAWINGS_SHARE_PATH SSH URI: {exc}"

    @property
    def _ssh_target(self) -> str:
        if self._ssh_user:
            return f"{self._ssh_user}@{self._ssh_host}"
        return self._ssh_host

    @staticmethod
    def _quote_remote(value: str) -> str:
        return shlex.quote(value)

    @staticmethod
    def _validate_segment(value: str, label: str) -> None:
        if not value or value in {".", ".."}:
            raise ValueError(f"Invalid {label}: {value!r}")
        if "/" in value or "\\" in value or "\x00" in value:
            raise ValueError(f"Invalid {label}: {value!r}")

    def _run_ssh_command_sync(
        self,
        remote_cmd: str,
        *,
        timeout: int = 60,
        stdout_file=None,
    ) -> subprocess.CompletedProcess:
        """Run SSH command. If stdout_file is set, stream stdout to file."""
        cmd = ["ssh", "-p", str(self._ssh_port), self._ssh_target, remote_cmd]
        if stdout_file is not None:
            return subprocess.run(
                cmd,
                stdout=stdout_file,
                stderr=subprocess.PIPE,
                timeout=timeout,
                check=False,
            )
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )

    def _scan_share_ssh_sync(self) -> list[dict]:
        """Scan remote SSH source and return same shape as local scanner."""
        if self._init_error:
            return []

        base = self._quote_remote(self._ssh_base_path)

        folders_cmd = (
            f"if [ -d {base} ]; then "
            f"find {base} -mindepth 1 -maxdepth 1 -type d -printf '%f\\n'; "
            f"fi"
        )
        folders_res = self._run_ssh_command_sync(folders_cmd)
        if folders_res.returncode != 0:
            logger.error(
                "SSH scan failed (folders): rc=%s, stderr=%s",
                folders_res.returncode,
                (folders_res.stderr or "").strip(),
            )
            return []

        all_folders = [
            line.strip()
            for line in (folders_res.stdout or "").splitlines()
            if line.strip()
        ]

        filtered_folders = [f for f in all_folders if not _should_skip_folder(f)]
        self._last_scan_skipped = max(0, len(all_folders) - len(filtered_folders))

        results_map = {
            folder_name: {
                "folder_name": folder_name,
                "pdf_files": [],
                "step_files": [],
            }
            for folder_name in filtered_folders
        }

        files_cmd = (
            f"if [ -d {base} ]; then "
            f"find {base} -mindepth 2 -maxdepth 2 -type f "
            f"\\( -iname '*.pdf' -o -iname '*.step' -o -iname '*.stp' \\) "
            f"-printf '%P\\t%s\\n'; "
            f"fi"
        )
        files_res = self._run_ssh_command_sync(files_cmd)
        if files_res.returncode != 0:
            logger.error(
                "SSH scan failed (files): rc=%s, stderr=%s",
                files_res.returncode,
                (files_res.stderr or "").strip(),
            )
            return sorted(results_map.values(), key=lambda item: item["folder_name"])

        for line in (files_res.stdout or "").splitlines():
            if "\t" not in line:
                continue
            relative_path, size_txt = line.split("\t", 1)
            if "/" not in relative_path:
                continue

            folder_name, filename = relative_path.split("/", 1)
            if _should_skip_folder(folder_name):
                continue

            file_type = _detect_share_file_type(filename)
            if not file_type:
                continue

            try:
                file_size = int(size_txt.strip())
            except ValueError:
                file_size = 0

            payload = {
                "filename": filename,
                "file_size": file_size,
                "file_type": file_type,
            }

            if folder_name not in results_map:
                results_map[folder_name] = {
                    "folder_name": folder_name,
                    "pdf_files": [],
                    "step_files": [],
                }

            if file_type == "pdf":
                results_map[folder_name]["pdf_files"].append(payload)
            else:
                results_map[folder_name]["step_files"].append(payload)

        results = sorted(results_map.values(), key=lambda item: item["folder_name"])
        for item in results:
            item["pdf_files"].sort(key=lambda f: f["filename"])
            item["step_files"].sort(key=lambda f: f["filename"])
        return results

    def _list_ssh_folder_files_sync(self, folder_name: str) -> list[dict]:
        """List supported files inside one remote SSH folder."""
        self._validate_segment(folder_name, "folder_name")
        remote_folder = posixpath.join(self._ssh_base_path, folder_name)
        folder_q = self._quote_remote(remote_folder)

        cmd = (
            f"if [ -d {folder_q} ]; then "
            f"find {folder_q} -mindepth 1 -maxdepth 1 -type f "
            f"\\( -iname '*.pdf' -o -iname '*.step' -o -iname '*.stp' \\) "
            f"-printf '%f\\t%s\\n'; "
            f"fi"
        )
        result = self._run_ssh_command_sync(cmd)
        if result.returncode != 0:
            stderr = (result.stderr or "").strip()
            raise ValueError(f"Unable to list remote folder {folder_name}: {stderr or 'SSH error'}")

        files = []
        for line in (result.stdout or "").splitlines():
            if "\t" not in line:
                continue
            filename, size_txt = line.split("\t", 1)
            file_type = _detect_share_file_type(filename)
            if not file_type:
                continue

            try:
                file_size = int(size_txt.strip())
            except ValueError:
                file_size = 0

            files.append(
                {
                    "filename": filename,
                    "file_size": file_size,
                    "file_type": file_type,
                }
            )

        files.sort(key=lambda f: f["filename"])
        return files

    def _download_ssh_file_sync(self, folder_name: str, filename: str) -> Path:
        """Download one remote file over SSH to temporary local path."""
        self._validate_segment(folder_name, "folder_name")
        self._validate_segment(filename, "filename")

        remote_file = posixpath.join(self._ssh_base_path, folder_name, filename)
        remote_q = self._quote_remote(remote_file)

        suffix = Path(filename).suffix or ".bin"
        fd, tmp_name = tempfile.mkstemp(prefix="drawing_import_", suffix=suffix)
        os.close(fd)

        try:
            with open(tmp_name, "wb") as fh:
                cmd = f"cat -- {remote_q}"
                result = self._run_ssh_command_sync(
                    cmd,
                    timeout=180,
                    stdout_file=fh,
                )
        except Exception:
            Path(tmp_name).unlink(missing_ok=True)
            raise

        if result.returncode != 0:
            stderr = (
                result.stderr.decode("utf-8", errors="ignore")
                if isinstance(result.stderr, (bytes, bytearray))
                else str(result.stderr or "")
            ).strip()
            Path(tmp_name).unlink(missing_ok=True)
            raise ValueError(f"Unable to download remote file {filename}: {stderr or 'SSH error'}")

        return Path(tmp_name)

    def check_status(self) -> ShareStatusResponse:
        """Check if source (local path or SSH URI) is accessible."""
        if self._init_error:
            return ShareStatusResponse(
                share_path=self.share_path_raw or "(not configured)",
                is_accessible=False,
                total_folders=0,
                message=self._init_error,
            )

        if self.source_mode == "ssh":
            base = self._quote_remote(self._ssh_base_path)
            cmd = (
                f"if [ -d {base} ]; then "
                f"find {base} -mindepth 1 -maxdepth 1 -type d "
                f"! -name '46*' ! -name '47*' | wc -l; "
                f"else echo MISSING; fi"
            )
            result = self._run_ssh_command_sync(cmd)
            if result.returncode != 0:
                stderr = (result.stderr or "").strip()
                return ShareStatusResponse(
                    share_path=self.share_path_raw,
                    is_accessible=False,
                    total_folders=0,
                    message=f"SSH source inaccessible: {stderr or 'SSH error'}",
                )

            raw = (result.stdout or "").strip()
            if raw == "MISSING":
                return ShareStatusResponse(
                    share_path=self.share_path_raw,
                    is_accessible=False,
                    total_folders=0,
                    message=f"Remote path not found: {self._ssh_base_path}",
                )

            try:
                folder_count = int(raw.splitlines()[-1]) if raw else 0
            except (ValueError, IndexError):
                folder_count = 0

            return ShareStatusResponse(
                share_path=self.share_path_raw,
                is_accessible=True,
                total_folders=folder_count,
                message="OK (ssh)",
            )

        if not self.share_path.exists():
            return ShareStatusResponse(
                share_path=str(self.share_path),
                is_accessible=False,
                total_folders=0,
                message=f"Share not accessible: {self.share_path}",
            )

        try:
            folder_count = sum(
                1 for e in self.share_path.iterdir()
                if e.is_dir() and not _should_skip_folder(e.name)
            )
            return ShareStatusResponse(
                share_path=str(self.share_path),
                is_accessible=True,
                total_folders=folder_count,
                message="OK",
            )
        except PermissionError:
            return ShareStatusResponse(
                share_path=str(self.share_path),
                is_accessible=False,
                total_folders=0,
                message="Permission denied",
            )

    async def scan_share(self) -> list[dict]:
        """Scan source folders (async wrapper)."""
        if self._init_error:
            return []
        if self.source_mode == "ssh":
            return await asyncio.to_thread(self._scan_share_ssh_sync)
        return await asyncio.to_thread(_scan_local_share_sync, self.share_path)

    async def _list_folder_files(self, folder_name: str) -> list[dict]:
        """List files inside one folder from active source."""
        if self.source_mode == "ssh":
            return await asyncio.to_thread(self._list_ssh_folder_files_sync, folder_name)
        folder_path = self.share_path / folder_name
        return await asyncio.to_thread(_list_local_folder_files_sync, folder_path)

    async def _store_source_file(
        self,
        *,
        folder_name: str,
        file_info: dict,
        directory: str,
        db: AsyncSession,
        allowed_types: list[str],
        created_by: str,
    ):
        """Store one file from active source into FileService."""
        if self.source_mode == "local":
            source_path: Path = file_info["source_path"]
            return await file_service.store_from_path(
                source_path=source_path,
                directory=directory,
                db=db,
                allowed_types=allowed_types,
                created_by=created_by,
            )

        tmp_path = await asyncio.to_thread(
            self._download_ssh_file_sync, folder_name, file_info["filename"]
        )
        try:
            return await file_service.store_from_path(
                source_path=tmp_path,
                directory=directory,
                db=db,
                allowed_types=allowed_types,
                created_by=created_by,
            )
        finally:
            tmp_path.unlink(missing_ok=True)

    async def preview_import(
        self,
        db: AsyncSession,
    ) -> DrawingImportPreviewResponse:
        """
        Step 1: Scan source + match folders to Parts + return preview.

        Uses batch DB queries for performance.
        """
        share_folders = await self.scan_share()

        if not share_folders:
            return DrawingImportPreviewResponse(
                share_path=self.share_path_raw or str(self.share_path),
                total_folders=0,
                folders=[],
            )

        if self.source_mode == "local":
            total_on_disk = (
                sum(1 for e in self.share_path.iterdir() if e.is_dir())
                if self.share_path.exists()
                else 0
            )
            skipped_count = total_on_disk - len(share_folders)
        else:
            skipped_count = self._last_scan_skipped

        folder_names = [f["folder_name"] for f in share_folders]

        # SQLite has a limit on IN clause params, chunk if needed
        # Match by both article_number and drawing_number
        parts_map: dict[str, dict] = {}
        chunk_size = 500
        from sqlalchemy import or_

        for i in range(0, len(folder_names), chunk_size):
            chunk = folder_names[i : i + chunk_size]
            result = await db.execute(
                select(
                    Part.id,
                    Part.part_number,
                    Part.article_number,
                    Part.drawing_number,
                    Part.file_id,
                ).where(
                    and_(
                        or_(
                            Part.article_number.in_(chunk),
                            Part.drawing_number.in_(chunk),
                        ),
                        Part.deleted_at.is_(None),
                    )
                )
            )
            for row in result.all():
                # article_number match takes precedence
                if row.article_number in chunk:
                    parts_map[row.article_number] = {
                        "id": row.id,
                        "part_number": row.part_number,
                        "file_id": row.file_id,
                    }
                if row.drawing_number in chunk and row.drawing_number not in parts_map:
                    parts_map[row.drawing_number] = {
                        "id": row.id,
                        "part_number": row.part_number,
                        "file_id": row.file_id,
                    }

        matched_part_ids = [p["id"] for p in parts_map.values()]
        linked_part_ids: set[int] = set()

        if matched_part_ids:
            for i in range(0, len(matched_part_ids), chunk_size):
                chunk = matched_part_ids[i : i + chunk_size]
                result = await db.execute(
                    select(FileLink.entity_id).where(
                        and_(
                            FileLink.entity_type == "part",
                            FileLink.entity_id.in_(chunk),
                            FileLink.deleted_at.is_(None),
                        )
                    )
                )
                linked_part_ids.update(row[0] for row in result.all())

        folders: list[ShareFolderPreview] = []
        stats = {
            "matched": 0,
            "unmatched": 0,
            "already_imported": 0,
            "ready": 0,
            "no_pdf": 0,
        }

        for folder_data in share_folders:
            folder_name = folder_data["folder_name"]
            pdf_files = [ShareFileInfo(**f) for f in folder_data["pdf_files"]]
            step_files = [ShareFileInfo(**f) for f in folder_data["step_files"]]

            part_info = parts_map.get(folder_name)
            if not part_info:
                stats["unmatched"] += 1
                folders.append(
                    ShareFolderPreview(
                        folder_name=folder_name,
                        pdf_files=pdf_files,
                        step_files=step_files,
                        status="no_match",
                    )
                )
                continue

            stats["matched"] += 1
            already = part_info["file_id"] is not None or part_info["id"] in linked_part_ids

            if already:
                status = "already_imported"
                stats["already_imported"] += 1
            elif not pdf_files:
                status = "no_pdf"
                stats["no_pdf"] += 1
            else:
                status = "ready"
                stats["ready"] += 1

            primary_pdf = pdf_files[0].filename if pdf_files else None
            folders.append(
                ShareFolderPreview(
                    folder_name=folder_name,
                    matched_part_id=part_info["id"],
                    matched_part_number=part_info["part_number"],
                    matched_article_number=folder_name,
                    pdf_files=pdf_files,
                    step_files=step_files,
                    primary_pdf=primary_pdf,
                    already_imported=already,
                    status=status,
                )
            )

        return DrawingImportPreviewResponse(
            share_path=self.share_path_raw or str(self.share_path),
            total_folders=len(share_folders),
            matched=stats["matched"],
            unmatched=stats["unmatched"],
            already_imported=stats["already_imported"],
            ready=stats["ready"],
            no_pdf=stats["no_pdf"],
            skipped=max(0, skipped_count),
            folders=folders,
        )

    async def execute_import(
        self,
        folders: list[ImportFolderRequest],
        db: AsyncSession,
        *,
        created_by: str = "drawing_import",
    ) -> DrawingImportExecuteResponse:
        """
        Step 2: Execute import for confirmed folders.

        Copies files from source to uploads/, creates FileRecord + FileLink,
        sets Part.file_id. Commits in batches of 50.
        """
        if self._init_error:
            return DrawingImportExecuteResponse(
                success=False,
                files_created=0,
                links_created=0,
                parts_updated=0,
                skipped=0,
                errors=[self._init_error],
            )

        files_created = 0
        links_created = 0
        parts_updated = 0
        skipped = 0
        errors: list[str] = []
        batch_size = 50

        for idx, folder_req in enumerate(folders):
            try:
                async with db.begin_nested():
                    counts = await self._import_folder(
                        folder_req,
                        db,
                        created_by=created_by,
                    )
                files_created += counts["files"]
                links_created += counts["links"]
                parts_updated += counts["parts"]
                skipped += counts["skipped"]
            except Exception as exc:
                error_msg = f"{folder_req.folder_name}: {exc}"
                errors.append(error_msg)
                logger.error(
                    "Import failed for folder %s: %s",
                    folder_req.folder_name,
                    exc,
                    exc_info=True,
                )
                continue

            if (idx + 1) % batch_size == 0:
                try:
                    await db.commit()
                    logger.info(
                        "Batch commit: %s/%s folders processed",
                        idx + 1,
                        len(folders),
                    )
                except Exception as exc:
                    logger.error("Batch commit failed at %s: %s", idx + 1, exc, exc_info=True)
                    errors.append(f"Batch commit failed at {idx + 1}: {exc}")
                    await db.rollback()
                    break

        try:
            await db.commit()
        except Exception as exc:
            logger.error("Final commit failed: %s", exc, exc_info=True)
            errors.append(f"Final commit failed: {exc}")
            await db.rollback()

        success = len(errors) == 0
        logger.info(
            "Drawing import complete: %s files, %s links, %s parts, %s skipped, %s errors",
            files_created,
            links_created,
            parts_updated,
            skipped,
            len(errors),
        )

        return DrawingImportExecuteResponse(
            success=success,
            files_created=files_created,
            links_created=links_created,
            parts_updated=parts_updated,
            skipped=skipped,
            errors=errors,
        )

    async def _import_folder(
        self,
        folder_req: ImportFolderRequest,
        db: AsyncSession,
        *,
        created_by: str,
    ) -> dict[str, int]:
        """Import a single folder's files and return counters."""
        if self.source_mode == "local":
            folder_path = self.share_path / folder_req.folder_name
            if not folder_path.exists():
                raise ValueError(f"Folder not found: {folder_req.folder_name}")

        result = await db.execute(
            select(Part).where(and_(Part.id == folder_req.part_id, Part.deleted_at.is_(None)))
        )
        part = result.scalar_one_or_none()
        if not part:
            raise ValueError(f"Part not found: ID {folder_req.part_id}")

        folder_files = await self._list_folder_files(folder_req.folder_name)
        pdf_files = [f for f in folder_files if f["file_type"] == "pdf"]
        step_files = [f for f in folder_files if f["file_type"] == "step"]
        primary_candidates = [f for f in pdf_files if f["filename"] == folder_req.primary_pdf]

        if not primary_candidates:
            raise ValueError(f"Primary PDF not found: {folder_req.primary_pdf}")

        directory = f"parts/{part.part_number}"
        counters = {"files": 0, "links": 0, "parts": 0, "skipped": 0}

        primary_info = primary_candidates[0]
        primary_record = await self._store_source_file(
            folder_name=folder_req.folder_name,
            file_info=primary_info,
            directory=directory,
            db=db,
            allowed_types=["pdf"],
            created_by=created_by,
        )
        await file_service.link(
            file_id=primary_record.id,
            entity_type="part",
            entity_id=part.id,
            db=db,
            is_primary=True,
            link_type="drawing",
            created_by=created_by,
        )
        part.file_id = primary_record.id
        part.drawing_path = primary_record.file_path

        counters["files"] += 1
        counters["links"] += 1
        counters["parts"] += 1

        for extra_pdf in pdf_files:
            if extra_pdf["filename"] == folder_req.primary_pdf:
                continue

            try:
                extra_record = await self._store_source_file(
                    folder_name=folder_req.folder_name,
                    file_info=extra_pdf,
                    directory=directory,
                    db=db,
                    allowed_types=["pdf"],
                    created_by=created_by,
                )
                await file_service.link(
                    file_id=extra_record.id,
                    entity_type="part",
                    entity_id=part.id,
                    db=db,
                    is_primary=False,
                    link_type="drawing",
                    created_by=created_by,
                )
                counters["files"] += 1
                counters["links"] += 1
            except Exception as exc:
                counters["skipped"] += 1
                logger.warning("Failed to import extra PDF %s: %s", extra_pdf["filename"], exc)

        if folder_req.import_step:
            for step_file in step_files:
                try:
                    step_record = await self._store_source_file(
                        folder_name=folder_req.folder_name,
                        file_info=step_file,
                        directory=directory,
                        db=db,
                        allowed_types=["step"],
                        created_by=created_by,
                    )
                    await file_service.link(
                        file_id=step_record.id,
                        entity_type="part",
                        entity_id=part.id,
                        db=db,
                        is_primary=False,
                        link_type="step_model",
                        created_by=created_by,
                    )
                    counters["files"] += 1
                    counters["links"] += 1
                except Exception as exc:
                    counters["skipped"] += 1
                    logger.warning("Failed to import STEP %s: %s", step_file["filename"], exc)

        return counters
