"""Deploy the app to a Hugging Face Space (Docker), reading the settings from `.env`.

Usage, from the repository root:
    uv run --project backend --with huggingface_hub python deploy/huggingface/deploy.py

Required in `.env`:
    HF_TOKEN              Hugging Face token with "write" access
    HF_SPACE              e.g. my-name/rag-assistant (created if it does not exist)
    DEPLOY_DATABASE_URL   PostgreSQL with pgvector, e.g. the Neon connection string
    DEMO_PASSWORD         password asked to visitors
    LLM_API_KEY or ANTHROPIC_API_KEY, depending on LLM_PROVIDER

Only committed files are sent (`git archive HEAD`): commit before deploying.
Secrets are stored as Space secrets (encrypted, never in the image or the repository).
"""

import io
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

from dotenv import dotenv_values
from huggingface_hub import HfApi

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent

# .env name -> Space secret name
SECRETS = {
    "DEPLOY_DATABASE_URL": "DATABASE_URL",
    "DEMO_PASSWORD": "DEMO_PASSWORD",
    "LLM_API_KEY": "LLM_API_KEY",
    "ANTHROPIC_API_KEY": "ANTHROPIC_API_KEY",
}
# Non-secret settings copied as-is when present in .env
VARIABLES = [
    "LLM_PROVIDER",
    "LLM_BASE_URL",
    "LLM_MODEL",
    "LLM_MAX_TOKENS",
    "LLM_EFFORT",
    "LLM_REFUSAL_FALLBACK",
    "RETRIEVAL_MODE",
    "RETRIEVAL_TOP_K",
]
PLACEHOLDERS = {"", "sk-ant-..."}


def fail(message: str) -> None:
    print(f"Erreur : {message}", file=sys.stderr)
    sys.exit(1)


def build_context(target: Path) -> None:
    """backend/ and frontend/ as committed, plus the Space's Dockerfile and README."""
    archive = subprocess.run(
        ["git", "archive", "--format=tar", "HEAD", "backend", "frontend"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    ).stdout
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        tar.extractall(target, filter="data")
    shutil.copy(HERE / "Dockerfile", target / "Dockerfile")
    shutil.copy(HERE / "README.md", target / "README.md")


def main() -> None:
    env = {k: v or "" for k, v in dotenv_values(ROOT / ".env").items()}
    for name in ("HF_TOKEN", "HF_SPACE", "DEPLOY_DATABASE_URL", "DEMO_PASSWORD"):
        if env.get(name, "") in PLACEHOLDERS:
            fail(f"{name} manque dans .env (voir l'en-tête de ce script).")
    if subprocess.run(["git", "diff", "--quiet", "HEAD"], cwd=ROOT).returncode != 0:
        print("Attention : des modifications non commitées ne seront pas déployées.")

    api = HfApi(token=env["HF_TOKEN"])
    space = env["HF_SPACE"]
    api.create_repo(space, repo_type="space", space_sdk="docker", exist_ok=True)

    for source, secret in SECRETS.items():
        if env.get(source, "") not in PLACEHOLDERS:
            api.add_space_secret(space, secret, env[source])
            print(f"Secret {secret} enregistré")
    for name in VARIABLES:
        if env.get(name, "") not in PLACEHOLDERS:
            api.add_space_variable(space, name, env[name])
            print(f"Variable {name}={env[name]}")

    with tempfile.TemporaryDirectory() as tmp:
        build_context(Path(tmp))
        api.upload_folder(
            repo_id=space,
            repo_type="space",
            folder_path=tmp,
            commit_message="Deploy from GitHub repository",
            delete_patterns=["backend/**", "frontend/**"],  # remove files deleted since last time
        )

    owner, name = space.split("/")
    print(f"\nEnvoyé. Construction en cours : https://huggingface.co/spaces/{space}")
    print(f"Application (une fois prête) : https://{owner}-{name}.hf.space".lower())


if __name__ == "__main__":
    main()
