#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOCAL_BIN="${HOME}/.local/bin"

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "missing command: $1" >&2
    exit 1
  fi
}

install_uv() {
  if command -v uv >/dev/null 2>&1; then
    return
  fi
  echo "[setup] installing uv"
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="${LOCAL_BIN}:${PATH}"
}

github_latest_asset_url() {
  local repo="$1"
  local pattern="$2"
  curl -fsSL "https://api.github.com/repos/${repo}/releases/latest" \
    | grep -E '"browser_download_url":' \
    | sed -E 's/.*"browser_download_url": "([^"]+)".*/\1/' \
    | grep -E "${pattern}" \
    | head -n 1
}

install_quarto() {
  if command -v quarto >/dev/null 2>&1; then
    return
  fi
  echo "[setup] installing Quarto CLI"
  require_command curl
  require_command grep
  require_command sed

  local deb_url
  deb_url="$(github_latest_asset_url "quarto-dev/quarto-cli" 'linux-amd64[.]deb$')"
  if [[ -z "${deb_url}" ]]; then
    echo "could not find the latest Quarto linux-amd64 .deb release asset" >&2
    exit 1
  fi

  local deb_path
  deb_path="$(mktemp --suffix=.deb)"
  curl -fL "${deb_url}" -o "${deb_path}"
  sudo apt-get update
  sudo apt-get install -y "${deb_path}"
  rm -f "${deb_path}"
}

install_typst() {
  if command -v typst >/dev/null 2>&1; then
    return
  fi
  echo "[setup] installing Typst CLI"
  require_command curl
  require_command tar
  require_command grep
  require_command sed

  mkdir -p "${LOCAL_BIN}"

  local archive_url
  archive_url="$(github_latest_asset_url "typst/typst" 'x86_64-unknown-linux-musl[.]tar[.]xz$')"
  if [[ -z "${archive_url}" ]]; then
    echo "could not find the latest Typst Linux release asset" >&2
    exit 1
  fi

  local temp_dir
  temp_dir="$(mktemp -d)"
  curl -fL "${archive_url}" -o "${temp_dir}/typst.tar.xz"
  tar -xf "${temp_dir}/typst.tar.xz" -C "${temp_dir}"
  find "${temp_dir}" -type f -name typst -perm -111 -exec cp {} "${LOCAL_BIN}/typst" \; -quit
  chmod +x "${LOCAL_BIN}/typst"
  rm -rf "${temp_dir}"
  export PATH="${LOCAL_BIN}:${PATH}"
}

prepare_env_file() {
  if [[ ! -f "${ROOT_DIR}/demos/.env" ]]; then
    cp "${ROOT_DIR}/demos/.env.example" "${ROOT_DIR}/demos/.env"
    echo "[setup] created demos/.env from demos/.env.example"
    echo "[setup] edit demos/.env and set API_KEY before running LLM demos"
  fi
}

verify_tools() {
  echo "[setup] versions"
  uv --version
  uv run python --version
  quarto --version
  typst --version
}

main() {
  if [[ ! -f /etc/debian_version ]]; then
    echo "This script targets Debian/Ubuntu-style Linux with apt. Install Quarto manually on other distributions." >&2
    exit 1
  fi

  require_command curl
  install_uv
  install_quarto
  install_typst

  cd "${ROOT_DIR}"
  uv sync
  prepare_env_file
  verify_tools

  echo "[setup] done"
  echo "[setup] next: edit demos/.env, then run demos/03-documeta-completion and demos/04-build-writing"
}

main "$@"
