"""Point the short, stable demo address to the current tunnel address.

The Cloudflare quick tunnel gets a new random address at every start. A tiny redirect page
published with GitHub Pages (branch `gh-pages`) gives a fixed address instead:
    https://boubacarthiam.github.io/rag-assistant/

Usage, from the repository root, once the demo is running:
    python deploy/demo_link.py
Needs the GitHub CLI (`gh`) logged in with push access to the repository.
The watchdog (deploy/watchdog.py) uses the same functions to do this automatically.
"""

import base64
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPOSE = ["compose", "-f", "docker-compose.demo.yml"]
REPO = "BoubacarThiam/rag-assistant"
BRANCH = "gh-pages"
PAGE_URL = "https://boubacarthiam.github.io/rag-assistant/"
TUNNEL_PATTERN = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")

# Where to look for the tools when they are not on the PATH (e.g. a scheduled task).
KNOWN_LOCATIONS = {
    "docker": [Path.home() / "AppData/Local/Programs/DockerDesktop/resources/bin/docker.exe"],
    "gh": [Path("C:/Program Files/GitHub CLI/gh.exe")],
}

PAGE = """<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="refresh" content="0; url={url}">
<title>Assistant RAG — démo</title>
<style>body{{font-family:system-ui,sans-serif;margin:3rem 1rem;text-align:center;color:#222}}
a{{color:#4f46e5}}</style>
</head>
<body>
<p>Redirection vers la démo…</p>
<p><a href="{url}">Ouvrir l'Assistant RAG</a></p>
<p><small>Si la page ne répond pas, la démo est probablement arrêtée.</small></p>
<script>location.replace({url_json});</script>
</body>
</html>
"""


class CommandError(RuntimeError):
    pass


def executable(name: str) -> str:
    found = shutil.which(name)
    if found:
        return found
    for path in KNOWN_LOCATIONS.get(name, []):
        if path.exists():
            return str(path)
    raise CommandError(f"{name} est introuvable.")


def run(*args: str, input_text: str | None = None, timeout: float = 120) -> str:
    result = subprocess.run(
        [executable(args[0]), *args[1:]],
        cwd=ROOT,
        input=input_text,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        # No console window flashing when started by the watchdog (Windows only).
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if result.returncode != 0:
        # The cause is on the last line (docker compose prints its progress before it).
        lines = result.stderr.strip().splitlines() or ["(pas de message)"]
        raise CommandError(f"{' '.join(args[:3])}… : {lines[-1][:300]}")
    return result.stdout


def latest_tunnel_url() -> str | None:
    """The address printed last by the tunnel container, if any."""
    found = TUNNEL_PATTERN.findall(run("docker", *COMPOSE, "logs", "tunnel"))
    return found[-1] if found else None


def wait_for_tunnel_url(not_this: str | None = None, attempts: int = 30) -> str:
    """Wait until the tunnel prints an address (a new one, when `not_this` is given)."""
    for _ in range(attempts):
        url = latest_tunnel_url()
        if url and url != not_this:
            return url
        time.sleep(2)
    raise CommandError("adresse du tunnel introuvable (la démo est-elle lancée ?).")


def publish(url: str) -> bool:
    """Make the GitHub Pages redirect point to `url`. Returns False if it already did."""
    content = PAGE.format(url=url, url_json=json.dumps(url))
    current = json.loads(run("gh", "api", f"repos/{REPO}/contents/index.html?ref={BRANCH}"))
    if base64.b64decode(current["content"]).decode("utf-8") == content:
        return False
    payload = {
        "message": "Point the demo link to the current tunnel",
        "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
        "branch": BRANCH,
        "sha": current["sha"],
    }
    run(
        "gh",
        "api",
        "-X",
        "PUT",
        f"repos/{REPO}/contents/index.html",
        "--input",
        "-",
        input_text=json.dumps(payload),
    )
    return True


def main() -> None:
    try:
        url = wait_for_tunnel_url()
        if publish(url):
            print(f"{PAGE_URL} -> {url}\n(GitHub Pages met environ une minute à se mettre à jour.)")
        else:
            print(f"Déjà à jour : {PAGE_URL} -> {url}")
    except CommandError as exc:
        sys.exit(f"Erreur : {exc}")


if __name__ == "__main__":
    main()
