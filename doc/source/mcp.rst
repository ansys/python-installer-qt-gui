PyAnsys MCP management
======================

The **PyAnsys MCPs** tab installs the public Ansys Model Context Protocol
(MCP) servers and configures coding agents to use them. Each product has a
separate Python environment, so installing one server does not change another
server's dependencies. The manager itself continues to support Python 3.10
and later; the MCP environments need newer Python versions.

Supported servers
-----------------

.. list-table:: Product launch contracts
   :header-rows: 1
   :widths: 22 28 22 28

   * - Product
     - Package
     - Python baseline
     - Transports
   * - `PyAEDT MCP <https://github.com/ansys/pyaedt-mcp>`_
     - ``ansys-aedt-mcp``
     - 3.13–3.14
     - Stdio, HTTP
   * - `PyMechanical MCP <https://github.com/ansys/pymechanical-mcp>`_
     - ``ansys-mechanical-mcp``
     - 3.12+
     - Stdio, HTTP
   * - `PyFluent MCP <https://github.com/ansys/pyfluent-mcp>`_
     - ``ansys-fluent-mcp``
     - 3.12+
     - Stdio, HTTP
   * - `PyMAPDL MCP <https://github.com/ansys/pymapdl-mcp>`_
     - ``ansys-mapdl-mcp``
     - 3.12–3.14
     - Stdio, HTTP
   * - `PyLumerical MCP <https://github.com/ansys/pylumerical-mcp>`_
     - ``ansys-lumerical-mcp``
     - 3.12+
     - Stdio
   * - `PyCFX MCP <https://github.com/ansys/pycfx-mcp>`_
     - ``ansys-cfx-mcp``
     - 3.12–3.14
     - Stdio, HTTP

These baselines follow the reviewed source contracts. Pip also checks the
requirements of the selected release and its dependencies. In particular,
the published PyLumerical 0.1.0 package allows Python 3.11, while current
development requires Python 3.12. This manager uses the 3.12 baseline.
``ansys-common-mcp`` is a framework dependency installed by the product
packages, rather than a separate solver server in the catalog.

Ansys products and appropriate licenses must be installed or accessible
separately. Consult each server's setup guide for supported solver versions,
platforms, and local or remote connection requirements. Installing an MCP
package does not install or license an Ansys solver.

Install a server
----------------

#. Install a compatible 64-bit Python using **Install Python**, or use an
   existing installation. Python 3.13 is a useful common baseline.
#. Select a product in **PyAnsys MCPs**, then open **Installation**.
#. Select the Python executable with **Browse**, or use the Python selected
   in **Create virtual environments**. The packaged manager executable cannot
   itself act as the environment's Python interpreter.
#. Use the product's managed environment, or choose an existing virtual or
   conda environment. Existing system Python installations are rejected as
   installation targets. Stop the manager's server before changing its environment.
#. Select a PyPI release (leave **Latest compatible** to let pip resolve it),
   or an official Git branch, tag or commit. Git installations require Git.
#. Click **Install**. **Update / repair** adds pip's upgrade option. The log
   shows progress and errors, and the final step checks dependency consistency.

Managed environments and settings are under
``~/.ansys/ansys_python_manager/mcp``. Managed environments also appear in
**Manage Python environments**. Cancelling an installation can leave a
partial environment; retry **Update / repair** to finish it. A cancelled or
failed installation is never reported as successful.

On Linux, uninstalling the manager offers separate options to remove settings
and managed environments. Removing settings preserves MCP environments;
removing managed environments includes the product environments. Existing
custom environments outside the manager's configured locations are preserved.

For an offline installation, select **Offline** and provide a directory of
wheels or a wheelhouse ZIP. Include the chosen MCP package and all dependencies,
including build dependencies if distributing source packages. Wheels must
match the target operating system, architecture and Python version. The
manager passes ``--no-index`` to pip and does not fetch version metadata
automatically. Git sources are unavailable in offline mode. ZIP extraction
rejects traversal paths and symbolic links.

Connect a coding agent
----------------------

For one local coding agent, use **stdio**. The agent starts the installed
MCP console script directly. The manager does not need to remain open.
For shared HTTP access, use **Start HTTP server** under **Server settings**.
The manager binds to ``127.0.0.1`` and waits for an MCP initialize response
before reporting readiness. Its servers stop when the manager exits.

HTTP transport ports are distinct from Ansys solver connection ports.
PyAEDT, PyMechanical and PyMAPDL expose solver connection fields. PyAEDT also
offers graphical mode, context tools and dynamic tool discovery. Additional
documented product options can be entered as a JSON string array, for example:

.. code-block:: json

   ["--transport-mode", "mtls", "--certs-dir", "C:/Ansys certificates"]

Environment overrides are a JSON object of string names and values. They are
passed to manager-owned HTTP processes and included in stdio client profiles.
Settings, profiles and backups store these values as plain text.

Under **Coding agents**, select VS Code, Copilot CLI, Claude Desktop, Cursor,
Codex or OpenCode. Review the destination file path. For VS Code, choose
``.vscode/mcp.json`` inside the intended workspace. Claude Desktop's local
configuration supports stdio here; PyLumerical offers stdio only.

Click **Preview profile**, review the complete merged document, then click
**Install previewed profile**. The manager preserves unrelated entries,
backs up existing files and replaces the destination atomically. It refuses
to overwrite a file changed after preview. Codex TOML comments are preserved.
JSON files must be strict JSON: files containing comments or duplicate keys
are rejected without modification. Merge the preview manually when a client
uses JSON with comments. Reload or restart the coding agent after saving.

The generated profiles reference the selected environment. Regenerate them
after changing the environment or connection settings. An HTTP profile uses
the selected HTTP port; start that server before connecting the client.

Architecture and validation
---------------------------

The existing ``main`` module composes the Python installation, environment
creation and package-management tabs. ``find_python`` discovers registry,
Ansys, conda and configured virtual environments. Platform-specific installers
and terminal launchers remain in ``windows_functions`` and ``linux_functions``.
``configure_json`` owns the existing environment search settings; updates and
PyInstaller/NSIS/Linux packaging remain independent of MCP package installation.

The MCP integration uses a separate native PySide6 tab. The
`PyAEDT desktop application <https://github.com/ansys/pyaedt-mcp/tree/main/desktop_app>`_
informed its installation, server controls, advanced settings, logs, and
profile workflows. Its Flet UI, Windows embedded runtime, tray integration,
and product-specific executable detection are not dependencies of this Qt app.

``mcp_catalog`` defines package and CLI differences. ``mcp_backend`` handles
installation plans, metadata, settings and wheelhouses. ``mcp_process`` owns
asynchronous subprocesses and HTTP readiness. ``mcp_owned_process`` contains
their descendants in Windows jobs or Unix process sessions, so persistent
Python workers stop with the server. ``mcp_profiles`` merges client
configurations, and ``mcp_tab`` connects these services to Qt. Adding a product
requires verifying its published package, Python requirements, launch command,
transports and client interoperability before extending the catalog and tests.

The automated suite exercises installation using a small offline wheel,
profile preservation, product-specific arguments, settings, real subprocesses,
cancellation and protocol readiness. CI runs on Windows and Ubuntu 22.04/24.04,
with container tests on CentOS Stream 9 and Fedora 40. Reproduce the latter with
``scripts/mcp-validation.Dockerfile``.

For opt-in testing against published packages, run:

.. code-block:: console

   python scripts/validate_mcp.py --python /path/to/python3.13 --root /tmp/apm-mcp

This installs the selected products through the Qt installation pipeline,
performs stdio initialization and tool discovery, and checks HTTP initialization
where supported. It writes ``validation.json`` beneath the validation root.
It does not exercise solver execution or licensing; those checks require
the corresponding product installations and licenses.
