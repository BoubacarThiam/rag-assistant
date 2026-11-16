"""Deploy the app to a Hugging Face Space (Docker), reading the settings from `.env`.

Note: Docker Spaces on the free CPU hardware need a Hugging Face PRO subscription.

Usage, from the repository root:
    uv run --project backend --with huggingface_hub python deploy/huggingface/deploy.py

Required in `.env`:
    HF_TOKEN              Hugging Face token with "write" access
    HF_SPACE              e.g. my-name/rag-assistant (created if it does not exist)
    DEPLOY_DATABASE_URL   PostgreSQL with pgvector, e.g. the Neon connection string
    DEMO_PASSWORD         password asked to visitors
    LLM_API_KEY or ANTHROPIC_API_KEY, depending on LLM_PROVIDER

Only committed files are sent: commit before deploying. Secrets become Space secrets
(encrypted, never in the image or the repository).
"""

import sys
import tempfile
from pathlib import Path

from huggingface_hub import HfApi

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import SECRETS, app_settings, build_context, load_env

HERE = Path(__file__).resolve().parent


def main() -> None:
    env = load_env(["HF_TOKEN", "HF_SPACE", "DEPLOY_DATABASE_URL", "DEMO_PASSWORD"])
    api = HfApi(token=env["HF_TOKEN"])
    space = env["HF_SPACE"]
    api.create_repo(space, repo_type="space", space_sdk="docker", exist_ok=True)

    secret_names = set(SECRETS.values())
    for name, value in app_settings(env).items():
        if name in secret_names:
            api.add_space_secret(space, name, value)
            print(f"Secret {name} enregistré")
        else:
            api.add_space_variable(space, name, value)
            print(f"Variable {name}={value}")

    with tempfile.TemporaryDirectory() as tmp:
        build_context(Path(tmp), (HERE / "README.md",))
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
