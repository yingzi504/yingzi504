#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -f "$SCRIPT_DIR/deploy.env" ]; then
  set -a
  # shellcheck disable=SC1091
  source "$SCRIPT_DIR/deploy.env"
  set +a
fi

REMOTE_USER="${REMOTE_USER:-root}"
REMOTE_HOST="${REMOTE_HOST:-47.110.226.47}"
REMOTE_PORT="${REMOTE_PORT:-22}"
SSH_PUBLIC_KEY_FILE="${SSH_PUBLIC_KEY_FILE:-${1:-}}"
SSH_PRIVATE_KEY_FILE="${SSH_PRIVATE_KEY_FILE:-}"

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

find_public_key() {
  for key_file in \
    "$HOME/.ssh/id_ed25519.pub" \
    "$HOME/.ssh/id_rsa.pub" \
    "$HOME/.ssh/id_ecdsa.pub"; do
    if [ -f "$key_file" ]; then
      printf '%s\n' "$key_file"
      return 0
    fi
  done
  return 1
}

require_command ssh

if [ -z "$SSH_PUBLIC_KEY_FILE" ]; then
  if ! SSH_PUBLIC_KEY_FILE="$(find_public_key)"; then
    echo "No SSH public key found under ~/.ssh." >&2
    echo "Create one first, for example: ssh-keygen -t ed25519 -C \"<your email acount>\"" >&2
    exit 1
  fi
fi

if [ ! -f "$SSH_PUBLIC_KEY_FILE" ]; then
  echo "SSH public key file does not exist: $SSH_PUBLIC_KEY_FILE" >&2
  exit 1
fi

if [ -z "$SSH_PRIVATE_KEY_FILE" ]; then
  case "$SSH_PUBLIC_KEY_FILE" in
    *.pub) SSH_PRIVATE_KEY_FILE="${SSH_PUBLIC_KEY_FILE%.pub}" ;;
    *)
      echo "Cannot infer the private key from: $SSH_PUBLIC_KEY_FILE" >&2
      echo "Set SSH_PRIVATE_KEY_FILE so the installed key can be verified." >&2
      exit 1
      ;;
  esac
fi

if [ ! -f "$SSH_PRIVATE_KEY_FILE" ]; then
  echo "SSH private key file does not exist: $SSH_PRIVATE_KEY_FILE" >&2
  echo "Set SSH_PRIVATE_KEY_FILE to the private key matching $SSH_PUBLIC_KEY_FILE." >&2
  exit 1
fi

PUBLIC_KEY="$(sed -e 's/\r$//' -e '/^[[:space:]]*$/d' "$SSH_PUBLIC_KEY_FILE" | head -n 1)"
if [ -z "$PUBLIC_KEY" ]; then
  echo "SSH public key file is empty: $SSH_PUBLIC_KEY_FILE" >&2
  exit 1
fi

REMOTE="${REMOTE_USER}@${REMOTE_HOST}"
SSH_OPTS=(
  -p "$REMOTE_PORT"
  -i "$SSH_PRIVATE_KEY_FILE"
  -o IdentitiesOnly=yes
  -o StrictHostKeyChecking=accept-new
)

echo "==> Remote host: $REMOTE"
echo "==> Public key: $SSH_PUBLIC_KEY_FILE"
echo "==> Private key used for verification: $SSH_PRIVATE_KEY_FILE"

if ssh "${SSH_OPTS[@]}" -o BatchMode=yes -o ConnectTimeout=10 "$REMOTE" "echo SSH_KEY_OK" >/dev/null 2>&1; then
  echo "The selected local key already works. Nothing to do."
  exit 0
fi

echo "==> Installing public key on remote server"
echo "If prompted, enter the remote user's password once."

printf '%s\n' "$PUBLIC_KEY" | ssh "${SSH_OPTS[@]}" "$REMOTE" '
set -e
umask 077
mkdir -p "$HOME/.ssh"
touch "$HOME/.ssh/authorized_keys"
key="$(cat)"
key_type="$(printf "%s\n" "$key" | awk "{print \$1}")"
key_data="$(printf "%s\n" "$key" | awk "{print \$2}")"
before_count="$(awk "NF {count++} END {print count+0}" "$HOME/.ssh/authorized_keys")"

# Match the key material rather than the optional comment. Never rewrite the
# file: appending preserves keys that were installed from other computers.
if awk -v type="$key_type" -v data="$key_data" \
  "\$1 == type && \$2 == data {found=1} END {exit !found}" \
  "$HOME/.ssh/authorized_keys"; then
  echo "==> Selected key is already present on the server"
else
  printf "%s\n" "$key" >> "$HOME/.ssh/authorized_keys"
  echo "==> Selected key was appended to the server"
fi
chmod 700 "$HOME/.ssh"
chmod 600 "$HOME/.ssh/authorized_keys"
after_count="$(awk "NF {count++} END {print count+0}" "$HOME/.ssh/authorized_keys")"
echo "==> authorized_keys entries: ${before_count} -> ${after_count}"
'

echo "==> Verifying passwordless SSH login"
if ssh "${SSH_OPTS[@]}" -o BatchMode=yes -o ConnectTimeout=10 "$REMOTE" "echo SSH_KEY_OK"; then
  echo "SSH key configured successfully."
else
  echo "SSH key was copied, but passwordless login verification failed." >&2
  exit 1
fi
