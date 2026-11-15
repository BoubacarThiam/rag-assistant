"""Upload validation: rejected before any database access."""

from httpx import AsyncClient

from app.core.config import Settings, get_settings
from app.main import app
from tests.pdf_factory import make_pdf


def pdf_file(name: str, data: bytes, content_type: str = "application/pdf") -> tuple[str, tuple]:  # type: ignore[type-arg]
    return ("files", (name, data, content_type))


async def test_rejects_non_pdf_extension(client: AsyncClient) -> None:
    response = await client.post(
        "/documents", files=[pdf_file("notes.txt", b"hello", "text/plain")]
    )
    assert response.status_code == 415
    assert "notes.txt" in response.json()["detail"]


async def test_rejects_fake_pdf_content(client: AsyncClient) -> None:
    response = await client.post("/documents", files=[pdf_file("faux.pdf", b"MZ\x90\x00 binary")])
    assert response.status_code == 415
    assert "PDF valide" in response.json()["detail"]


async def test_rejects_wrong_content_type(client: AsyncClient) -> None:
    response = await client.post(
        "/documents", files=[pdf_file("image.pdf", make_pdf(["x"]), "image/png")]
    )
    assert response.status_code == 415


async def test_rejects_too_large_file(client: AsyncClient) -> None:
    app.dependency_overrides[get_settings] = lambda: Settings(_env_file=None, max_upload_mb=1)  # type: ignore[call-arg]
    big = b"%PDF-1.7\n" + b"0" * (1024 * 1024)

    response = await client.post("/documents", files=[pdf_file("gros.pdf", big)])

    assert response.status_code == 413
    assert response.json()["code"] == "payload_too_large"


async def test_rejects_empty_file(client: AsyncClient) -> None:
    response = await client.post("/documents", files=[pdf_file("vide.pdf", b"")])
    assert response.status_code == 400


async def test_rejects_too_many_files(client: AsyncClient) -> None:
    app.dependency_overrides[get_settings] = lambda: Settings(  # type: ignore[call-arg]
        _env_file=None, max_files_per_upload=2
    )
    files = [pdf_file(f"{i}.pdf", make_pdf([f"Doc {i}."])) for i in range(3)]

    response = await client.post("/documents", files=files)

    assert response.status_code == 400


async def test_requires_at_least_one_file(client: AsyncClient) -> None:
    response = await client.post("/documents")
    assert response.status_code == 422
