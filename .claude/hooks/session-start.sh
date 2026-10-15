#!/bin/bash
# Installs the REA reverse-engineering toolchain (Ghidra + JADX MCP bridge) for cloud sessions.
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

GHIDRA_VERSION=12.1.4
GHIDRA_ZIP=ghidra_${GHIDRA_VERSION}_PUBLIC_20260921.zip
GHIDRA_URL=https://github.com/NationalSecurityAgency/ghidra/releases/download/Ghidra_${GHIDRA_VERSION}_build/${GHIDRA_ZIP}
GHIDRA_SHA256=ddac49f903da9d5bac833e5cc79395098b9c33cfd3279be5f31bd00387d2d4db
GHIDRA_DIR=/opt/ghidra/ghidra_${GHIDRA_VERSION}_PUBLIC

JADX_JAR=/opt/jadx/jadx-headless-mcp-0.7.1-all.jar
JADX_URL=https://github.com/1013503897/jadx-headless-mcp/releases/download/v0.7.1/jadx-headless-mcp-0.7.1-all.jar
JADX_SHA256=6e5eacf500b64292bfb73c49797c1958f6ee44646e43e868039ae7feb573ff75

CURL=(curl -fsSL --retry 4 --retry-delay 2)
[ -f /root/.ccr/ca-bundle.crt ] && CURL+=(--cacert /root/.ccr/ca-bundle.crt)

# JDK 21 (Ghidra and JADX both need a full JDK)
if ! command -v javac >/dev/null 2>&1 || ! javac -version 2>&1 | grep -qE 'javac (2[1-9]|[3-9][0-9])'; then
  apt-get update -qq
  DEBIAN_FRONTEND=noninteractive apt-get install -y -qq openjdk-21-jdk-headless >/dev/null
fi

# Ghidra
if [ ! -x "$GHIDRA_DIR/support/analyzeHeadless" ]; then
  tmp=$(mktemp -d)
  "${CURL[@]}" -o "$tmp/$GHIDRA_ZIP" "$GHIDRA_URL"
  echo "$GHIDRA_SHA256  $tmp/$GHIDRA_ZIP" | sha256sum -c --quiet
  mkdir -p /opt/ghidra
  unzip -q "$tmp/$GHIDRA_ZIP" -d /opt/ghidra
  rm -rf "$tmp"
fi

# JADX headless MCP bridge
if ! echo "$JADX_SHA256  $JADX_JAR" | sha256sum -c --quiet >/dev/null 2>&1; then
  mkdir -p /opt/jadx
  "${CURL[@]}" -o "$JADX_JAR.tmp" "$JADX_URL"
  echo "$JADX_SHA256  $JADX_JAR.tmp" | sha256sum -c --quiet
  mv "$JADX_JAR.tmp" "$JADX_JAR"
fi

# Pre-fetch the pinned REA package so the MCP server starts quickly
npx -y rea-agents@6.5.0 --help >/dev/null 2>&1 || true

if [ -n "${CLAUDE_ENV_FILE:-}" ]; then
  {
    echo "export GHIDRA_INSTALL_DIR=$GHIDRA_DIR"
    echo "export REA_JADX_MCP_JAR=$JADX_JAR"
  } >> "$CLAUDE_ENV_FILE"
fi
