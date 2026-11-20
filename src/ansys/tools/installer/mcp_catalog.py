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

"""Verified product contracts for the public PyAnsys MCP servers.

Keep CLI differences here rather than assuming all servers share the common MCP
launcher. See the repository links and ``doc/source/mcp.rst`` before updating.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class McpProduct:
    """Describe a product's package, launcher and supported transports."""

    key: str
    name: str
    package: str
    python: str
    description: str
    http_flags: tuple[str, str] | None = ("--http-host", "--http-port")
    connect_flag: str = ""
    machine_flag: str = "--ip"
    product_port: int = 0

    @property
    def repository(self):
        """Return the official source repository."""
        return f"https://github.com/ansys/{self.key}-mcp"

    @property
    def documentation(self):
        """Return the official installation guide used to verify this contract."""
        product = self.package.removeprefix("ansys-").removesuffix("-mcp")
        return f"https://{product}-mcp.docs.pyansys.com/version/stable/getting_started/installation.html"


PRODUCTS = (
    McpProduct(
        "pyaedt",
        "PyAEDT MCP",
        "ansys-aedt-mcp",
        ">=3.13,<3.15",
        "Electronics Desktop: HFSS, Maxwell, Icepak, Q3D and circuit workflows.",
        connect_flag="--connect",
        machine_flag="--machine",
        product_port=50051,
    ),
    McpProduct(
        "pymechanical",
        "PyMechanical MCP",
        "ansys-mechanical-mcp",
        ">=3.12,<3.15",
        "Mechanical: remote sessions, models, analyses, scripts and results.",
        connect_flag="--connect-on-startup",
        product_port=10000,
    ),
    McpProduct(
        "pyfluent",
        "PyFluent MCP",
        "ansys-fluent-mcp",
        ">=3.12,<4",
        "Fluent: CFD solver sessions, setup, execution and post-processing.",
        http_flags=("--host", "--port"),
    ),
    McpProduct(
        "pymapdl",
        "PyMAPDL MCP",
        "ansys-mapdl-mcp",
        ">=3.12,<3.15",
        "Mechanical APDL: sessions, modeling, solving, files and results.",
        connect_flag="--connect-on-startup",
        product_port=50052,
    ),
    McpProduct(
        "pylumerical",
        "PyLumerical MCP",
        "ansys-lumerical-mcp",
        ">=3.11,<4",
        "Lumerical: FDTD, MODE, DEVICE and INTERCONNECT sessions. Stdio only.",
        http_flags=None,
    ),
    McpProduct(
        "pycfx",
        "PyCFX MCP",
        "ansys-cfx-mcp",
        ">=3.12,<3.15",
        "CFX: solver sessions and CFD simulation workflows.",
        http_flags=("--host", "--port"),
    ),
)

PRODUCT_BY_KEY = {product.key: product for product in PRODUCTS}
