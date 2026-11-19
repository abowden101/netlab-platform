#!/usr/bin/env bash
# Build a VyOS runtime container image from a VyOS nightly ISO.
#
# There is NO official prebuilt VyOS router container image. VyOS LTS package
# repositories are closed to the public; only rolling nightly builds are
# published. This script downloads the nightly ISO you name, verifies its
# SHA256 against the release checksums, and builds a bootable runtime
# container image from the ISO's live filesystem.
#
# Usage:
#   ./scripts/build-vyos-image.sh 1.5-rolling-202507120000
#
# The version MUST be supplied explicitly — nothing is downloaded by default.
# Requires: docker, curl, unsquashfs (squashfs-tools), sudo for loop mounts
# on some hosts. The resulting image is tagged vyos-runtime:<version>.
#
# This build path is community practice, not an official VyOS artifact.
# Verify the booted container on your host before using it in a lab.
set -euo pipefail

VERSION="${1:-}"
if [ -z "$VERSION" ]; then
  echo "Usage: $0 <vyos-rolling-version>  (e.g. 1.5-rolling-202507120000)" >&2
  exit 2
fi

ISO_URL="https://github.com/vyos/vyos-rolling-nightly-builds/releases/download/${VERSION}/vyos-${VERSION}-generic-amd64.iso"
WORKDIR="${TMPDIR:-/tmp}/vyos-build-${VERSION}"
mkdir -p "$WORKDIR"
ISO="$WORKDIR/vyos-${VERSION}-generic-amd64.iso"

echo "Downloading $ISO_URL ..."
curl -fL -o "$ISO" "$ISO_URL"

echo "Verifying SHA256 ..."
curl -fL -o "$WORKDIR/SHA256SUMS" \
  "https://github.com/vyos/vyos-rolling-nightly-builds/releases/download/${VERSION}/SHA256SUMS" \
  || echo "WARNING: no SHA256SUMS file published for this release — verify the ISO yourself."
if [ -f "$WORKDIR/SHA256SUMS" ]; then
  (cd "$WORKDIR" && sha256sum -c SHA256SUMS --ignore-missing) \
    || { echo "ERROR: SHA256 mismatch — refusing to build." >&2; exit 1; }
fi

echo "Building container image vyos-runtime:${VERSION} ..."
docker build \
  -f "$(dirname "$0")/vyos-runtime.Dockerfile" \
  --build-arg "ISO_FILE=$ISO" \
  -t "vyos-runtime:${VERSION}" \
  "$WORKDIR"

echo "Done: vyos-runtime:${VERSION}"
echo "Use it in a topology as:  image: vyos-runtime:${VERSION}  (kind: vyos)"
