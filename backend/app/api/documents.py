"""Document routes: upload (multi-file), list, detail, delete."""

import hashlib
import logging
import uuid
from dataclasses import dataclass
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, File, Response, UploadFile, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.deps import EmbedderDep, SessionDep, SessionFactoryDep, SettingsDep
from app.core.errors import (
    AppError,
    ConflictError,
    NotFoundError,
    PayloadTooLargeError,
    UnsupportedMediaTypeError,
)
from app.models import Document
from app.schemas.document import DocumentOut
from app.services.ingestion.pipeline import ingest_document

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/documents", tags=["documents"])

PDF_MAGIC = b"%PDF-"
# Browsers send application/pdf; some clients send a generic type. The real check is PDF_MAGIC.
ALLOWED_CONTENT_TYPES = {"application/pdf", "application/x-pdf", "application/octet-stream", ""}


@dataclass(frozen=True)
class ValidatedUpload:
    filename: str
    data: bytes
    sha256: str


def _safe_filename(raw: str) -> str:
    return raw.replace("\\", "/").rsplit("/", 1)[-1].strip()[:255]


async def _read_and_validate(upload: UploadFile, max_bytes: int) -> ValidatedUpload:
    filename = _safe_filename(upload.filename or "")
    if not filename.lower().endswith(".pdf"):
        raise UnsupportedMediaTypeError(
            f"« {filename} » n'est pas un PDF (extension .pdf attendue)."
        )
    if (upload.content_type or "") not in ALLOWED_CONTENT_TYPES:
        raise UnsupportedMediaTypeError(f"« {filename} » : type de fichier non pris en charge.")

    data = await upload.read(max_bytes + 1)  # one extra byte is enough to detect "too large"
    if len(data) > max_bytes:
        raise PayloadTooLargeError(
            f"« {filename} » dépasse la taille maximale de {max_bytes // (1024 * 1024)} Mo."
        )
    if not data:
        raise AppError(f"« {filename} » est vide.")
    if not data.startswith(PDF_MAGIC):
        raise UnsupportedMediaTypeError(f"« {filename} » n'est pas un fichier PDF valide.")
    return ValidatedUpload(filename, data, hashlib.sha256(data).hexdigest())


@router.post("", status_code=status.HTTP_202_ACCEPTED, response_model=list[DocumentOut])
async def upload_documents(
    files: Annotated[list[UploadFile], File(description="Un ou plusieurs fichiers PDF")],
    background_tasks: BackgroundTasks,
    session: SessionDep,
    session_factory: SessionFactoryDep,
    settings: SettingsDep,
    embedder: EmbedderDep,
) -> list[Document]:
    """Validate and register the PDFs, then process them in the background (202 Accepted).

    All-or-nothing: if one file is invalid, nothing is imported.
    """
    if len(files) > settings.max_files_per_upload:
        raise AppError(f"Maximum {settings.max_files_per_upload} fichiers par envoi.")

    uploads = [await _read_and_validate(f, settings.max_upload_bytes) for f in files]

    hashes = [u.sha256 for u in uploads]
    if len(set(hashes)) != len(hashes):
        raise ConflictError("Le même fichier figure plusieurs fois dans l'envoi.")
    existing = list(
        await session.scalars(select(Document.filename).where(Document.content_hash.in_(hashes)))
    )
    if existing:
        raise ConflictError(f"Déjà importé : {', '.join(existing)}.")

    documents = [
        Document(filename=u.filename, content_hash=u.sha256, size_bytes=len(u.data))
        for u in uploads
    ]
    session.add_all(documents)
    try:
        await session.commit()
    except IntegrityError as exc:  # same file uploaded concurrently by another request
        await session.rollback()
        raise ConflictError("Ce document est déjà en cours d'import.") from exc

    for document, upload in zip(documents, uploads, strict=True):
        logger.info("Document registered: id=%s file=%s", document.id, document.filename)
        background_tasks.add_task(
            ingest_document, document.id, upload.data, session_factory, embedder, settings
        )
    return documents


@router.get("", response_model=list[DocumentOut])
async def list_documents(session: SessionDep) -> list[Document]:
    return list(await session.scalars(select(Document).order_by(Document.created_at.desc())))


async def _get_or_404(session: SessionDep, document_id: uuid.UUID) -> Document:
    document = await session.get(Document, document_id)
    if document is None:
        raise NotFoundError("Document introuvable.")
    return document


@router.get("/{document_id}", response_model=DocumentOut)
async def get_document(document_id: uuid.UUID, session: SessionDep) -> Document:
    return await _get_or_404(session, document_id)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(document_id: uuid.UUID, session: SessionDep) -> Response:
    document = await _get_or_404(session, document_id)
    await session.delete(document)  # chunks are deleted by the database (ON DELETE CASCADE)
    await session.commit()
    logger.info("Document deleted: id=%s", document_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
