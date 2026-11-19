# syntax=docker/dockerfile:1
# Build a bootable VyOS runtime container image from a nightly ISO.
#
# Context: the build directory containing the ISO (see build-vyos-image.sh).
# The live ISO's squashfs is extracted and used as the container rootfs;
# the container boots VyOS init as PID 1 and must run privileged with
# /dev/net/tun available, like any VyOS container deployment.
#
# This is a community build path, not an official VyOS artifact. Verify the
# booted container on your host before using it in a lab.
ARG ISO_FILE
FROM debian:bookworm-slim AS extractor
ARG ISO_FILE
RUN apt-get update && apt-get install -y --no-install-recommends \
      squashfs-tools xorriso \
    && rm -rf /var/lib/apt/lists/*
COPY ${ISO_FILE} /tmp/vyos.iso
RUN mkdir -p /mnt/iso /rootfs \
    && mount -o loop,ro /tmp/vyos.iso /mnt/iso \
    && unsquashfs -d /rootfs /mnt/iso/live/filesystem.squashfs \
    && umount /mnt/iso

FROM scratch
COPY --from=extractor /rootfs/ /
# VyOS runtime needs these for container operation.
RUN mkdir -p /dev/net && mknod /dev/net/tun c 10 200 || true
ENTRYPOINT ["/sbin/init"]
CMD []
