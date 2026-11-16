"""Shared by the deploy scripts: read `.env` and assemble the Docker build folder."""

import io
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
DEPLOY_DIR = Path(__file__).resolve().parent
PLACEHOLDERS = {"", "sk-ant-..."}

# .env name -> name inside the deployed app (secrets)
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


def fail(message: str) -> None:
    print(f"Erreur : {message}", file=sys.stderr)
    sys.exit(1)


def load_env(required: list[str]) -> dict[str, str]:
    env = {k: v or "" for k, v in dotenv_values(ROOT / ".env").items()}
    for name in required:
        if env.get(name, "") in PLACEHOLDERS:
            fail(f"{name} manque dans .env.")
    if subprocess.run(["git", "diff", "--quiet", "HEAD"], cwd=ROOT).returncode != 0:
        print("Attention : des modifications non commitées ne seront pas déployées.")
    return env


def app_settings(env: dict[str, str]) -> dict[str, str]:
    """Secrets and variables for the deployed app, renamed as the app expects them."""
    # Only the key of the provider in use: no secret is deployed without a reason.
    unused_key = (
        "ANTHROPIC_API_KEY" if env.get("LLM_PROVIDER") == "openai_compatible" else "LLM_API_KEY"
    )
    settings = {
        target: env[source]
        for source, target in SECRETS.items()
        if source != unused_key and env.get(source, "") not in PLACEHOLDERS
    }
    settings |= {name: env[name] for name in VARIABLES if env.get(name, "") not in PLACEHOLDERS}
    return settings


def build_context(target: Path, extra_files: tuple[Path, ...] = ()) -> None:
    """backend/ and frontend/ as committed (`git archive`: no .env, no node_modules),
    plus the shared Dockerfile and any platform-specific file."""
    archive = subprocess.run(
        ["git", "archive", "--format=tar", "HEAD", "backend", "frontend"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    ).stdout
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        tar.extractall(target, filter="data")
    shutil.copy(DEPLOY_DIR / "Dockerfile", target / "Dockerfile")
    for path in extra_files:
        shutil.copy(path, target / path.name)
