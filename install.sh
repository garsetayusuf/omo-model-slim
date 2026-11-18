#!/bin/sh
# OMO Manager installer. No sudo. Installs only into the user's home directory.
# Usage: install.sh [install|verify|uninstall]
# Testing overrides: OMO_BASE_URL, OMO_VERSION, OMO_NO_VERIFY=1, PREFIX
set -eu

REPO=${OMO_REPO:-garsetayusuf/omo-model-slim}
VERSION=${OMO_VERSION:-v1.0.1}
PREFIX=${PREFIX:-$HOME/.local}
BIN=$PREFIX/bin
APP=$PREFIX/share/omo-model-slim
ACTION=${1:-install}
TMP=

cleanup() { if [ -n "$TMP" ]; then rm -rf "$TMP"; fi; return 0; }
trap cleanup EXIT HUP INT TERM

info() { printf '  %s\n' "$*"; }
fail() { printf 'error: %s\n' "$*" >&2; exit 1; }

detect_platform() {
    case $(uname -s) in
        Darwin) printf 'macOS\n' ;;
        Linux)
            if grep -qi microsoft /proc/version 2>/dev/null || uname -r | grep -qi microsoft; then
                printf 'WSL\n'
            else
                printf 'Linux\n'
            fi
            ;;
        *) printf 'Unsupported\n' ;;
    esac
}

check_python() {
    command -v python3 >/dev/null 2>&1 || fail 'python3 is required (3.10 or newer)'
    python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)' \
        || fail "Python 3.10+ is required; found $(python3 --version 2>&1)"
}

download() {
    url=$1
    destination=$2
    if ! curl -fsSL --retry 3 --connect-timeout 10 --max-time 120 "$url" -o "$destination"; then
        fail "download failed: $url (check your network connection and the version $VERSION)"
    fi
    [ -s "$destination" ] || fail "empty download: $url"
}

paths() {
    RAW="https://raw.githubusercontent.com/$REPO/$VERSION"
    RELEASE="https://github.com/$REPO/releases/download/$VERSION"
    if [ -n "${OMO_BASE_URL:-}" ]; then
        RAW=${OMO_BASE_URL%/}
        RELEASE=${OMO_BASE_URL%/}
    fi
}

verify_manifest() {
    if [ "${OMO_NO_VERIFY:-0}" = 1 ]; then
        info 'checksum verification disabled (test mode)'
        return 0
    fi
    if command -v shasum >/dev/null 2>&1; then
        CHECKER='shasum -a 256 -c'
    else
        CHECKER='sha256sum -c'
    fi
    [ -n "${CHECKER:-}" ] || fail 'no SHA-256 checker found (shasum or sha256sum)'
    download "$RELEASE/SHA256SUMS" "$TMP/SHA256SUMS" || return 1
    # Check only the artifacts this installer uses.
    grep -E ' (omo-model-slim|omo_model_slim\.py|omo_tui\.py|opencode_manage\.py)$' "$TMP/SHA256SUMS" > "$TMP/check.txt" \
        || fail "SHA256SUMS is missing the expected artifacts"
    (cd "$TMP" && $CHECKER check.txt) || fail 'checksum verification failed; refusing to install'
    info 'artifact checksums verified'
}

do_install() {
    PLATFORM=$(detect_platform)
    [ "$PLATFORM" != Unsupported ] || fail 'unsupported operating system (need macOS, Linux, or WSL)'
    info "platform: $PLATFORM"
    check_python
    command -v curl >/dev/null 2>&1 || fail 'curl is required'
    paths

    TMP=$(mktemp -d "${TMPDIR:-/tmp}/omo-install.XXXXXX")
    info "installing version $VERSION"

    download "$RAW/omo-model-slim" "$TMP/omo-model-slim"
    download "$RAW/omo_model_slim.py" "$TMP/omo_model_slim.py"
    download "$RAW/omo_tui.py" "$TMP/omo_tui.py"
    download "$RAW/opencode_manage.py" "$TMP/opencode_manage.py"
    download "$RAW/install.sh" "$TMP/install.sh"
    verify_manifest

    python3 -m py_compile "$TMP/omo-model-slim" "$TMP/omo_model_slim.py" \
        "$TMP/omo_tui.py" "$TMP/opencode_manage.py" || fail 'downloaded files failed syntax validation'
    chmod 755 "$TMP/omo-model-slim"

    mkdir -p "$BIN" "$APP"
    ROLLBACK=
    if [ -f "$APP/omo-model-slim" ]; then
        ROLLBACK=$APP.rollback.$(date +%Y%m%d%H%M%S)
        cp -R "$APP" "$ROLLBACK" || fail 'could not create rollback copy'
        info "previous installation saved to $ROLLBACK"
    fi

    if ! (
        install -m 644 "$TMP/omo_model_slim.py" "$APP/omo_model_slim.py" &&
        install -m 644 "$TMP/omo_tui.py" "$APP/omo_tui.py" &&
        install -m 644 "$TMP/opencode_manage.py" "$APP/opencode_manage.py" &&
        install -m 755 "$TMP/omo-model-slim" "$APP/omo-model-slim" &&
        install -m 644 "$TMP/install.sh" "$APP/install.sh" &&
        rm -rf "$APP/__pycache__" &&
        printf '#!/bin/sh\nexec python3 "%s/omo-model-slim" "$@"\n' "$APP" > "$TMP/wrapper" &&
        install -m 755 "$TMP/wrapper" "$BIN/omo-model-slim"
    ); then
        if [ -n "$ROLLBACK" ]; then
            rm -rf "$APP"
            mv "$ROLLBACK" "$APP"
            info 'restored previous installation after failure'
        fi
        fail 'installation failed; no partial installation left behind'
    fi

    "$BIN/omo-model-slim" --version || fail 'installed executable failed verification'
    info "installed: $BIN/omo-model-slim"
    case ":$PATH:" in
        *":$BIN:"*) ;;
        *) info "add this to your shell profile to use the command:"
           info "  export PATH=\"$BIN:\$PATH\"" ;;
    esac
    info 'the existing omo-model executable was not modified'
    if [ -n "$ROLLBACK" ]; then
        info "rollback: rm -rf \"$APP\" && mv \"$ROLLBACK\" \"$APP\""
    fi
    return 0
}

do_verify() {
    [ -x "$BIN/omo-model-slim" ] || fail "not installed at $BIN/omo-model-slim"
    "$BIN/omo-model-slim" --version
    for file in omo-model-slim omo_model_slim.py omo_tui.py opencode_manage.py install.sh; do
        [ -f "$APP/$file" ] || fail "missing installed file: $APP/$file"
    done
    info 'installation verified'
}

do_uninstall() {
    rm -f "$BIN/omo-model-slim"
    rm -rf "$APP"
    info 'OMO Manager removed; configuration and backups were left untouched'
    info 'remove any PATH line you added for ~/.local/bin if it is no longer needed'
}

case "$ACTION" in
    install) do_install ;;
    verify) do_verify ;;
    uninstall) do_uninstall ;;
    *) fail "unknown action: $ACTION (use install, verify, or uninstall)" ;;
esac
