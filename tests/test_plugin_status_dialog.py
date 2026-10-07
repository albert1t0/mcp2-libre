"""Tests for the LibreOffice MCP server status dialog."""

import importlib.util
import sys
import types
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest


REGISTRATION_PATH = (
    Path(__file__).resolve().parents[1] / "plugin/pythonpath/registration.py"
)


def load_registration(monkeypatch):
    """Load the UNO extension module with minimal interfaces stubbed."""
    uno = types.ModuleType("uno")
    unohelper = types.ModuleType("unohelper")
    unohelper.Base = type("Base", (), {})
    unohelper.ImplementationHelper = type(
        "ImplementationHelper",
        (),
        {"addImplementation": lambda *args: None},
    )

    for module_name in ("com", "com.sun", "com.sun.star"):
        module = types.ModuleType(module_name)
        module.__path__ = []
        monkeypatch.setitem(sys.modules, module_name, module)

    for module_name, interface_name in (
        ("com.sun.star.task", "XJobExecutor"),
        ("com.sun.star.lang", "XServiceInfo"),
    ):
        module = types.ModuleType(module_name)
        setattr(module, interface_name, type(interface_name, (), {}))
        monkeypatch.setitem(sys.modules, module_name, module)

    monkeypatch.setitem(sys.modules, "uno", uno)
    monkeypatch.setitem(sys.modules, "unohelper", unohelper)
    spec = importlib.util.spec_from_file_location(
        "_registration_status_dialog_test", REGISTRATION_PATH
    )
    registration = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, registration)
    spec.loader.exec_module(registration)
    return registration


@pytest.mark.parametrize(
    "status,expected",
    [
        (
            {
                "running": True,
                "started": True,
                "thread_alive": True,
                "host": "127.0.0.1",
                "port": 8765,
                "url": "http://127.0.0.1:8765",
            },
            (
                "Server: Running\n"
                "Extension: Started\n"
                "HTTP listener thread: Running\n"
                "Endpoint: http://127.0.0.1:8765\n"
                "Health check: http://127.0.0.1:8765/health"
            ),
        ),
        (
            {"running": False, "started": False},
            (
                "Server: Stopped\n"
                "Extension: Stopped\n"
                "HTTP listener thread: Not started\n"
                "Endpoint: http://localhost:8765\n"
                "Health check: http://localhost:8765/health"
            ),
        ),
    ],
)
def test_status_message_reports_listener_and_endpoint(monkeypatch, status, expected):
    registration = load_registration(monkeypatch)
    assert registration.MCPExtension._format_status_message(status) == expected


def test_get_status_menu_action_shows_and_disposes_dialog(monkeypatch):
    registration = load_registration(monkeypatch)
    window = object()
    frame = Mock()
    frame.getContainerWindow.return_value = window
    desktop = Mock()
    desktop.getCurrentFrame.return_value = frame
    dialog = Mock()
    toolkit = Mock()
    toolkit.createMessageBox.return_value = dialog
    service_manager = Mock()
    service_manager.createInstanceWithContext.side_effect = [desktop, toolkit]

    extension = object.__new__(registration.MCPExtension)
    extension.ctx = SimpleNamespace(ServiceManager=service_manager)
    extension.started = True
    extension.mcp_server = object()
    extension.ai_interface = SimpleNamespace(get_status=lambda: {
        "running": True,
        "host": "localhost",
        "port": 8765,
        "url": "http://localhost:8765",
        "thread_alive": True,
    })

    extension.trigger("get_status")

    toolkit.createMessageBox.assert_called_once_with(
        window,
        "infobox",
        1,
        "LibreOffice MCP Server Status",
        "Server: Running\n"
        "Extension: Started\n"
        "HTTP listener thread: Running\n"
        "Endpoint: http://localhost:8765\n"
        "Health check: http://localhost:8765/health",
    )
    dialog.execute.assert_called_once_with()
    dialog.dispose.assert_called_once_with()


def test_status_dialog_uses_desktop_parent_when_no_frame(monkeypatch):
    registration = load_registration(monkeypatch)
    desktop_window = object()
    desktop = Mock()
    desktop.getCurrentFrame.return_value = None
    dialog = Mock()
    toolkit = Mock()
    toolkit.getDesktopWindow.return_value = desktop_window
    toolkit.createMessageBox.return_value = dialog
    service_manager = Mock()
    service_manager.createInstanceWithContext.side_effect = [desktop, toolkit]

    extension = object.__new__(registration.MCPExtension)
    extension.ctx = SimpleNamespace(ServiceManager=service_manager)
    extension._show_status_dialog({"running": False})

    assert toolkit.createMessageBox.call_args.args[0] is desktop_window
    dialog.execute.assert_called_once_with()
    dialog.dispose.assert_called_once_with()
