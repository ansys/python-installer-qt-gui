"""Opt-in live MCP validation; installs packages but does not launch Ansys solvers.

Run with the manager's development Python. Example::

    python scripts/validate_mcp.py --python /path/to/python3.13 --root /tmp/apm-mcp

This exercises the real Qt installation pipeline, stdio initialize/tools/list,
and HTTP readiness. It writes a machine-readable report beneath the given root.
"""

import argparse
import json
from pathlib import Path
import queue
import socket
import subprocess
import threading
import time

from PySide6 import QtWidgets

from ansys.tools.installer.mcp_backend import (
    console_executable,
    installed_version,
)
from ansys.tools.installer.mcp_catalog import PRODUCTS
from ansys.tools.installer.mcp_tab import McpTab


def stdio_probe(executable, arguments, timeout=90):
    """Initialize a real server and list its tools without calling solver tools."""
    messages = queue.Queue()
    errors = []
    process = subprocess.Popen(
        [str(executable), *arguments],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    def read_output():
        for line in process.stdout:
            try:
                messages.put(json.loads(line))
            except ValueError:
                errors.append(line)

    def read_errors():
        for line in process.stderr:
            errors.append(line)

    readers = [
        threading.Thread(target=read_output, daemon=True),
        threading.Thread(target=read_errors, daemon=True),
    ]
    for reader in readers:
        reader.start()

    def send(message):
        process.stdin.write(json.dumps({"jsonrpc": "2.0", **message}) + "\n")
        process.stdin.flush()

    def response(identifier):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError(
                    f"Server exited {process.returncode}: {''.join(errors)[-8000:]}"
                )
            try:
                message = messages.get(timeout=0.2)
            except queue.Empty:
                continue
            if message.get("id") == identifier:
                if "error" in message:
                    raise RuntimeError(str(message["error"]))
                return message["result"]
        raise TimeoutError(f"MCP response timed out: {''.join(errors)[-8000:]}")

    try:
        send(
            {
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {},
                    "clientInfo": {"name": "apm-validation", "version": "1"},
                },
            }
        )
        initialized = response(1)
        send({"method": "notifications/initialized"})
        send({"id": 2, "method": "tools/list", "params": {}})
        tools = response(2)["tools"]
        if not tools:
            raise RuntimeError("Server returned no tools.")
        return {"server": initialized["serverInfo"], "tools": len(tools)}
    finally:
        process.stdin.close()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        for reader in readers:
            reader.join(timeout=2)
        process.stdout.close()
        process.stderr.close()


def main():
    """Run the requested products through installation and protocol validation."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python", required=True, help="64-bit Python 3.13 executable")
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument(
        "--products", nargs="*", choices=[product.key for product in PRODUCTS]
    )
    parser.add_argument("--skip-install", action="store_true")
    args = parser.parse_args()
    app = QtWidgets.QApplication([])
    tab = McpTab(directory=args.root.absolute())
    report = {}
    try:
        for index, product in enumerate(PRODUCTS):
            if args.products and product.key not in args.products:
                continue
            tab.product_select.setCurrentIndex(index)
            result = {}
            report[product.key] = result
            print(f"Validating {product.name}…", flush=True)
            try:
                if not args.skip_install:
                    tab.select_python(args.python)
                    tab._install(False)
                    deadline = time.monotonic() + 1500
                    while tab.queue.active or tab._preparing:
                        app.processEvents()
                        if time.monotonic() > deadline:
                            tab.queue.shutdown()
                            raise TimeoutError("Installation timed out.")
                        time.sleep(0.01)
                    if "completed" not in tab.status.text():
                        raise RuntimeError(
                            tab.status.text() + "\n" + tab.log.toPlainText()[-12000:]
                        )
                result["version"] = installed_version(tab.environment, product)
                tab._load_launch_options()
                deadline = time.monotonic() + 60
                while tab._launch_context != tab._launch_signature():
                    app.processEvents()
                    if time.monotonic() > deadline:
                        raise RuntimeError(tab.launch_hint.text())
                    time.sleep(0.01)
                result["launch_options"] = [
                    option["flags"][0] for option in tab._launch_schema
                ]
                command = console_executable(tab.environment, product)
                result["stdio"] = stdio_probe(command, tab._arguments("stdio"))
                if product.http_flags:
                    with socket.socket() as probe:
                        probe.bind(("127.0.0.1", 0))
                        port = probe.getsockname()[1]
                    tab.http_port.setValue(port)
                    tab._start_server()
                    server = tab.servers[product.key]
                    deadline = time.monotonic() + 70
                    while (
                        server.active
                        and not server.state.startswith("Ready:")
                        and time.monotonic() < deadline
                    ):
                        app.processEvents()
                        time.sleep(0.01)
                    if not server.state.startswith("Ready:"):
                        raise RuntimeError(
                            server.state + "\n" + tab.log.toPlainText()[-10000:]
                        )
                    result["http"] = "initialize passed"
                    server.shutdown()
                else:
                    result["http"] = "unsupported by product launcher"
                result["passed"] = True
                print(json.dumps(result), flush=True)
            except Exception as error:
                result["passed"] = False
                result["error"] = str(error)
                print(str(error), flush=True)
            finally:
                args.root.mkdir(parents=True, exist_ok=True)
                (args.root / "validation.json").write_text(
                    json.dumps(report, indent=2) + "\n", encoding="utf-8"
                )
    finally:
        tab.shutdown()
    return (
        0 if report and all(result.get("passed") for result in report.values()) else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
