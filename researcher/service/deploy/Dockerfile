# Runtime/dependency image only. Supply a reviewed digest; there is no default.
ARG BASE_IMAGE
FROM ${BASE_IMAGE}
ARG BASE_IMAGE
ARG INSTALL_MCP=0

RUN python -c 'import re,sys; sys.exit(0 if re.fullmatch(r"python:3\.12\.[0-9]+-slim-bookworm@sha256:[0-9a-f]{64}", sys.argv[1]) else "A reviewed Python 3.12 slim-bookworm patch tag and sha256 digest are required")' "$BASE_IMAGE"
RUN python -c 'import sys; sys.exit(0 if sys.argv[1] in ("0", "1") else "INSTALL_MCP must be 0 or 1")' "$INSTALL_MCP"
RUN apt-get update \
    && apt-get install --yes --no-install-recommends ca-certificates git \
    && apt-get clean \
    && groupadd --gid 10001 context-research \
    && useradd --uid 10001 --gid 10001 --no-create-home --shell /usr/sbin/nologin context-research

COPY requirements-dev.txt /opt/context-research/requirements-dev.txt
COPY researcher/service/requirements-mcp.txt /opt/context-research/requirements-mcp.txt
COPY researcher/service/deploy/requirements-codex-linux.txt /opt/context-research/requirements-codex-linux.txt
RUN python -m venv /opt/context-research/venv \
    && if [ "$INSTALL_MCP" = "1" ]; then \
        /opt/context-research/venv/bin/python -m pip install --no-cache-dir --require-hashes --only-binary=:all: -r /opt/context-research/requirements-dev.txt -r /opt/context-research/requirements-mcp.txt; \
       else \
        /opt/context-research/venv/bin/python -m pip install --no-cache-dir --require-hashes --only-binary=:all: -r /opt/context-research/requirements-dev.txt; \
       fi \
    && /opt/context-research/venv/bin/python -m pip check \
    && git config --system --add safe.directory /repo
# Mandatory SDK runtime, isolated from optional MCP dependencies. This lock has
# reviewed wheels for both existing Linux image targets, not arbitrary ABIs.
RUN python -c 'import platform,sys; sys.exit(0 if sys.platform == "linux" and sys.version_info[:2] == (3,12) and platform.machine() in ("aarch64","x86_64") else "CODEX_SDK_LOCK_TARGET_UNSUPPORTED")' \
    && python -m venv /opt/context-research/codex-venv \
    && /opt/context-research/codex-venv/bin/python -m pip install --no-cache-dir --require-hashes --only-binary=:all: -r /opt/context-research/requirements-codex-linux.txt \
    && /opt/context-research/codex-venv/bin/python -m pip check \
    && /opt/context-research/codex-venv/bin/python -c 'from importlib.metadata import version; assert version("openai-codex") == version("openai-codex-cli-bin") == "0.159.0"'
COPY researcher/service/deploy/launch.py /opt/context-research/launch.py
RUN mkdir /repo /state /config \
    && chown 10001:10001 /state \
    && chmod 0700 /state

ENV PATH=/opt/context-research/venv/bin:/usr/local/bin:/usr/bin:/bin \
    PYTHONPATH=/repo \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONUTF8=1 \
    RESEARCH_RELEASE_DIR=/repo \
    RESEARCH_DEPENDENCY_LOCK=/opt/context-research/requirements-dev.txt \
    RESEARCH_INSTALL_MCP=${INSTALL_MCP} \
    RESEARCH_MCP_DEPENDENCY_LOCK=/opt/context-research/requirements-mcp.txt \
    RESEARCH_CODEX_DEPENDENCY_LOCK=/opt/context-research/requirements-codex-linux.txt \
    RESEARCH_CODEX_PYTHON=/opt/context-research/codex-venv/bin/python
WORKDIR /repo
USER 10001:10001
ENTRYPOINT ["/opt/context-research/venv/bin/python", "-B", "/opt/context-research/launch.py"]
CMD ["status", "--config", "/config/service.json", "--state", "/state", "--repo", "/repo"]
