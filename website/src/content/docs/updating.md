---
title: Updating
order: 11
description: Re-run the installer to upgrade safely.
---

# Updating

Re-run the same installer. It downloads the pinned version, verifies checksums, saves the previous installation, and replaces only the CLI files.

```sh
omo-model-slim upgrade
omo-model-slim --version
```

The `update` and `install` aliases do the same thing. If the CLI is not installed yet, run the [one-line installer](/docs/installation) first.

No configuration is read or written during an upgrade.

## Rollback

If an upgrade misbehaves:

```sh
rm -rf ~/.local/share/omo-model-slim
mv ~/.local/share/omo-model-slim.rollback.* ~/.local/share/omo-model-slim
omo-model-slim --version
```

Keep only the rollback copy you intend to use if several exist.

## Version pinning

The installer defaults to `v1.0.3`. Set `OMO_VERSION` to install a different tagged release:

```sh
OMO_VERSION=v1.0.3 sh install.sh
```

Checksums are verified against the release `SHA256SUMS` asset. A missing or mismatched checksum aborts the installation.
