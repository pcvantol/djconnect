from __future__ import annotations

import ast
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class HttpRouteRegistrationTest(unittest.TestCase):
    def test_config_entry_setup_registers_http_views(self) -> None:
        """Configured integrations restore the public HTTP views at startup."""
        module = ast.parse(
            (ROOT / "custom_components" / "djconnect" / "__init__.py").read_text(
                encoding="utf-8"
            )
        )
        setup_entry = next(
            node
            for node in module.body
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "async_setup_entry"
        )
        calls = [
            node
            for node in ast.walk(setup_entry)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "register_http_views"
            and len(node.args) == 1
            and isinstance(node.args[0], ast.Name)
            and node.args[0].id == "hass"
        ]

        self.assertEqual(len(calls), 1)

    def test_parameterless_http_views_are_not_constructed_with_hass(self) -> None:
        """Startup registration must match each view's constructor contract."""
        module = ast.parse(
            (ROOT / "custom_components" / "djconnect" / "__init__.py").read_text(
                encoding="utf-8"
            )
        )
        register = next(
            node
            for node in module.body
            if isinstance(node, ast.FunctionDef) and node.name == "register_http_views"
        )
        constructors = {
            node.func.id: node
            for node in ast.walk(register)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }

        self.assertEqual(constructors["DJConnectTransportCapabilitiesView"].args, [])
        self.assertEqual(constructors["DJConnectUniversalReceiverView"].args, [])
        self.assertEqual(constructors["DJConnectVibeCastRendererView"].args, [])
