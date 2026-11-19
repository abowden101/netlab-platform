# BYO-Image Guide (Bring Your Own Image)

## License notice — read this first

**This project bundles, downloads, and links NO proprietary network
operating system images.**

Cisco IOS-XE, Arista cEOS, and Juniper vJunos-switch are proprietary
software owned by their vendors. You may only use them if you hold a valid
license or entitlement from the vendor. It is your responsibility — not this
project's — to obtain images lawfully and to comply with the vendor's license
terms, including any restriction on redistribution, lab use, or evaluation.

- Never commit an image file, image URL, or license key to this repository.
  The `.gitignore` blocks `*.qcow2`, `*.vmdk`, `*.ova`, `*.iso`, `*.img`,
  and `*.tar` for this reason.
- Never share an uploaded image with another user of a hosted deployment
  unless your license permits it.
- Images you upload are stored on the lab host only, under the upload
  directory, and are referenced by SHA256 — never by a public URL.

FRR and Linux host images are open-source and are pulled from public
registries automatically. VyOS is open-source but has no official prebuilt
router container image; see the VyOS section below.

## Upload flow (Cisco IOS-XE, Arista cEOS, Juniper vJunos)

1. **Obtain the image lawfully.** Download the container image from the
   vendor (Cisco Software Download, arista.com, juniper.net) under your own
   account and license. Export it as a Docker image tarball, e.g.
   `docker save <image> -o ios-xe.tar`.
2. **Open the UI** → **Images** → **Upload BYO image**.
3. **Tick the license acknowledgement.** The upload is refused without it.
   The acknowledgement and the SHA256 are stored with the image record.
4. **Upload the tarball.** The API streams it to disk, computes SHA256 as it
   writes, enforces the size cap (`MAX_IMAGE_UPLOAD_MB`, default 4096), and
   rejects anything that is not a `.tar` file.
5. **Load it.** Click **Load** (or `POST /api/v1/images/{id}/load`). This
   runs `docker load -i <file>` on the lab host and records the image tags
   the tarball contains. Only after a successful load can the image be
   selected for a lab.
6. **Use it.** Pick the image in a topology (`image: byo:<sha256-prefix>`)
   or select it in the UI when deploying a lab whose driver requires a BYO
   image. Deploying a lab with a driver whose image is not configured fails
   with a clear error naming the driver — it never falls back to a download.

### What the driver expects

| Driver | Containerlab kind | Console | Notes |
|---|---|---|---|
| `ios-xe` | `cisco_iosxe` | SSH | Catalyst 8000V container; set credentials on first boot |
| `ceos` | `ceos` | SSH | Arista cEOS container |
| `vjunos` | `juniper_vjunos-switch` | SSH | vJunos-switch container |

Default credentials in the drivers are the vendors' documented lab
defaults — change them in your topology's `env` / startup-config before
any shared deployment.

## VyOS — build your own runtime image

VyOS publishes rolling nightly ISOs, but no official prebuilt router
container image. LTS package repositories are closed to the public. Build
the runtime image yourself from a nightly ISO:

```bash
./scripts/build-vyos-image.sh 1.5-rolling-202507120000
```

The script downloads the ISO you name (nothing is downloaded by default),
verifies its SHA256 against the release checksums, and builds
`vyos-runtime:<version>` from the ISO's live filesystem. Then use
`image: vyos-runtime:<version>` with `kind: vyos`. Verify the booted
container on your host before using it in a lab — this is a community build
path, not an official VyOS artifact.

## FRR and Linux hosts — public images

These are pulled automatically; nothing to upload:

| Driver | Image |
|---|---|
| `frr` | `quay.io/frrouting/frr-containerlab:10.7.1` |
| `linux` | `alpine:3.20` |

## Verifying an upload

Every upload response includes the SHA256. Compare it with the checksum the
vendor published (or the one you computed locally) before loading:

```bash
sha256sum ios-xe.tar
```

If the checksums differ, delete the upload and re-download the image. The
API refuses to load an image whose stored SHA256 does not match the file on
disk.
