# Copyright (C) 2023 - 2026 Synopsys, Inc. and ANSYS, Inc. All rights reserved.
# SPDX-License-Identifier: MIT
#
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import gc
import socket
import sys

from PySide6 import QtCore
import pytest

from ansys.tools.installer.mcp_process import CommandQueue, McpServer


def _free_port():
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def test_command_queue_is_async_and_stops_on_failure(qtbot, tmp_path):
    queue = CommandQueue()
    marker = tmp_path / "should not exist"
    ticks = []
    QtCore.QTimer.singleShot(20, lambda: ticks.append(True))
    with qtbot.waitSignal(queue.completed, timeout=10000) as completion:
        queue.start(
            [
                [
                    sys.executable,
                    "-c",
                    "import time; time.sleep(.15); print('output'); exit(7)",
                ],
                [sys.executable, "-c", f"open({str(marker)!r}, 'w').close()"],
            ]
        )
    assert completion.args[0] is False
    assert "7" in completion.args[1]
    assert ticks
    assert not marker.exists()
    assert not queue.active


def test_command_queue_handles_missing_executable(qtbot, tmp_path):
    queue = CommandQueue()
    with qtbot.waitSignal(queue.completed, timeout=5000) as completion:
        queue.start([[str(tmp_path / "missing-program")]])
    assert completion.args[0] is False
    assert not queue.active


def test_command_cancel_reaps_process(qtbot):
    queue = CommandQueue()
    queue.start([[sys.executable, "-c", "import time; time.sleep(60)"]])
    qtbot.waitUntil(lambda: queue.process.state() == QtCore.QProcess.Running)
    with qtbot.waitSignal(queue.completed, timeout=5000) as completion:
        queue.cancel()
    assert completion.args[0] is False
    assert "cancelled" in completion.args[1]
    assert queue.process.state() == QtCore.QProcess.NotRunning


HTTP_FIXTURE = """
from http.server import BaseHTTPRequestHandler, HTTPServer
import json, sys
class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        body = self.rfile.read(int(self.headers['Content-Length']))
        request = json.loads(body)
        assert request['method'] == 'initialize'
        data = DATA
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
HTTPServer(('127.0.0.1', int(sys.argv[1])), Handler).serve_forever()
"""


@pytest.mark.parametrize("valid", [True, False])
def test_http_readiness_requires_mcp_handshake(qtbot, valid):
    port = _free_port()
    data = (
        {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "serverInfo": {"name": "fixture", "version": "1"},
            },
        }
        if valid
        else {"status": "ok"}
    )
    script = HTTP_FIXTURE.replace("DATA", repr(data))
    server = McpServer()
    try:
        server.start(sys.executable, ["-u", "-c", script, str(port)], port)
        if valid:
            qtbot.waitUntil(lambda: server.state.startswith("Ready:"), timeout=10000)
        else:
            qtbot.wait(1600)
            assert server.active
            assert server.state.startswith("Starting")
    finally:
        server.shutdown()
    assert not server.active


def test_occupied_port_does_not_attach_to_existing_server(qtbot):
    server = McpServer()
    with socket.socket() as occupied:
        occupied.bind(("127.0.0.1", 0))
        occupied.listen()
        with pytest.raises(OSError):
            server.start(sys.executable, ["-c", "pass"], occupied.getsockname()[1])
    assert not server.active


def test_early_exit_and_timeout_are_never_ready(qtbot):
    server = McpServer()
    server.start(sys.executable, ["-c", "exit(3)"], _free_port())
    qtbot.waitUntil(lambda: server.state.startswith("Exited"), timeout=5000)
    assert "3" in server.state
    server.start(sys.executable, ["-c", "import time; time.sleep(60)"], _free_port())
    qtbot.waitUntil(lambda: server.active)
    server.deadline = 0
    server._probe()
    qtbot.waitUntil(lambda: not server.active, timeout=5000)
    assert not server.state.startswith("Ready")


def test_shutdown_terminates_persistent_child_worker(qtbot):
    port = _free_port()
    child = (
        "import socket,time; s=socket.socket(); "
        f"s.bind(('127.0.0.1',{port})); s.listen(); "
        "print('CHILD_READY',flush=True); time.sleep(15)"
    )
    parent = (
        "import subprocess,sys,time; "
        f"subprocess.Popen([sys.executable,'-u','-c',{child!r}]); time.sleep(30)"
    )
    server = McpServer()
    output = []
    server.output.connect(output.append)
    try:
        server.process.start(sys.executable, ["-u", "-c", parent])
        qtbot.waitUntil(lambda: "CHILD_READY" in "".join(output), timeout=10000)
        server.shutdown()
        assert not server.active

        # A child that survived its parent would still own this listening port.
        def released():
            try:
                with socket.socket() as probe:
                    probe.bind(("127.0.0.1", port))
                return True
            except OSError:
                return False

        qtbot.waitUntil(released, timeout=3000)
    finally:
        server.shutdown()


def test_stopped_servers_can_be_destroyed_with_pending_kill_timer(qtbot):
    for _ in range(5):
        server = McpServer()
        server.process.start(sys.executable, ["-c", "import time; time.sleep(60)"])
        qtbot.waitUntil(lambda: server.active)
        server.shutdown()
        server.deleteLater()
        del server
        gc.collect()
        qtbot.wait(1)
    # Run beyond the former singleShot callback's two-second deadline.
    qtbot.wait(2100)
