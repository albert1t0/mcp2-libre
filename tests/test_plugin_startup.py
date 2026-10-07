"""Plugin startup tests without an installed LibreOffice extension."""

import importlib.util
import io
import os
import shutil
import subprocess
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest


PLUGIN_DIR = Path(__file__).resolve().parents[1] / "plugin"


def load_module(name):
    spec = importlib.util.spec_from_file_location(name, PLUGIN_DIR / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def launcher():
    return load_module("start_server")


def test_reuses_healthy_server_without_launching(launcher, monkeypatch):
    monkeypatch.setattr(launcher, "is_healthy", lambda **kwargs: True)
    popen = Mock()
    monkeypatch.setattr(launcher.subprocess, "Popen", popen)
    assert launcher.ensure_server()
    popen.assert_not_called()


def test_launches_extension_and_waits_for_health(launcher, monkeypatch):
    health = Mock(side_effect=[False, False, True])
    monkeypatch.setattr(launcher, "is_healthy", health)
    # LibreOffice's CLI exits zero after forwarding to an existing process.
    popen = Mock(return_value=SimpleNamespace(poll=lambda: 0))
    monkeypatch.setattr(launcher.subprocess, "Popen", popen)
    assert launcher.ensure_server(timeout=1)
    assert health.call_count == 3
    assert popen.call_args.args[0] == [
        "libreoffice", "--norestore", launcher.START_URL
    ]


@pytest.mark.parametrize("returncode", [None, 0, 1])
def test_never_runs_ahead_of_failed_startup(launcher, monkeypatch, returncode):
    monkeypatch.setattr(launcher, "is_healthy", lambda **kwargs: False)
    monkeypatch.setattr(
        launcher.subprocess, "Popen",
        Mock(return_value=SimpleNamespace(poll=lambda: returncode)),
    )
    assert not launcher.ensure_server(timeout=0.02)


@pytest.mark.parametrize("body,expected", [
    (b'{"status":"healthy","server":"LibreOffice MCP Extension"}', True),
    (b'{"status":"healthy","server":"Other server"}', False),
    (b'{"status":"starting","server":"LibreOffice MCP Extension"}', False),
    (b'[]', False),
    (b'<html>not a health check</html>', False),
])
def test_health_validates_response_identity(launcher, monkeypatch, body, expected):
    response = io.BytesIO(body)
    response.status = 200
    monkeypatch.setattr(launcher.OPENER, "open", Mock(return_value=response))
    assert launcher.is_healthy() is expected


def test_connection_refused_is_not_healthy(launcher, monkeypatch):
    monkeypatch.setattr(
        launcher.OPENER, "open", Mock(side_effect=ConnectionRefusedError)
    )
    assert not launcher.is_healthy()


@pytest.mark.parametrize("success", [False, True])
def test_client_exit_code_matches_result(monkeypatch, success):
    client = load_module("test_plugin")
    monkeypatch.setattr(client.sys, "argv", ["test_plugin.py"])
    monkeypatch.setattr(
        client.LibreOfficeMCPClient, "run_comprehensive_test", lambda self: success
    )
    assert client.main() == (0 if success else 1)


def test_create_failure_does_not_edit_existing_document(monkeypatch):
    module = load_module("test_plugin")
    client = module.LibreOfficeMCPClient()
    monkeypatch.setattr(client, "test_connection", lambda: True)
    monkeypatch.setattr(client, "get_server_info", lambda: {"name": "test"})
    monkeypatch.setattr(client, "list_tools", lambda: {"tools": []})
    tools = Mock(side_effect=[
        {"success": False, "error": "No document available"},
        {"success": False, "error": "Cannot create"},
    ])
    monkeypatch.setattr(client, "execute_tool", tools)
    assert client.run_comprehensive_test() is False
    assert [call.args[0] for call in tools.call_args_list] == [
        "get_document_info_live", "create_document_live"
    ]


@pytest.mark.parametrize("startup_status,client_status", [(0, 0), (1, 0), (0, 7)])
def test_install_test_gates_client_on_startup(tmp_path, startup_status, client_status):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    scripts = {
        "libreoffice": '#!/bin/sh\nprintf "LibreOffice test\\n"\n',
        "unopkg": '#!/bin/sh\nprintf "org.mcp.libreoffice.extension\\n"\n',
        "python3": f"""#!/bin/sh
case "$1" in
    */start_server.py)
        printf 'STARTUP_CHECK\\n'
        exit {startup_status}
        ;;
    test_plugin.py)
        printf 'CLIENT_EXECUTED\\n'
        exit {client_status}
        ;;
esac
""",
    }
    for name, content in scripts.items():
        path = bin_dir / name
        path.write_text(content)
        path.chmod(0o755)
    result = subprocess.run(
        ["bash", str(PLUGIN_DIR / "install.sh"), "test"],
        env={**os.environ, "PATH": str(bin_dir) + os.pathsep + os.environ["PATH"]},
        capture_output=True, text=True, timeout=5,
    )
    assert result.returncode == (startup_status or client_status)
    assert "STARTUP_CHECK" in result.stdout
    assert ("CLIENT_EXECUTED" in result.stdout) == (startup_status == 0)


def test_built_extension_contains_all_declared_files(tmp_path):
    plugin = tmp_path / "plugin"
    shutil.copytree(PLUGIN_DIR, plugin, ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copy(PLUGIN_DIR.parent / "LICENSE", tmp_path / "LICENSE")
    subprocess.run(["bash", str(plugin / "build.sh")], check=True, timeout=10)
    with zipfile.ZipFile(tmp_path / "build/libreoffice-mcp-extension.oxt") as archive:
        manifest = ET.fromstring(archive.read("META-INF/manifest.xml"))
        for entry in manifest:
            path = entry.attrib["{http://openoffice.org/2001/manifest}full-path"]
            assert path in archive.namelist()
        description = ET.fromstring(archive.read("description.xml"))
        for element in description.iter():
            href = element.attrib.get("{http://www.w3.org/1999/xlink}href")
            if href and not href.startswith("https://"):
                assert href in archive.namelist()
