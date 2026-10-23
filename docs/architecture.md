# Arc Forever architecture

Arc Forever v0.1.0 is an experimental, source-distributed patcher for an existing macOS Arc installation. The commands are `arc_forever.py status`, `apply`, and `restore`. The [compatibility matrix](compatibility.md) separates verified patch structure, native harness behavior, and actual browser observations.

## In-place application patch

The patcher verifies Arc's original bundle identity, executable name, version, build, and whole-executable SHA-256 before mutation. It also requires an existing local `StorableAuthState.session.user.id`; a missing or invalid cached identity is rejected before any mutation. This tool does not provision a fresh Arc installation or replace first-time login. Unpatched `status` checks the full main-executable hash rather than relying on version labels. Mach-O editing adds a library load command for `ArcForeverGuard.dylib`, using unused header space and preserving executable code and section offsets. Unknown binary structures, unexpected hashes, and repeated application are rejected.

The guard is built locally from Objective-C source with Apple's Command Line Tools as a universal arm64/x86_64 library. It is installed inside the existing app. The patcher preserves the app path, name, `Info.plist`, bundle identifier, Chromium profiles, and ordinary launch entry points. It neither edits the duplicate-instance check nor adds a launcher app, alternate home directory, separate browser profile, mock Keychain flag, or `get-task-allow` entitlement.

## Injection strategies and signatures

`apply --strategy auto` checks the existing SIP status and available build definitions; it never changes SIP or other system security settings.

| Strategy | Carrier | Behavior |
| --- | --- | --- |
| `framework` | `Contents/Frameworks/libswiftCompatibilitySpan.dylib` | Available only with already-disabled SIP and a verified carrier hash. Injects `@loader_path/ArcForeverGuard.dylib`, signs the changed carrier ad hoc, and verifies that the original main executable remains byte-identical. |
| `main` | `Contents/MacOS/Arc` | Injects `@executable_path/../Frameworks/ArcForeverGuard.dylib`, then signs the main application ad hoc with hardened runtime and disabled library validation. It does not deep-re-sign ArcCore or Chromium helpers. |

The framework strategy retains the main executable's original vendor CMS signature and entitlements, but changes a sealed resource: the original whole-bundle resource seal no longer matches. Preserving the main signature is not equivalent to preserving an untouched, notarized application bundle. Framework-only injection is rejected when SIP is enabled; disabling SIP to use it is not part of this project.

The main strategy is the implementation path for SIP-enabled installations. It cannot reproduce the vendor's signing identity or restricted entitlements. macOS may request Keychain reauthorization, and vendor-dependent passkey, CloudKit, or other behavior can differ. A successful main-strategy run on an already SIP-disabled host is not evidence of a stock SIP-enabled run. See the test matrix for precisely which configuration was exercised.

## Local identity and callbacks

The guard installs Objective-C runtime overrides at the Firebase authentication boundary. It supplies a local `FIRUser` from Arc's persisted local identity, returns it through current-user and listener callbacks, completes reload locally, and prevents remote sign-out or invalidation from clearing that local identity. If the local cache is missing and the private patch-time authentication snapshot is available, the guard can restore that cached state. No valid remote account or token is required for this local identity.

Cloud-token requests fail with an offline error. The guard does not mint, forge, refresh, or store usable cloud credentials. Firestore listeners report an offline error to use the client's local fallback. The main strategy builds a CloudKit adapter that reports no cloud account; the framework strategy retains the original CloudKit implementation because the original main entitlements are preserved. Neither strategy promises restoration of Arc Sync or any discontinued vendor service.

## Shutdown and update flags

The identified Arc feature flags `arc-force-sign-out-enabled` and `arc-updates-dialog-enabled` are set to `false` through `transientFeatureFlagOverrides` in the volatile `NSArgumentDomain` of `NSUserDefaults`. Other override pairs are retained. This is an in-process preference override; no preference plist is rewritten. The guard also suppresses supported Sparkle automatic-update paths while loaded.

These flags were located in shipped client code. Static tracing and a test harness establish what the patch targets; actual browser results establish only the behavior observed in the tested build. The guard does not alter system time, DNS, host files, server account status, or unknown future shutdown mechanisms.

## Backup, rollback, and restore

Before mutation, `apply` saves the original main executable, injection carrier, signature resource file, file modes, relevant Finder attributes, and integrity hashes under `~/Library/Application Support/Arc Forever/Backups`. It always saves the validated existing local authentication JSON. Keep this backup while the patch is installed, because the guard can restore a missing identity cache from the saved snapshot through the application receipt. The directory and sensitive records use restricted local permissions. These backups contain private state and original application files and must not be published.

The application receives a patch receipt referring to its backup. A manifest tracks prepared, applied, rolled-back, and restored states. Installation and signing failures trigger restoration of saved files. `status` reports the selected strategy and integrity of the installed guard and carrier. `restore` validates backup hashes and the expected application identity before restoring the saved files and removing the guard and receipt. Explicit `--backup` handles an interrupted operation whose receipt is unavailable.

This is a backup of changed application files, not a complete app or profile backup. The patcher does not migrate or rewrite the browser profile. Restoring does not roll back tabs, history, extensions, preferences, or browser writes made while Arc was running; it also cannot undo a macOS permission decision.

## Verification boundary

Python tests cover executable parsing, repeated or unsupported patch rejection, backup integrity and path validation, changed-executable refusal, missing-identity rejection before mutation, and failure rollback. The native harness uses synthetic Firebase classes to check local identities, callbacks, cloud-token errors, forced sign-out, and feature flag overrides. These checks do not contact or disable a real user account.

Real browser acceptance must separately cover ordinary launch, navigation, Spaces/tabs, close/reopen persistence, website sessions, Keychain-protected passwords, extensions, and restore. The recorded private-profile tests exercised the actual CLI and both strategies on a SIP-disabled Apple Silicon host; their mock Keychain fixture provides no evidence about existing real Keychain permissions. The framework strategy also passed normal launch, HTTPS navigation, restoration, and reapplication with the existing installation and ordinary profile. No Keychain prompt was observed, but real website cookies, saved passwords, and passkeys were not directly tested. A passing signature verification is not a test of these features. Only observed, configuration-specific results belong in the compatibility matrix.
