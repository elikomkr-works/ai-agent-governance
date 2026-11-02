#!/bin/bash
# Docker Engine inside WSL2, so the server step can be proven on this machine.
#
# Run it once, from Windows, as root -- which needs no password at all:
#
#   wsl -d Ubuntu-24.04 -u root --cd "/mnt/c/Users/User/OneDrive/Desktop/AiAgent oz" \
#       -- bash tools/wsl_docker_setup.sh
#
# Or from a normal WSL shell, where sudo will ask for the Linux user's password:
#
#   bash /mnt/c/Users/User/OneDrive/Desktop/AiAgent\ oz/tools/wsl_docker_setup.sh
#
# Either way the docker group is granted to the human user, not to root: when
# this runs as root the script resolves that user from SUDO_USER, then from uid
# 1000 (WSL's default account), so the normal shell gets docker without sudo.
#
# Why Docker Engine and not Docker Desktop: Desktop is a ~3 GB Windows
# application with its own licence terms, and the only thing this project needs
# from it is a container runtime. Engine inside WSL2 is the same runtime without
# the application, and it is what the real server will run anyway -- so the image
# is built here under the conditions it will be deployed under.
#
# Why the official apt repository and not `curl https://get.docker.com | sh`:
# this is a security governance project. Piping a remote script into a root
# shell is exactly the pattern its own policy forbids. The repository route
# pins a signed key and a known source, and every step below is readable.
set -euo pipefail

say() { printf '\n== %s\n' "$1"; }

# The account that should end up able to run docker without sudo. Running as
# root leaves $USER as root, which would grant the group to nobody useful.
TARGET_USER="${DOCKER_USER:-${SUDO_USER:-}}"
if [ -z "$TARGET_USER" ] || [ "$TARGET_USER" = "root" ]; then
  TARGET_USER="$(getent passwd 1000 | cut -d: -f1)"
fi
[ -n "$TARGET_USER" ] || TARGET_USER="$USER"
echo "Docker access will be granted to: $TARGET_USER"

# `sudo` is a no-op when already root, but it is not always installed in a
# minimal image; this keeps both routes working.
if [ "$(id -u)" -eq 0 ]; then
  sudo() { "$@"; }
fi

say "1/6  Removing any distro-packaged Docker leftovers"
# Debian/Ubuntu ship old, differently-named packages that conflict with the
# official ones. Missing packages are not an error here.
for pkg in docker.io docker-doc docker-compose podman-docker containerd runc; do
  sudo apt-get remove -y "$pkg" >/dev/null 2>&1 || true
done

say "2/6  Base packages"
sudo apt-get update -qq
sudo apt-get install -y -qq ca-certificates curl gnupg

say "3/6  Docker's signing key"
sudo install -m 0755 -d /etc/apt/keyrings
# --fail so an HTML error page is never written over the key.
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
  -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

say "4/6  Docker's apt repository"
codename="$(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}")"
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $codename stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null

say "5/6  Installing Docker Engine"
sudo apt-get update -qq
sudo apt-get install -y -qq \
  docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

say "6/6  Starting the daemon and granting this user access"
# WSL2 has no systemd by default on older installs, so try both.
sudo service docker start >/dev/null 2>&1 || sudo systemctl start docker || true
sudo usermod -aG docker "$TARGET_USER"

cat <<DONE

== Done.

Version check (as root, because a running shell's group membership is stale):

  wsl -d Ubuntu-24.04 -u root -- docker run --rm hello-world

The group change takes effect in a NEW shell. For $TARGET_USER, close any open
WSL window and open a new one; from then on \`docker\` works without sudo.

If the daemon is not running after a Windows restart:

  sudo service docker start

DONE
