"""Activate the installed extension inside LibreOffice before HTTP tests."""

import json
import subprocess
import sys
import tempfile
import time
from urllib.request import ProxyHandler, build_opener


HEALTH_URL = "http://localhost:8765/health"
START_URL = "service:org.mcp.libreoffice.MCPExtension?start_mcp_server"
OPENER = build_opener(ProxyHandler({}))


def is_healthy(timeout=1):
    """Do not mistake another service's HTTP 200 for a ready extension."""
    try:
        with OPENER.open(HEALTH_URL, timeout=timeout) as response:
            data = json.load(response)
            return (
                response.status == 200
                and isinstance(data, dict)
                and data.get("status") == "healthy"
                and data.get("server") == "LibreOffice MCP Extension"
            )
    except (OSError, ValueError):
        return False


def ensure_server(timeout=15):
    """Reuse a healthy server or ask LibreOffice to start the installed plugin."""
    if is_healthy():
        print("MCP server is already healthy")
        return True

    print("Starting the MCP extension inside LibreOffice...", flush=True)
    # A new office process may outlive this launcher; do not pipe its output
    # or kill it when tests finish, since it can own the user's documents.
    with tempfile.TemporaryFile(mode="w+") as log:
        process = subprocess.Popen(
            ["libreoffice", "--norestore", START_URL],
            stdout=log,
            stderr=log,
            start_new_session=True,
        )
        deadline = time.monotonic() + timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            if is_healthy(timeout=min(1, remaining)):
                print("MCP server is healthy at http://localhost:8765")
                return True
            if process.poll() not in (None, 0):
                break
            time.sleep(min(0.25, max(0, deadline - time.monotonic())))

        log.seek(0)
        print(log.read(), file=sys.stderr, end="")

    print(
        "MCP server did not become healthy. Install/rebuild the extension, "
        "then restart LibreOffice after saving your documents. "
        "Check that port 8765 is free and the extension is enabled.",
        file=sys.stderr,
    )
    return False


if __name__ == "__main__":
    try:
        sys.exit(0 if ensure_server() else 1)
    except OSError as exc:
        print(f"Could not start LibreOffice: {exc}", file=sys.stderr)
        sys.exit(1)
