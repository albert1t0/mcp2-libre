"""Regression tests for the LibreOffice plugin HTTP server lifecycle."""

import importlib.util
import json
import sys
import types
from pathlib import Path
from urllib.request import urlopen


def _load_ai_interface(monkeypatch):
    """Load ai_interface.py without requiring LibreOffice's UNO modules."""
    plugin_dir = Path(__file__).resolve().parents[1] / "plugin"
    package_name = "_plugin_test_package"

    package = types.ModuleType(package_name)
    package.__path__ = [str(plugin_dir / "pythonpath")]
    monkeypatch.setitem(sys.modules, package_name, package)

    mcp_server = types.ModuleType(f"{package_name}.mcp_server")
    mcp_server.get_mcp_server = lambda: object()
    monkeypatch.setitem(sys.modules, mcp_server.__name__, mcp_server)

    module_name = f"{package_name}.ai_interface"
    spec = importlib.util.spec_from_file_location(
        module_name, plugin_dir / "pythonpath" / "ai_interface.py"
    )
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, module_name, module)
    spec.loader.exec_module(module)
    return module


def test_start_keeps_health_endpoint_available(monkeypatch):
    module = _load_ai_interface(monkeypatch)
    interface = module.AIInterface(port=0, host="127.0.0.1")

    interface.start()
    try:
        port = interface.server.server_address[1]
        assert interface.server.server_address[0] == "127.0.0.1"
        with urlopen(f"http://127.0.0.1:{port}/health", timeout=2) as response:
            assert response.status == 200
            assert json.loads(response.read()) == {
                "status": "healthy",
                "server": "LibreOffice MCP Extension",
            }
    finally:
        interface.stop()

    assert interface.is_running() is False
    assert not interface.server_thread.is_alive()


def test_stop_releases_socket_for_restart(monkeypatch):
    module = _load_ai_interface(monkeypatch)
    interface = module.AIInterface(port=0, host="127.0.0.1")
    for _ in range(2):
        interface.start()
        try:
            interface.port = interface.server.server_address[1]
            with urlopen(f"http://127.0.0.1:{interface.port}/health", timeout=2) as r:
                assert r.status == 200
        finally:
            interface.stop()
    interface.stop()


def test_thread_start_failure_closes_socket(monkeypatch):
    import pytest

    module = _load_ai_interface(monkeypatch)
    interface = module.AIInterface(port=0, host="127.0.0.1")
    sockets = []

    def fail_to_start(thread):
        sockets.append(interface.server.socket)
        raise RuntimeError("cannot start thread")

    monkeypatch.setattr(module.threading.Thread, "start", fail_to_start)
    with pytest.raises(RuntimeError, match="cannot start thread"):
        interface.start()
    assert sockets[0].fileno() == -1
    assert interface.server is None
    assert not interface.is_running()
