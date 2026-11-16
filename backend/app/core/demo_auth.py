"""Optional single-password protection for a public demo (HTTP basic auth).

The app has no user accounts. When `DEMO_PASSWORD` is set, every request must carry it
(any user name is accepted); the browser shows its own login box and then remembers it.
The health check stays open so the hosting platform can monitor the app.
"""

import base64
import binascii
import secrets

from fastapi.responses import JSONResponse

REALM = "Assistant RAG"


def password_matches(authorization: str | None, expected: str) -> bool:
    if not authorization or not authorization.startswith("Basic "):
        return False
    try:
        decoded = base64.b64decode(authorization.removeprefix("Basic "), validate=True)
        _, _, password = decoded.decode("utf-8").partition(":")
    except (binascii.Error, UnicodeDecodeError):
        return False
    # Constant-time comparison: the answer time does not leak how much of the password matched.
    return secrets.compare_digest(password.encode("utf-8"), expected.encode("utf-8"))


def is_public_path(path: str) -> bool:
    return path.rstrip("/").endswith("/health")


def auth_required_response() -> JSONResponse:
    return JSONResponse(
        {"detail": "Mot de passe de démonstration requis.", "code": "auth_required"},
        status_code=401,
        headers={"WWW-Authenticate": f'Basic realm="{REALM}", charset="UTF-8"'},
    )
