# Arc Forever — Arc Browser after account shutdown

**A reversible, in-place macOS patch for keeping Arc Browser usable with local authentication after the December 22, 2026 account shutdown.** Arc Forever modifies your installed Arc without creating another app or changing its name, interface, bundle identifier, or browser profile. It ships source and a patch tool, never an Arc installer.

[简体中文](README.zh-CN.md) · [Compatibility and test results](docs/compatibility.md) · [Technical design](docs/architecture.md) · [Arc's shutdown announcement](https://arc.net/)

**v0.1.0 is an experimental prerelease.** Arc 1.170.0 passed apply, normal launch with the existing profile, HTTPS browsing, restore, and reapply using the framework strategy on macOS 15.7.4, Apple Silicon, with SIP already disabled. Existing Spaces, tabs, favorites, and active content extensions remained visible; no Keychain prompt was observed. Both strategies also passed private-profile tests. Stock SIP-enabled macOS and direct real-cookie/password/passkey checks remain unverified. See the [test record](docs/compatibility.md); future shutdown mechanisms cannot be guaranteed in advance.

## Install and use

Requires macOS, Python 3, and Apple's Command Line Tools (`xcode-select --install`). An existing Arc profile with a cached signed-in identity is required; this is not a fresh-install or replacement-login tool. Quit Arc first and keep a separate backup of your browser data.

For a double-click menu, download or clone this repository, then open [Arc Forever.command](Arc%20Forever.command) in Finder. Choose Apply, Restore, or Status in the bilingual Terminal menu; it runs the same Python CLI without creating an app.

For command-line use, clone the tool, inspect your installation, then apply:

```sh
git clone https://github.com/ChambersXDU/Arc-Forever.git
cd Arc-Forever
python3 arc_forever.py status
python3 arc_forever.py apply
```

Open Arc normally afterward. The default target is `/Applications/Arc.app`; pass `--app /path/to/Arc.app` to any command for a different installation. Arc Forever does not redirect `HOME`, create another browser profile, use a mock Keychain, or edit `Info.plist`.

Restore the original application files with:

```sh
python3 arc_forever.py restore
```

Backups default to `~/Library/Application Support/Arc Forever/Backups`. They contain the files and signature resources that the tool changes, integrity hashes, and a private snapshot of the required cached local authentication state; they are not a full browser-data backup. Keep these backups while using the patch: the guard can recover a missing identity cache from the saved snapshot referenced by its receipt. `apply --backup-dir /path/to/backups` changes the location. For an interrupted operation without a patch receipt, use `restore --backup /path/to/specific-backup`. Restore refuses to overwrite an installation whose patched carrier has changed since application.

## Signing and system compatibility

The default `--strategy auto` chooses between two injection paths:

| Strategy | When selected | Signing consequences |
| --- | --- | --- |
| `framework` | Only when SIP is **already disabled** and that build's framework is verified. | Modifies a compatibility library; preserves the main executable's original vendor signature and entitlements. The original whole-bundle resource seal no longer matches. |
| `main` | Other supported installations, including SIP-enabled systems. | Modifies and ad-hoc re-signs the main app with hardened runtime and library validation disabled. Original Chromium helper and ArcCore signatures remain intact. |

**Arc Forever never disables or changes SIP. Do not disable SIP to use it.** Explicit strategies are available with `apply --strategy main` or `apply --strategy framework`; the latter is rejected when SIP is enabled. See [tested configurations](docs/compatibility.md) before applying.

A re-signed main app cannot retain the vendor's signing identity or restricted entitlements. macOS may request renewed access to existing Keychain items; vendor-entitlement-dependent passkeys, CloudKit, or other features may differ. A completely invisible change on stock macOS is not guaranteed. Passing signature checks does not prove every browser feature remains unchanged.

## What keeps browsing local

The guard supplies a local Firebase user from Arc's existing authentication state and prevents remote account invalidation from clearing that local identity. Cloud-token requests return an offline error; Arc Forever does not generate valid tokens or reactivate a server account. It also overrides Arc's traced force-sign-out and update-dialog feature flags in process memory and disables supported automatic-update paths. These overrides do not persistently rewrite your preferences.

Arc Sync and other vendor cloud services are not restored. The framework strategy preserves the existing CloudKit path; the main strategy uses a local unavailable-account adapter because vendor CloudKit entitlements cannot be recreated. See the [architecture](docs/architecture.md) for details.

## FAQ

**Does this bypass Arc account shutdown?** It addresses local client authentication and the identified forced-sign-out path, so browsing can use a local identity. It cannot restore a disabled remote account, cloud sync, or a server-side service. Future shutdown behavior remains a limitation until observed.

**Will my tabs, Spaces, cookies, and passwords be moved?** The patcher keeps Arc's existing data location and does not migrate or rewrite the browser profile. Signing changes may still affect access to Keychain-protected data. Check the compatibility record for actual session/password tests rather than assuming that unchanged files mean unchanged access.

**Is this a maintained browser engine?** No. Retaining an Arc build also retains its Chromium security and website-compatibility level. Arc Forever does not provide future Chromium security updates. Updating Arc can replace the patch or install an unsupported version.

## Development and reports

```sh
python3 -m unittest discover -s tests -v
```

The macOS CI workflow runs Python tests and a native authentication harness. The current local verification passed 16 Python tests and both CloudKit configurations of the harness. Browser checks include HTTPS navigation, JavaScript interaction, storage persistence across restart, runtime feature-flag overrides, and exact-file restoration; their configuration and limits are documented in [compatibility](docs/compatibility.md).

Report macOS version, CPU architecture, Arc version/build, the tool revision, and redacted errors. Do not upload browser profiles, authentication state, browsing history, cookies, Keychain contents, backups, or Arc binaries. The ignored `.local/` directory stays private.

Arc Forever is independent of The Browser Company. Project source is [MIT licensed](LICENSE); Arc and its third-party components retain their own licenses.
