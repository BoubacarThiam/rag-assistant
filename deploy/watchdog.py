"""Keep the public demo online: restart what is down and keep the short link up to date.

Every minute:
  1. Docker running? If not, start Docker Desktop and wait for it.
  2. Demo containers up? (`docker compose up -d` is cheap when they already are.)
  3. Public address answering? It is tested from the outside, like a visitor, on the
     password-free health check. After 3 failures in a row, the tunnel is restarted: it
     gets a new address.
  4. Short link pointing to the current address? If not, it is updated (deploy/demo_link.py).

Run it by hand:  python deploy/watchdog.py           (Ctrl+C to stop)
Start it at every Windows sign-in:  powershell -File deploy/install-watchdog.ps1
Activity is written to demo-watchdog.log at the repository root.
"""

import logging
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from logging.handlers import RotatingFileHandler
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from demo_link import (
    COMPOSE,
    PAGE_URL,
    ROOT,
    CommandError,
    latest_tunnel_url,
    publish,
    run,
    wait_for_tunnel_url,
)

CHECK_EVERY_S = 60
FAILURES_BEFORE_RESTART = 3
GRACE_AFTER_RESTART_S = 45  # a new tunnel address takes a few seconds to resolve
DOCKER_DESKTOP = Path.home() / "AppData/Local/Programs/DockerDesktop/Docker Desktop.exe"
LOCK_PORT = 47860  # held while the watchdog runs, so that only one copy runs at a time

log = logging.getLogger("watchdog")


def setup_logging() -> None:
    handler = RotatingFileHandler(
        ROOT / "demo-watchdog.log", maxBytes=500_000, backupCount=1, encoding="utf-8"
    )
    handlers: list[logging.Handler] = [handler]
    if sys.stderr is not None:  # None under pythonw (no console)
        handlers.append(logging.StreamHandler())
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=handlers,
    )


def single_instance() -> socket.socket:
    lock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        lock.bind(("127.0.0.1", LOCK_PORT))
    except OSError:
        log.info("Une surveillance tourne déjà : arrêt de celle-ci.")
        sys.exit(0)
    return lock


def docker_ready() -> bool:
    try:
        run("docker", "info", timeout=30)
        return True
    except (CommandError, subprocess.TimeoutExpired):
        return False


def ensure_docker() -> None:
    if docker_ready():
        return
    if DOCKER_DESKTOP.exists():
        log.info("Docker n'est pas lancé : démarrage de Docker Desktop.")
        subprocess.Popen([str(DOCKER_DESKTOP)])
    for _ in range(60):  # up to ~5 minutes
        time.sleep(5)
        if docker_ready():
            log.info("Docker est prêt.")
            return
    raise CommandError("Docker ne démarre pas.")


def ensure_containers() -> None:
    """Start what is stopped. A failure here must not stop the round: the public check
    below still runs, and a stuck tunnel gets recreated."""
    try:
        run("docker", *COMPOSE, "up", "-d", timeout=600)
    except (CommandError, subprocess.TimeoutExpired) as exc:
        log.warning("Démarrage des conteneurs : %s", exc)


def is_online(url: str) -> bool:
    request = urllib.request.Request(f"{url}/api/health", headers={"User-Agent": "demo-watchdog"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return bool(response.status == 200)
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def restart_tunnel(old_url: str | None) -> str:
    log.warning("Adresse publique injoignable : redémarrage du tunnel.")
    # Recreated rather than restarted: works even if the container is stuck, and the new
    # container's log only holds the new address.
    run("docker", *COMPOSE, "up", "-d", "--force-recreate", "--no-deps", "tunnel", timeout=300)
    url = wait_for_tunnel_url(not_this=old_url)
    log.info("Nouvelle adresse du tunnel : %s", url)
    return url


def update_link(url: str) -> None:
    if publish(url):
        log.info("Lien court mis à jour : %s -> %s", PAGE_URL, url)


def loop() -> None:
    failures = 0
    checked_url: str | None = None
    grace_until = 0.0
    while True:
        try:
            ensure_docker()
            ensure_containers()
            url = latest_tunnel_url() or wait_for_tunnel_url()
            if url != checked_url:  # first round, or the tunnel restarted on its own
                log.info("Adresse du tunnel : %s", url)
                update_link(url)
                checked_url, failures = url, 0
                grace_until = time.monotonic() + GRACE_AFTER_RESTART_S
            if time.monotonic() >= grace_until:
                if is_online(url):
                    if failures:
                        log.info("La démo répond de nouveau.")
                    failures = 0
                else:
                    failures += 1
                    log.warning("Démo injoignable (%d/%d).", failures, FAILURES_BEFORE_RESTART)
                    if failures >= FAILURES_BEFORE_RESTART:
                        url = restart_tunnel(url)
                        update_link(url)
                        checked_url, failures = url, 0
                        grace_until = time.monotonic() + GRACE_AFTER_RESTART_S
        except (CommandError, subprocess.TimeoutExpired) as exc:
            log.error("%s", exc)
        except Exception:  # keep watching whatever happens; the log tells what went wrong
            log.exception("Erreur inattendue")
        time.sleep(CHECK_EVERY_S)


def main() -> None:
    setup_logging()
    lock = single_instance()
    log.info("Surveillance de la démo démarrée.")
    try:
        loop()
    except KeyboardInterrupt:
        log.info("Surveillance arrêtée.")
    finally:
        lock.close()


if __name__ == "__main__":
    main()
