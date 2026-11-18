# Reproduce the MCP Qt/offline-install tests on the Linux packaging targets.
# docker build --build-arg DISTRO=ubuntu:22.04 -f scripts/mcp-validation.Dockerfile -t apm-mcp-test .
# docker run --rm apm-mcp-test
ARG DISTRO=ubuntu:24.04
FROM ghcr.io/astral-sh/uv:0.10.4 AS uv
FROM ${DISTRO}
COPY --from=uv /uv /usr/local/bin/uv
RUN if [ -f /etc/fedora-release ] && grep -q 'release 40 ' /etc/fedora-release; then \
      sed -i 's|^metalink=|#metalink=|; s|^#baseurl=http://download.example/pub/fedora/linux/|baseurl=https://archives.fedoraproject.org/pub/archive/fedora/linux/|' \
        /etc/yum.repos.d/fedora.repo /etc/yum.repos.d/fedora-updates.repo; \
    fi
RUN if command -v apt-get >/dev/null; then \
      apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates libegl1 libopengl0 libxkbcommon0 libdbus-1-3 \
        libfontconfig1 libglib2.0-0 libxrender1 libxext6 libx11-6; \
    else \
      dnf install -y ca-certificates mesa-libEGL mesa-libGL libxkbcommon \
        dbus-libs fontconfig glib2 libXrender libXext libX11; \
    fi
RUN if command -v apt-get >/dev/null; then apt-get install -y --no-install-recommends libgl1; fi
WORKDIR /workspace
COPY pyproject.toml README.rst LICENSE ./
COPY src ./src
COPY tests ./tests
COPY scripts/validate_mcp.py ./scripts/validate_mcp.py
ENV QT_QPA_PLATFORM=offscreen UV_LINK_MODE=copy
RUN uv venv --python 3.13 /opt/apm && uv pip install --python /opt/apm/bin/python -e '.[tests]'
CMD ["/opt/apm/bin/python", "-m", "pytest", "tests/test_mcp_backend.py", "tests/test_mcp_releases.py", "tests/test_mcp_compatibility.py", "tests/test_mcp_profiles.py", "tests/test_mcp_process.py", "tests/test_mcp_tab.py", "-q", "--tb=short"]
