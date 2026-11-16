"""Point the short, stable demo address to the current tunnel address.

The Cloudflare quick tunnel gets a new random address at every start. A tiny redirect page
published with GitHub Pages (branch `gh-pages`) gives a fixed address instead:
    https://boubacarthiam.github.io/rag-assistant/

Usage, from the repository root, once the demo is running:
    python deploy/demo_link.py
Needs the GitHub CLI (`gh`) logged in with push access to the repository.
"""

import base64
import json
import re
import shutil
import subprocess
import sys
import time

REPO = "BoubacarThiam/rag-assistant"
BRANCH = "gh-pages"
PAGE_URL = "https://boubacarthiam.github.io/rag-assistant/"
TUNNEL_PATTERN = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")

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


def run(*args: str) -> str:
    executable = shutil.which(args[0])
    if executable is None:
        sys.exit(f"Erreur : {args[0]} est introuvable.")
    result = subprocess.run([executable, *args[1:]], capture_output=True, text=True)
    if result.returncode != 0:
        sys.exit(f"Erreur : {' '.join(args[:3])}…\n{result.stderr}")
    return result.stdout


def tunnel_url() -> str:
    for _ in range(30):  # the tunnel prints its address a few seconds after starting
        logs = run("docker", "compose", "-f", "docker-compose.demo.yml", "logs", "tunnel")
        found = TUNNEL_PATTERN.findall(logs)
        if found:
            return found[-1]
        time.sleep(2)
    sys.exit("Erreur : adresse du tunnel introuvable (la démo est-elle lancée ?).")


def main() -> None:
    url = tunnel_url()
    content = PAGE.format(url=url, url_json=json.dumps(url))
    current = json.loads(run("gh", "api", f"repos/{REPO}/contents/index.html?ref={BRANCH}"))
    if base64.b64decode(current["content"]).decode("utf-8") == content:
        print(f"Déjà à jour : {PAGE_URL} -> {url}")
        return
    payload = {
        "message": "Point the demo link to the current tunnel",
        "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
        "branch": BRANCH,
        "sha": current["sha"],
    }
    executable = shutil.which("gh")
    assert executable is not None
    subprocess.run(
        [executable, "api", "-X", "PUT", f"repos/{REPO}/contents/index.html", "--input", "-"],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=True,
    )
    print(f"{PAGE_URL} -> {url}\n(GitHub Pages met environ une minute à se mettre à jour.)")


if __name__ == "__main__":
    main()
