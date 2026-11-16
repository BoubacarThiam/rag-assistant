"""Deploy the app to Google Cloud Run, reading the settings from `.env`.

Usage, from the repository root (after `gcloud auth login`):
    uv run --project backend python deploy/cloudrun/deploy.py

Required in `.env`:
    GCP_PROJECT           Google Cloud project id (billing enabled)
    DEPLOY_DATABASE_URL   PostgreSQL with pgvector, e.g. the Neon connection string
    DEMO_PASSWORD         password asked to visitors
    LLM_API_KEY or ANTHROPIC_API_KEY, depending on LLM_PROVIDER
Optional: GCP_REGION (default us-east1, next to Neon's us-east-1).

Steps: enable the APIs, build the image with Cloud Build, store it in Artifact Registry,
then deploy one Cloud Run service. The service scales to zero when unused (free tier) and
to at most one instance, which caps the cost. Only committed files are sent.
"""

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import app_settings, build_context, fail, load_env

SERVICE = "rag-assistant"
REPOSITORY = "rag-assistant"


def gcloud(*args: str, capture: bool = False) -> str:
    executable = shutil.which("gcloud")
    if executable is None:
        fail("gcloud est introuvable (installer Google Cloud CLI).")
    result = subprocess.run([executable, *args], check=False, text=True, capture_output=capture)
    if result.returncode != 0:
        fail(f"échec de : gcloud {' '.join(args[:3])}…\n{result.stderr or ''}")
    return (result.stdout or "").strip()


def main() -> None:
    env = load_env(["GCP_PROJECT", "DEPLOY_DATABASE_URL", "DEMO_PASSWORD"])
    project = env["GCP_PROJECT"]
    region = env.get("GCP_REGION") or "us-east1"
    image = f"{region}-docker.pkg.dev/{project}/{REPOSITORY}/{SERVICE}"
    common = ["--project", project, "--quiet"]

    print("1/4 Activation des services Google Cloud…")
    gcloud(
        "services",
        "enable",
        "run.googleapis.com",
        "cloudbuild.googleapis.com",
        "artifactregistry.googleapis.com",
        *common,
    )

    print("2/4 Dépôt d'images (Artifact Registry)…")
    existing = gcloud(
        "artifacts",
        "repositories",
        "list",
        "--location",
        region,
        "--format",
        "value(name)",
        *common,
        capture=True,
    )
    if not any(line.endswith(f"/{REPOSITORY}") for line in existing.splitlines()):
        gcloud(
            "artifacts",
            "repositories",
            "create",
            REPOSITORY,
            "--repository-format",
            "docker",
            "--location",
            region,
            *common,
        )

    with tempfile.TemporaryDirectory() as tmp:
        context = Path(tmp) / "context"
        context.mkdir()
        build_context(context)

        print("3/4 Construction de l'image avec Cloud Build (environ 10 à 15 min)…")
        gcloud("builds", "submit", str(context), "--tag", image, "--timeout", "3600s", *common)

        # The settings go through a file: values such as the database URL contain characters
        # (&, ?) that a command line would mangle. JSON strings are valid YAML.
        settings_file = Path(tmp) / "env.yaml"
        settings_file.write_text(
            "".join(f"{k}: {json.dumps(v)}\n" for k, v in app_settings(env).items()),
            encoding="utf-8",
        )

        print("4/4 Déploiement sur Cloud Run…")
        gcloud(
            "run",
            "deploy",
            SERVICE,
            "--image",
            image,
            "--region",
            region,
            "--port",
            "7860",
            "--memory",
            "2Gi",
            "--cpu",
            "1",
            # PDF imports run in the background after the response: keep the CPU available.
            "--no-cpu-throttling",
            "--min-instances",
            "0",
            "--max-instances",
            "1",
            "--timeout",
            "300",
            # Public URL; the app itself asks for DEMO_PASSWORD.
            "--allow-unauthenticated",
            "--env-vars-file",
            str(settings_file),
            *common,
        )

    url = gcloud(
        "run",
        "services",
        "describe",
        SERVICE,
        "--region",
        region,
        "--format",
        "value(status.url)",
        *common,
        capture=True,
    )
    print(f"\nEn ligne : {url}")


if __name__ == "__main__":
    main()
