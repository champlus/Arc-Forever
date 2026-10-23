# Arc Forever compatibility and testing

Arc Forever v0.1.0 is an experimental in-place patch tool, not a replacement Arc installer. Support is pinned to exact executable hashes. An existing profile with a valid cached signed-in user identity is required; a fresh installation without that cache is rejected before mutation. Both Mach-O slices being patchable does not establish runtime compatibility on both CPU architectures.

| Arc version | Build | Main executable SHA-256 | Patch definition |
| --- | --- | --- | --- |
| 1.169.0 | 88758 | `24e2aca39abd6645528b5f5e1241555a1ab5c925bb6e6c1e9ecaabdd2b83ed51` | Main strategy; initial source sample. |
| 1.170.0 | 89123 | `25af5f4eaaae5aca25021f2737e90cc4d41fdf195c4a5c4012ea31a1bba4b86a` | Main strategy; verified framework carrier definition also available. |
| Other versions | Any | No recognized hash. | Rejected until explicitly supported. |

## Runtime verification

Verification recorded on October 23, 2026: macOS 15.7.4, arm64, with SIP **already disabled**. The actual CLI was tested first with private application copies and profiles, then with the existing `/Applications/Arc.app` installation and its ordinary profile. The public tool patches an existing installation; it does not produce or distribute test copies.

| Configuration | Observed result | Limits |
| --- | --- | --- |
| 1.169.0, main strategy | Static patch definition. | Final in-place browser acceptance pending. |
| 1.170.0, framework strategy | Private-profile checks and ordinary-profile apply, browsing, restore, reapply, and relaunch passed. | Host SIP already disabled; real cookies/passwords/passkeys not directly checked. |
| 1.170.0, main strategy | CLI apply, browser checks, native helper sandbox checks, and exact-file restore passed. | Private profile; host SIP already disabled. |
| 1.170.0, existing installation and ordinary profile | Normal Arc launch preserved both existing Spaces, tabs, favorites, and active content extensions; HTTPS navigation passed. | Framework strategy only; no Keychain prompt observed, which is not a direct Keychain continuity test. |
| Stock SIP-enabled macOS | Not runtime verified. | A main-strategy pass on this SIP-disabled host does not cover the stock configuration. |
| Intel macOS | Universal build and patch support only. | Native browser runtime acceptance pending. |

The framework strategy preserves the original main executable signature and entitlements while changing the bundle's resource seal. The main strategy re-signs the main application ad hoc, keeps hardened runtime, and disables its library validation. Neither establishes seamless Keychain access, passkey support, or full feature equivalence.

### Sanitized ordinary-installation verification record

The existing Arc 1.170.0 installation passed `apply` with the default automatic strategy, which selected `framework` on the already SIP-disabled host. Arc was opened through its normal launch path, with the real home directory and original profile; no alternative `HOME` or mock-Keychain launch flag was used.

- Both existing Spaces, original tabs, and favorites appeared in the ordinary Arc interface.
- HTTPS `example.com` rendered successfully with existing translation/content extensions active. No Keychain authorization prompt was observed during these checks.
- The main executable and `Info.plist` stayed byte-identical. Saved Finder icon attributes were unchanged, and process memory inspection confirmed that the guard was loaded.
- Whole-bundle `codesign --verify` failed with the expected modified-resource mismatch. The unchanged main executable retains its original vendor signature; the modified app is not an untouched vendor-signed bundle.
- After a graceful quit, real restoration recovered every saved original-file hash and Finder attribute and removed the guard and receipt. Reapplying and reopening normally again recovered the existing Spaces and tabs.

Real website-cookie continuity, saved-password access, and passkeys were **not directly tested**. Absence of a prompt during browsing is not proof that every Keychain item remains accessible.

### Sanitized private-profile verification record

Both 1.170.0 strategies passed the following checks with the actual CLI:

- A local test page exercised JavaScript interaction and `localStorage`. In the framework test, two graceful browser cycles observed the fixture's saved-state flag change from `false` on the first cycle to `true` after restart.
- HTTPS navigation to `example.com` returned the expected page title and a secure JavaScript context.
- Apply/restore round trips returned the main executable, compatibility shim, and `CodeResources` to their exact original SHA-256 hashes.
- In the main-strategy browser run, native Chromium GPU, utility, and renderer helpers each returned `1` in the recorded `sandbox_check` probes. This is a scoped observation of the tested helper processes, not a full sandbox audit.

Runtime debugger checks in 1.170.0 also established that Arc's built-in feature-flag initializer consumed the volatile override, replaced a pre-existing `true` value, and retained an unrelated override pair. The force-sign-out getter returned `0` in three observed calls; the update-dialog getter returned `0`. This verifies the targeted getters in this build, not all future shutdown paths.

The private-profile browser tests used Chromium's `--use-mock-keychain` **only as a test fixture**. The public tool and normal launch do not use that flag. These tests do not establish that real cookies, saved passwords, passkeys, or existing Keychain permissions survive main-app re-signing without prompts. No real account was disabled to produce this record.

## Automated checks

All 16 Python tests passed locally. They cover Mach-O header editing, rejection cases, the independent sidebar exporter, repeat-application refusal, failure rollback, backup checksum refusal, refusal to overwrite a changed main executable, backup path traversal rejection, and missing-identity rejection before mutation. The native harness supplies synthetic Firebase classes and local identity data, then checks local user callbacks, asynchronous completion, offline token errors, forced sign-out preserving identity, and shutdown/update-dialog flag overrides. It neither disables a real account nor simulates every possible official shutdown mechanism.

Both native harness configurations (`AF_PRESERVE_CLOUDKIT=0` and `1`) passed locally. The macOS CI workflow builds and runs both with synthetic data. A green result is not a browser acceptance test or proof of Keychain continuity. The shipped guard contains both arm64 and x86_64 code; a harness run exercises only the runner's native architecture.

## Acceptance record requirements

A useful browser test record identifies the app hash, macOS version, CPU architecture, SIP state, strategy, and observed checks:

- `status` recognizes the original app by its full executable hash; unknown binaries, invalid headers, missing cached identities, and repeat application are rejected.
- `apply` creates a verified backup and preserves application name, path, `Info.plist`, bundle identifier, data directories, and normal entry points.
- Existing Spaces and tabs load, web navigation works, and local state survives closing and reopening Arc.
- Synthetic account invalidation and token errors preserve local identity without valid cloud credentials.
- Feature flag overrides disable the identified forced-sign-out and update-dialog paths without persistent preference edits.
- Website-session, password, extension, and passkey checks are reported individually; untested features remain explicit.
- `restore` returns the saved application files and original signature resources; partial failures leave a recoverable original.

## Future shutdown and browser security

The official [Arc announcement](https://arc.net/) gives December 22, 2026 as the shutdown date. Tests before that date cannot prove coverage of every mechanism that may be used during shutdown. Arc Forever targets identified local authentication and client feature-flag paths; it does not reactivate accounts or restore discontinued cloud services.

Retaining an Arc build also retains its Chromium security and website-compatibility level. Arc Forever does not maintain Chromium or supply future engine security updates.
