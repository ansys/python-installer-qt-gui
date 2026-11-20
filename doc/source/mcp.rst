Manage PyAnsys MCPs
===================

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
     - 3.12–3.14
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
     - 3.11+
     - Stdio
   * - `PyCFX MCP <https://github.com/ansys/pycfx-mcp>`_
     - ``ansys-cfx-mcp``
     - 3.12–3.14
     - Stdio, HTTP

These ranges follow the official installation guides and package declarations.
Before installation, the manager checks the exact release's ``Requires-Python``
metadata against the selected interpreter and the documented product range.
Git installations read ``requires-python`` from the selected branch or tag;
offline installations read the selected wheel's metadata. For example,
PyLumerical 0.1.0 supports Python 3.11, while current development requires
Python 3.12. Pip also validates the requirements of all dependencies.
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
#. Under **Python environment**, keep **Dedicated environment (recommended)**
   and use **Select Python version**, the same dropdown used by
   **Create virtual environments**. The selector remains available after installation.
   Selecting another Python creates or reuses a separate dedicated environment;
   the previous environment is preserved.
#. To reuse a virtual or conda environment, choose **Existing virtual environment**.
   **Available virtual environments** uses the same discovery as
   **Manage Python environments**. System Python installations are rejected as
   installation targets. Stop the manager's server before changing its environment.
#. Select a PyPI release (leave **Latest** to check the newest published release),
   or an official Git branch, tag, or commit. Git installations require Git.
#. Click **Install MCP**. For an installed MCP, the action becomes **Update / repair**.
   Progress appears below the page; expand **Activity log** for details.
   The final installation step checks dependency consistency.

Managed environments and settings are under
``~/.ansys/ansys_python_manager/mcp``. Managed environments also appear in
**Manage Python environments**. Cancelling an installation can leave a
partial environment; retry **Update / repair** to finish it. A cancelled or
failed installation is never reported as successful.

**Latest** checks PyPI every time and installs that exact version with upgrade
enabled, including when an older version is already installed. It never
substitutes an older MCP release to accommodate an unsupported Python. If the
version check cannot reach PyPI, installation stops without changing the
environment. Choose an explicit version from the dropdown for reproducible setups; the
version field cannot be edited. Opening it loads releases automatically. APM caches this list for
15 minutes; **Latest** still performs a fresh check before installation.

The Python dropdowns update for the selected product, source, and release.
APM checks the actual interpreter version and architecture against the exact
release requirements. Unsupported discovered Python versions are hidden from the normal dropdown.
Virtual environments remain visible with compatibility information. A compatible Python is selected for a new dedicated environment;
an existing environment is never silently replaced by another selection.
Late responses from an earlier selection cannot change the current choices.
Installation always checks the requirements again before making changes.

Returning to this tab reuses the choices already discovered by the other APM
tabs. **Refresh** scans in the background without blocking navigation. Use
**Other locations and details** to add a Python executable or an environment
outside the configured search folders, or to inspect the full environment path.
Manually added Python interpreters remain visible even outside the documented
product range. For those explicit selections, the release's own ``Requires-Python``
metadata and the 64-bit requirement still apply. APM never silently replaces
an explicit interpreter with another Python. A release that requires Python
3.12 cannot be installed on Python 3.9 through this option.

Existing incompatible environments are preserved; create a supported
environment in **Create virtual environments** and select it here.

On Linux, uninstalling the manager offers separate options to remove settings
and managed environments. Removing settings preserves MCP environments;
removing managed environments includes the product environments. Existing
custom environments outside the manager's configured locations are preserved.

For an offline installation, select **Offline wheelhouse** under **Install from**
and provide a directory of
wheels or a wheelhouse ZIP. Include the chosen MCP package and all dependencies,
including build dependencies if distributing source packages. Wheels must
match the target operating system, architecture, and Python version. The
manager passes ``--no-index`` to pip and does not query PyPI.
Git sources are unavailable in offline mode. ZIP extraction
rejects traversal paths and symbolic links.
The version dropdown automatically lists versions found in the selected folder
or ZIP. In offline mode, **Latest** means the newest stable MCP wheel in the selected
wheelhouse; the manager does not contact PyPI.

Connect a coding agent
----------------------

For one local coding agent, use **stdio**. The agent starts the installed
MCP console script directly. The manager does not need to remain open.
For shared HTTP access, use **Start HTTP server** under **Server settings**.
The manager binds to ``127.0.0.1`` and waits for an MCP initialize response
before reporting readiness. Its servers stop when the manager exits.

The **Local HTTP server** section separates the endpoint and server status from
the optional **Solver connection** section. Solver host and port appear only
when connecting on startup is enabled. Less common options are under
**Advanced launch settings**, with separate sections for product options,
additional arguments, and environment variables. Server actions stay visible
when scrolling or viewing the activity log. PyLumerical instead shows its
automatic stdio connection and a shortcut to **Coding agents**.

HTTP transport ports are distinct from Ansys solver connection ports.
PyAEDT, PyMechanical, and PyMAPDL expose solver connection fields. PyAEDT also
offers graphical mode, context tools, and dynamic tool discovery. Additional
product options are read from the installed release when expanding advanced
settings. Use **Add an option** to select a flag, a choice, or a value. Options
include their help text and defaults in tooltips. APM reads the argument parser
in a separate process and exits before starting a server or connecting a solver.
Unsupported saved options must be removed before launching. If a future release
changes its parser, consult **Documentation** and use **Custom arguments**.
Expert options can also be entered as a JSON string array, for example:

.. code-block:: json

   ["--transport-mode", "mtls", "--certs-dir", "C:/Ansys certificates"]

Environment overrides are a JSON object of string names and values. They are
passed to manager-owned HTTP processes and included in stdio client profiles.
Settings, profiles and backups store these values as plain text.

Under **Coding agents**, select VS Code, the Copilot command-line tool, Claude Desktop,
Cursor, Codex, or OpenCode. Review the destination path. VS Code defaults to
the current Copilot harness and its personal ``~/.copilot/mcp-config.json``,
respecting ``COPILOT_HOME``. **Choose workspace** selects a project
``.mcp.json`` instead. For older installations, choose **Local harness (legacy)**
to use the VS Code user-profile ``mcp.json`` or a workspace ``.vscode/mcp.json``.
The current format uses ``mcpServers``; the legacy format uses ``servers``.
See the `VS Code MCP configuration reference <https://code.visualstudio.com/docs/agents/reference/mcp-configuration>`_.
Choose **Automatic (stdio)** for an agent-managed process or **Shared HTTP server**
for an already running server. Claude Desktop's local
configuration supports stdio here; PyLumerical offers stdio only.

Click **Review configuration**, review the complete merged document, then click
**Save reviewed configuration**. The same button guides both steps; editing
any connection setting requires a new review. The review section opens when a preview is available;
the actions stay visible below the page. The manager preserves unrelated entries,
backs up existing files, and replaces the destination atomically. Existing
product entries are updated under their current names, including recognized
aliases such as ``pymechanical`` and ``pymechanical-mcp``. Matching aliases
are consolidated, and repeated saves do not add duplicate servers. Tool
restrictions, timeouts, unrelated environment variables, and other preferences
are retained. If several custom entries launch the same product, APM refuses
to guess which one to replace. It refuses
to overwrite a file changed after preview. Codex TOML comments are preserved.
JSON files must be strict JSON: files containing comments or duplicate keys
are rejected without modification. Merge the preview manually when a client
uses JSON with comments. Reload or restart the coding agent after saving.
Codex profiles include a 60-second startup timeout for MCP imports on a cold
environment. The command and argument fields follow the
`official Codex MCP configuration <https://developers.openai.com/codex/mcp/>`_.

New OpenCode profiles follow the current V2 ``mcp.servers`` layout. Existing
V1 files with server entries directly under ``mcp`` keep their layout; mixed
V1/V2 files require manual migration. These formats follow the
`OpenCode MCP reference <https://opencode.ai/docs/mcp-servers/>`_.

The generated profiles reference the selected environment. Regenerate them
after changing the environment or connection settings. An HTTP profile uses
the selected HTTP port; start that server before connecting the client.

Architecture and validation
---------------------------

The existing ``main`` module composes the Python installation, environment
creation and package-management tabs. ``find_python`` discovers registry,
Ansys, conda, and configured virtual environments. Platform-specific installers
and terminal launchers remain in ``windows_functions`` and ``linux_functions``.
``configure_json`` owns the existing environment search settings; updates and
PyInstaller/NSIS/Linux packaging remain independent of MCP package installation.

The MCP integration uses a separate native PySide6 tab. The
`PyAEDT desktop app <https://github.com/ansys/pyaedt-mcp/tree/main/desktop_app>`_
informed its installation, server controls, advanced settings, logs, and
profile workflows. Its Flet UI, Windows embedded runtime, tray integration,
and product-specific executable detection are not dependencies of this Qt app.

``mcp_catalog`` defines package and command-line differences. ``mcp_backend`` handles
installation plans, metadata, settings, and wheelhouses. ``mcp_process`` owns
asynchronous subprocesses and HTTP readiness. ``mcp_owned_process`` contains
their descendants in Windows jobs or Unix process sessions, so persistent
Python workers stop with the server. ``mcp_profiles`` merges client
configurations, and ``mcp_tab`` connects these services to Qt. Adding a product
requires verifying its published package, Python requirements, launch command,
transports and client interoperability before extending the catalog and tests.
``mcp_launch`` reads installed launch options without starting a server.
``mcp_releases`` resolves exact releases and validates interpreter versions
against their metadata before installation.

The command contracts were cross-checked against the official
`PyAEDT <https://aedt-mcp.docs.pyansys.com/version/stable/getting_started/installation.html>`_,
`PyMechanical <https://mechanical-mcp.docs.pyansys.com/version/stable/getting_started/installation.html>`_,
`PyFluent <https://fluent-mcp.docs.pyansys.com/version/stable/getting_started/ide_configuration.html>`_,
`PyMAPDL <https://mapdl-mcp.docs.pyansys.com/version/stable/getting_started/ide_configuration.html>`_,
`PyLumerical <https://lumerical-mcp.docs.pyansys.com/version/stable/getting_started/installation.html>`_,
and `PyCFX <https://cfx-mcp.docs.pyansys.com/version/stable/getting_started/ide_configuration.html>`_
guides. Stable documentation can lag a release: for example, Fluent 0.9 installs
its solver backend as a dependency, although the older stable installation
guide still lists a separate extra. Published package metadata determines the
actual installation requirements.

The automated suite exercises installation using a small offline wheel,
profile preservation, product-specific arguments, settings, real subprocesses,
cancellation, and protocol readiness. CI runs on Windows and Ubuntu 22.04/24.04,
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
