# winget package for Lemon

`PrometheanSacrifice.Lemon` installs the Windows `x64` distribution as a
**zip with a nested portable executable**: winget extracts the tree under
its Packages directory and puts a `lemon` command symlink on `PATH`. The
executable resolves its library (`lib/lemon`) through the symlink, so no
environment setup is needed.

## Files

- `template/` — the three manifest YAMLs (`installer`, `defaultLocale`,
  `version`) with `__VERSION__` / `__URL__` / `__SHA__` placeholders.
- `render-manifest.py` — renders a manifest set for a given version,
  installer URL, and local zip (computes the SHA256).

## Validate locally (CI does this on every push)

```sh
python packaging/winget/render-manifest.py build/winget 0.2.0 \
  https://github.com/prometheansacrifice/lemon/releases/download/v0.2.0/lemon-0.2.0-windows-x86_64.zip \
  dist/lemon-0.2.0-windows-x86_64.zip
winget validate --manifest build/winget
```

## Install from a rendered manifest (post-release check)

```powershell
winget install --manifest build\winget --exact
& "$env:LOCALAPPDATA\Microsoft\WinGet\Links\lemon.exe" --help
```

`winget install` downloads `InstallerUrl`, so this full loop only works
once the release asset exists; the release workflow runs it automatically
against the published URL.

## Submitting to winget-pkgs (the public catalog)

1. Publish a release with `lemon-<version>-windows-x86_64.zip`.
2. Render the manifest set for the release (same command as above).
3. Fork `microsoft/winget-pkgs`, copy the three YAMLs into
   `manifests/p/PrometheanSacrifice/Lemon/<version>/`, and open a pull
   request (the `winget-pkgs-automation` bot can do this for you after the
   first manual submission). Reference the release in the PR.
4. After merge: `winget install PrometheanSacrifice.Lemon`.
