# SPDX-License-Identifier: Apache-2.0
# This file was created or modified with the assistance of an AI (Large Language Model).
from __future__ import annotations

import os
import shutil
import socket
import ssl
import subprocess
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen
from uuid import uuid4

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _compose_cmd() -> list[str] | None:
    if shutil.which("docker") is None:
        return None
    try:
        subprocess.run(
            ["docker", "compose", "version"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
            timeout=20,
        )
        subprocess.run(
            ["docker", "info"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
            timeout=20,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None
    return ["docker", "compose"]


def _docker_tests_enabled() -> bool:
    return os.environ.get("RUN_DOCKER_TESTS") == "1"


def _require_docker_compose() -> list[str]:
    if not _docker_tests_enabled():
        pytest.skip("Set RUN_DOCKER_TESTS=1 to enable Docker integration tests")
    cmd = _compose_cmd()
    if cmd is None:
        pytest.skip("Docker Compose is unavailable or Docker daemon is not accessible")
    return cmd


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_https_ready(port: int, timeout_seconds: int = 90) -> None:
    deadline = time.monotonic() + timeout_seconds
    context = ssl._create_unverified_context()
    url = f"https://127.0.0.1:{port}/upload"
    last_error = "unknown"
    while time.monotonic() < deadline:
        try:
            with urlopen(url, timeout=5, context=context) as response:
                if response.status == 200:
                    return
                last_error = f"unexpected HTTP status: {response.status}"
        except URLError as exc:
            last_error = str(exc)
        time.sleep(2)
    raise AssertionError(f"Timed out waiting for {url}: {last_error}")


def test_docker_compose_build_images() -> None:
    compose = _require_docker_compose()
    subprocess.run(
        [*compose, "-f", "docker-compose.yml", "build", "app", "nginx"],
        cwd=ROOT,
        check=True,
        timeout=900,
    )


def test_docker_compose_up_serves_https() -> None:
    compose = _require_docker_compose()
    project_name = f"patchwork_test_{uuid4().hex[:8]}"
    port = _find_free_port()
    env = os.environ.copy()
    env["PATCHWORK_HTTPS_PORT"] = str(port)
    env.setdefault("SECRET_KEY", "docker-test-secret")

    try:
        subprocess.run(
            [*compose, "-p", project_name, "-f", "docker-compose.yml", "up", "-d", "--build"],
            cwd=ROOT,
            env=env,
            check=True,
            timeout=1200,
        )
        _wait_https_ready(port)
    finally:
        subprocess.run(
            [*compose, "-p", project_name, "-f", "docker-compose.yml", "down", "-v"],
            cwd=ROOT,
            env=env,
            check=False,
            timeout=300,
        )
