#!/bin/sh
# OMO Manager installer. No sudo. Installs only into the user's home directory.
# Usage: install.sh [install|upgrade|verify|uninstall]
# Testing overrides: OMO_BASE_URL, OMO_VERSION, OMO_NO_VERIFY=1, PREFIX, OMO_COLOR
set -eu

REPO=${OMO_REPO:-garsetayusuf/omo-model-slim}
VERSION=${OMO_VERSION:-v1.0.6}
PREFIX=${PREFIX:-$HOME/.local}
BIN=$PREFIX/bin
APP=$PREFIX/share/omo-model-slim
ACTION=${1:-install}
TMP=

cleanup() { if [ -n "$TMP" ]; then rm -rf "$TMP"; fi; return 0; }
trap cleanup EXIT HUP INT TERM

# Color is opt-out with NO_COLOR/OMO_COLOR=0 and off for pipes and dumb terminals.
# OMO_COLOR=1 forces it on (useful for previewing the output in a pipeline).
USE_COLOR=0
if [ "${OMO_COLOR:-auto}" = 1 ]; then
    USE_COLOR=1
elif [ "${OMO_COLOR:-auto}" = auto ] && [ -t 1 ] && [ -z "${NO_COLOR:-}" ] && [ "${TERM:-dumb}" != dumb ]; then
    USE_COLOR=1
fi
if [ "$USE_COLOR" = 1 ]; then
    C_RESET='\033[0m'
    C_BOLD='\033[1m'
    C_DIM='\033[2m'
    C_OK='\033[32m'
    C_ERR='\033[31m'
    C_ACCENT='\033[38;5;141m'
    I_OK='✓'
    I_ERR='✗'
    I_STEP='▸'
    SEP='·'
else
    C_RESET=''
    C_BOLD=''
    C_DIM=''
    C_OK=''
    C_ERR=''
    C_ACCENT=''
    I_OK='OK'
    I_ERR='ERROR'
    I_STEP='*'
    SEP='-'
fi

header() {
    printf '%b\n\n' "${C_BOLD}${C_ACCENT}OMO Manager${C_RESET} ${C_DIM}${SEP}${C_DIM} ${VERSION}${C_RESET}"
    printf '  %s  %s\n' "$I_STEP" "$1"
}

STEP=0
TOTAL=5
step() {
    STEP=$((STEP + 1))
    printf '  %s  %d/%d  %-38s' "$I_STEP" "$STEP" "$TOTAL" "$1"
}
done_step() {
    step "$1"
    if [ -n "${2:-}" ]; then
        printf '%b\n' "${C_OK}${I_OK}${C_RESET} ${2}${C_RESET}"
    else
        printf '%b\n' "${C_OK}${I_OK}${C_RESET}"
    fi
}

summary() {
    title=$1
    shift
    printf '\n  %b\n' "${C_BOLD}${C_OK}${I_OK}${C_RESET} ${title}${C_RESET}"
    for line in "$@"; do printf '    %s\n' "$line"; done
}

fail() {
    printf '\n  %b\n' "${C_ERR}${I_ERR}${C_RESET} ${*}${C_RESET}" >&2
    printf '    No changes were made.\n' >&2
    exit 1
}

info() { printf '    %s\n' "$*"; }
verbose() { [ "${OMO_VERBOSE:-0}" = 1 ] && info "$*" || true; }

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
    python3 --version 2>&1
}

download() {
    url=$1
    destination=$2
    if ! curl -fsSL --retry 3 --connect-timeout 10 --max-time 120 "$url" -o "$destination"; then
        fail "download failed for $destination (check network access and version $VERSION)"
    fi
    [ -s "$destination" ] || fail "empty download for $destination"
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
        verbose 'checksum verification disabled (test mode)'
        return 0
    fi
    if command -v shasum >/dev/null 2>&1; then
        CHECKER='shasum -a 256 -c'
    else
        CHECKER='sha256sum -c'
    fi
    download "$RELEASE/SHA256SUMS" "$TMP/SHA256SUMS"
    grep -E ' (omo-model-slim|omo_model_slim\.py|omo_tui\.py|opencode_manage\.py)$' "$TMP/SHA256SUMS" > "$TMP/check.txt" \
        || fail 'SHA256SUMS is missing the expected artifacts'
    if ! (cd "$TMP" && $CHECKER check.txt > /dev/null 2>&1); then
        fail 'checksum verification failed; refusing to install'
    fi
}

normalize_version() { printf '%s' "$1" | sed 's/^v//'; }

installed_version() {
    [ -x "$BIN/omo-model-slim" ] || return 0
    "$BIN/omo-model-slim" --version 2>/dev/null | awk '{print $NF}' | sed 's/^v//'
}

version_gt() {
    awk -v a="$1" -v b="$2" 'BEGIN {
        na = split(a, x, "."); nb = split(b, y, "."); n = (na > nb ? na : nb)
        for (i = 1; i <= n; i++) {
            p = x[i] + 0; q = y[i] + 0
            if (p > q) exit 0
            if (p < q) exit 1
        }
        exit 1
    }'
}

do_install() {
    TARGET_VERSION=$(normalize_version "$VERSION")
    INSTALLED_VERSION=$(installed_version)
    ACTION_LABEL='Install'
    if [ -n "$INSTALLED_VERSION" ]; then
        if [ "$INSTALLED_VERSION" = "$TARGET_VERSION" ]; then
            if [ "${OMO_FORCE:-0}" != 1 ]; then
                header 'Update check'
                TOTAL=2
                done_step 'Installed version' "$INSTALLED_VERSION"
                done_step 'Release version' "$TARGET_VERSION"
                summary 'Already up to date' \
                    "Version   $VERSION" \
                    'Next      omo-model-slim' \
                    'Force     OMO_FORCE=1 omo-model-slim upgrade'
                return 0
            fi
            ACTION_LABEL='Reinstall'
        elif version_gt "$TARGET_VERSION" "$INSTALLED_VERSION"; then
            ACTION_LABEL='Upgrade'
        fi
    fi
    header "$ACTION_LABEL"

    PLATFORM=$(detect_platform)
    [ "$PLATFORM" != Unsupported ] || fail 'unsupported operating system (need macOS, Linux, or WSL)'
    done_step 'Platform detected' "$PLATFORM"

    PYTHON_VERSION=$(check_python)
    done_step 'Python 3.10+' "$PYTHON_VERSION"
    command -v curl >/dev/null 2>&1 || fail 'curl is required'
    paths

    TMP=$(mktemp -d "${TMPDIR:-/tmp}/omo-install.XXXXXX")

    download "$RAW/omo-model-slim" "$TMP/omo-model-slim"
    download "$RAW/omo_model_slim.py" "$TMP/omo_model_slim.py"
    download "$RAW/omo_tui.py" "$TMP/omo_tui.py"
    download "$RAW/opencode_manage.py" "$TMP/opencode_manage.py"
    download "$RAW/install.sh" "$TMP/install.sh"
    verify_manifest
    done_step 'Download & checksums' '4 files verified'

    python3 -m py_compile "$TMP/omo-model-slim" "$TMP/omo_model_slim.py" \
        "$TMP/omo_tui.py" "$TMP/opencode_manage.py" || fail 'downloaded files failed syntax validation'
    chmod 755 "$TMP/omo-model-slim"

    mkdir -p "$BIN" "$APP"
    ROLLBACK=
    if [ -f "$APP/omo-model-slim" ]; then
        ROLLBACK=$APP.rollback.$(date +%Y%m%d%H%M%S)
        cp -R "$APP" "$ROLLBACK" || fail 'could not create a rollback copy'
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
            printf '\n  %s  Restored the previous installation after failure.\n' "$I_OK" >&2
        fi
        fail 'installation failed; no partial installation left behind'
    fi
    done_step 'Install application files'

    INSTALLED_VERSION=$("$BIN/omo-model-slim" --version) || fail 'installed executable failed verification'
    done_step 'Verify executable' "$INSTALLED_VERSION"

    NEXT='omo-model-slim'
    case ":$PATH:" in
        *":$BIN:"*) ;;
        *) NEXT="export PATH=\"$BIN:\$PATH\"  # then omo-model-slim" ;;
    esac
    if [ -n "$ROLLBACK" ]; then
        summary "$ACTION_LABEL complete" "Command   omo-model-slim" "Location  $BIN/omo-model-slim" \
            "Rollback  $ROLLBACK" "Next      $NEXT"
    else
        summary "$ACTION_LABEL complete" "Command   omo-model-slim" "Location  $BIN/omo-model-slim" "Next      $NEXT"
    fi
    return 0
}

do_verify() {
    header 'Verify'
    TOTAL=3
    [ -x "$BIN/omo-model-slim" ] || fail "not installed at $BIN/omo-model-slim"
    done_step 'Executable' "$BIN/omo-model-slim"
    COUNT=0
    for file in omo-model-slim omo_model_slim.py omo_tui.py opencode_manage.py install.sh; do
        [ -f "$APP/$file" ] || fail "missing installed file: $APP/$file"
        COUNT=$((COUNT + 1))
    done
    done_step 'Application files' "$COUNT/5 present"
    INSTALLED_VERSION=$("$BIN/omo-model-slim" --version) || fail 'installed executable did not run'
    done_step 'Installed version' "$INSTALLED_VERSION"
    summary 'Installation is healthy' "Location  $BIN/omo-model-slim"
}

cleanup_path_lines() {
    # Dependency-aware: if the bin directory still holds other tools, its PATH
    # entry is probably needed by something else, so leave every profile alone.
    REMAINING=$(ls -A "$BIN" 2>/dev/null | wc -l | tr -d ' ')
    if [ "${REMAINING:-0}" -gt 0 ]; then
        printf 'skipped: %s still contains other executables\n' "$BIN"
        return 0
    fi
    USE_DEFAULT=0
    if [ "$BIN" = "$HOME/.local/bin" ]; then USE_DEFAULT=1; fi

    REMOVED=0
    for profile in "$HOME/.zshrc" "$HOME/.zprofile" "$HOME/.bashrc" "$HOME/.bash_profile" "$HOME/.profile"; do
        [ -f "$profile" ] || continue
        TMP_PROFILE="$profile.omo-tmp.$$"
        if ! awk -v absolute="$BIN" -v use_default="$USE_DEFAULT" '
            BEGIN { DROP = sprintf("%c", 1) }
            function is_omo(seg) {
                if (seg == absolute) return 1
                if (use_default == 1 && (seg == "$HOME/.local/bin" || seg == "~/.local/bin")) return 1
                return 0
            }
            function is_path(seg) { return seg == "$PATH" || seg == "${PATH}" }
            function cleanup(line,    prefix, value, quote, parts, n, i, seg, out, changed, added) {
                if (!match(line, /^[[:space:]]*(export[[:space:]]+)?PATH=/)) return line
                prefix = substr(line, 1, RLENGTH)
                value = substr(line, RLENGTH + 1)
                quote = ""
                if (length(value) >= 2 && substr(value, 1, 1) == "\"" && substr(value, length(value), 1) == "\"") {
                    quote = "\""; value = substr(value, 2, length(value) - 2)
                } else if (length(value) >= 2 && substr(value, 1, 1) == "\047" && substr(value, length(value), 1) == "\047") {
                    quote = "\047"; value = substr(value, 2, length(value) - 2)
                }
                n = split(value, parts, ":")
                out = ""; changed = 0; added = 0; first = 1
                for (i = 1; i <= n; i++) {
                    seg = parts[i]
                    if (is_omo(seg)) { changed = 1; continue }
                    if (!first) out = out ":"
                    out = out seg
                    first = 0
                    if (seg != "" && !is_path(seg)) added = 1
                }
                if (!changed) return line
                if (!added) return DROP
                return prefix quote out quote
            }
            {
                result = cleanup($0)
                if (result == DROP) next
                print result
            }
        ' "$profile" > "$TMP_PROFILE"; then
            rm -f "$TMP_PROFILE"
            continue
        fi
        if ! cmp -s "$profile" "$TMP_PROFILE"; then
            cp -p "$profile" "$profile.omo-bak.$(date +%Y%m%d%H%M%S)"
            cat "$TMP_PROFILE" > "$profile"
            REMOVED=$((REMOVED + 1))
        fi
        rm -f "$TMP_PROFILE"
    done
    if [ "$REMOVED" -gt 0 ]; then
        printf '%s shell profile(s) cleaned (backups saved)\n' "$REMOVED"
    else
        printf 'no PATH entries to remove\n'
    fi
}

do_uninstall() {
    header 'Uninstall'
    TOTAL=3
    rm -f "$BIN/omo-model-slim" || fail 'could not remove the command wrapper'
    done_step 'Remove command wrapper'
    rm -rf "$APP" || fail 'could not remove application files'
    done_step 'Remove application files'
    PATH_RESULT=$(cleanup_path_lines)
    done_step 'Clean shell PATH entries' "$PATH_RESULT"
    summary 'Uninstall complete' \
        'Configuration and backups were kept.' \
        'Reinstall: curl -fsSL https://raw.githubusercontent.com/garsetayusuf/omo-model-slim/main/install.sh | bash'
}

case "$ACTION" in
    install|upgrade) do_install ;;
    verify) do_verify ;;
    uninstall) do_uninstall ;;
    *) fail "unknown action: $ACTION (use install, upgrade, verify, or uninstall)" ;;
esac
