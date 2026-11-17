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

"""Asynchronous, owned subprocesses for installation and HTTP MCP servers."""

import codecs
import json
import socket
import time

from PySide6 import QtCore, QtNetwork

from ansys.tools.installer.mcp_owned_process import OwnedProcess


def process_environment(overrides=None):
    """Keep the user environment while removing frozen Python startup variables."""
    environment = QtCore.QProcessEnvironment.systemEnvironment()
    for key in ("PYTHONHOME", "PYTHONPATH", "VIRTUAL_ENV"):
        environment.remove(key)
    environment.insert("PYTHONUNBUFFERED", "1")
    environment.insert("PYTHONIOENCODING", "utf-8")
    for key, value in (overrides or {}).items():
        environment.insert(key, value)
    return environment


class CommandQueue(QtCore.QObject):
    """Run an installation plan without blocking the GUI or invoking a shell."""

    output = QtCore.Signal(str)
    completed = QtCore.Signal(bool, str)

    def __init__(self, parent=None):
        """Create one reusable process and its timeout watchdog."""
        super().__init__(parent)
        self.process = OwnedProcess(self)
        self.process.setProcessChannelMode(QtCore.QProcess.MergedChannels)
        self.process.setProcessEnvironment(process_environment())
        self.process.readyReadStandardOutput.connect(self._read)
        self.process.finished.connect(self._finished)
        self.process.errorOccurred.connect(self._error)
        self.timer = QtCore.QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(lambda: self.cancel("Command timed out."))
        self.active = False
        self.commands = []
        self.failure = ""
        self._decoder = codecs.getincrementaldecoder("utf-8")("replace")

    def start(self, commands):
        """Start a new command plan, rejecting overlapping installations."""
        if self.active:
            raise RuntimeError("An MCP operation is already in progress.")
        if not commands:
            raise ValueError("An installation plan must contain commands.")
        self.commands = list(commands)
        self.active = True
        self.failure = ""
        self._next()

    def _next(self):
        if not self.commands:
            self._complete(True, "Installation completed and dependencies checked.")
            return
        command = self.commands.pop(0)
        self._decoder = codecs.getincrementaldecoder("utf-8")("replace")
        self.output.emit(f"\n> {command[0]} {' '.join(command[1:])}\n")
        self.process.start(command[0], command[1:])
        self.timer.start(20 * 60 * 1000)

    def _read(self):
        self.output.emit(
            self._decoder.decode(bytes(self.process.readAllStandardOutput()))
        )

    def _finished(self, code, status):
        self.timer.stop()
        self._read()
        self.output.emit(self._decoder.decode(b"", final=True))
        if not self.active:
            return
        if self.failure or code or status != QtCore.QProcess.NormalExit:
            self._complete(
                False,
                self.failure
                or self.process.ownership_error
                or f"Command failed (exit {code}). See the log.",
            )
        else:
            self._next()

    def _error(self, error):
        if error == QtCore.QProcess.FailedToStart:
            self._complete(False, self.process.errorString())

    def _complete(self, success, message):
        if not self.active:
            return
        self.timer.stop()
        self.active = False
        self.commands = []
        self.completed.emit(success, message)

    def cancel(
        self, message="Installation cancelled. Retry to repair a partial environment."
    ):
        """Terminate the owned command and discard the remaining plan."""
        if not self.active:
            return
        self.failure = message
        self.commands = []
        self.process.terminate()
        QtCore.QTimer.singleShot(2000, self._kill_if_needed)

    def _kill_if_needed(self):
        if self.failure and self.process.state() != QtCore.QProcess.NotRunning:
            self.process.kill()

    def shutdown(self):
        """Reap the command before its QObject owner is destroyed."""
        if self.active:
            self.cancel()
            if not self.process.waitForFinished(2000):
                self.process.kill()
                self.process.waitForFinished(2000)


class McpServer(QtCore.QObject):
    """Own an HTTP server and report readiness after an MCP initialize response."""

    output = QtCore.Signal(str)
    changed = QtCore.Signal(str)

    def __init__(self, parent=None):
        """Initialize the server process and bounded readiness polling."""
        super().__init__(parent)
        self.process = OwnedProcess(self)
        self.process.setProcessChannelMode(QtCore.QProcess.MergedChannels)
        self.process.readyReadStandardOutput.connect(self._read)
        self.process.finished.connect(self._finished)
        self.process.errorOccurred.connect(self._error)
        self.network = QtNetwork.QNetworkAccessManager(self)
        self.network.setProxy(QtNetwork.QNetworkProxy(QtNetwork.QNetworkProxy.NoProxy))
        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(500)
        self.timer.timeout.connect(self._probe)
        self.reply = None
        self.state = "Stopped"
        self.url = ""
        self.deadline = 0
        self._decoder = codecs.getincrementaldecoder("utf-8")("replace")

    @property
    def active(self):
        """Return whether this manager still owns a live or starting process."""
        return self.process.state() != QtCore.QProcess.NotRunning

    def _set_state(self, state):
        self.state = state
        self.changed.emit(state)

    def start(self, executable, arguments, port, environment=None):
        """Launch on loopback, refusing an occupied port before readiness checks."""
        if self.active:
            raise ValueError("This MCP server is already running.")
        with socket.socket() as check:
            if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
                check.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            check.bind(("127.0.0.1", port))
        self.url = f"http://127.0.0.1:{port}/mcp"
        self._decoder = codecs.getincrementaldecoder("utf-8")("replace")
        self.process.setProcessEnvironment(process_environment(environment))
        self.deadline = time.monotonic() + 60
        self._set_state("Starting; waiting for MCP handshake…")
        self.process.start(str(executable), arguments)
        self.timer.start()

    def _read(self):
        self.output.emit(
            self._decoder.decode(bytes(self.process.readAllStandardOutput()))
        )

    def _probe(self):
        if time.monotonic() > self.deadline:
            self.output.emit("\nMCP readiness timed out after 60 seconds.\n")
            self.stop()
            return
        if self.reply is not None or not self.active:
            return
        request = QtNetwork.QNetworkRequest(QtCore.QUrl(self.url))
        request.setHeader(
            QtNetwork.QNetworkRequest.ContentTypeHeader, "application/json"
        )
        request.setRawHeader(b"Accept", b"application/json, text/event-stream")
        request.setTransferTimeout(1500)
        body = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {"name": "Ansys Python Manager", "version": "1"},
            },
        }
        reply = self.network.post(request, json.dumps(body).encode())
        self.reply = reply
        reply.finished.connect(lambda: self._probe_finished(reply))

    def _probe_finished(self, reply):
        if self.reply is reply:
            self.reply = None
        payload = (
            bytes(reply.readAll()).decode("utf-8", errors="replace")
            if reply.isOpen()
            else ""
        )
        status = reply.attribute(QtNetwork.QNetworkRequest.HttpStatusCodeAttribute)
        session = bytes(reply.rawHeader("mcp-session-id"))
        reply.deleteLater()
        if not self.timer.isActive() or status != 200:
            return
        messages = (
            [payload]
            if payload.lstrip().startswith("{")
            else [
                line[5:].strip()
                for line in payload.splitlines()
                if line.startswith("data:")
            ]
        )
        for message in messages:
            try:
                response = json.loads(message)
                result = response.get("result", {})
                if response.get("id") != 1 or not all(
                    key in result
                    for key in ("protocolVersion", "serverInfo", "capabilities")
                ):
                    continue
            except (ValueError, AttributeError, TypeError):
                continue
            self.timer.stop()
            self._set_state(f"Ready: {self.url}")
            if session:
                request = QtNetwork.QNetworkRequest(QtCore.QUrl(self.url))
                request.setRawHeader(b"mcp-session-id", session)
                cleanup = self.network.deleteResource(request)
                cleanup.finished.connect(cleanup.deleteLater)
            return

    def _error(self, error):
        if error == QtCore.QProcess.FailedToStart:
            self.timer.stop()
            self._set_state(f"Failed to start: {self.process.errorString()}")

    def _finished(self, code, status):
        self.timer.stop()
        self._read()
        if self.reply is not None:
            self.reply.abort()
        self._set_state(
            self.process.ownership_error
            or (
                "Stopped"
                if self.state == "Stopping…"
                else f"Exited (code {code}); see log."
            )
        )

    def stop(self):
        """Stop this manager's process, escalating to kill after two seconds."""
        self.timer.stop()
        if self.reply is not None:
            self.reply.abort()
        if self.active:
            self._set_state("Stopping…")
            self.process.terminate()
            QtCore.QTimer.singleShot(2000, self._kill_if_stopping)

    def _kill_if_stopping(self):
        if self.state == "Stopping…" and self.active:
            self.process.kill()

    def shutdown(self):
        """Reap the owned process when the manager closes."""
        self.stop()
        if self.active and not self.process.waitForFinished(2000):
            self.process.kill()
            self.process.waitForFinished(2000)
