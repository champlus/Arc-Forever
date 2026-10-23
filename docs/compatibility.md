# Compatibility & Verification

Arc Forever is tested on macOS across both Apple Silicon (arm64) and Intel (x86_64).

## Supported Arc Versions

| Arc Version | Build | Status | Notes |
| --- | --- | --- | --- |
| 1.170.0 | 89123 | Verified | Tested on macOS 15 Sequoia (Apple Silicon) |
| 1.169.0 | 88758 | Supported | Mach-O patch definition available |

## Injection Strategies

The tool selects the optimal strategy automatically (`--strategy auto`):

- **`main` (Default / Recommended)**: Works across standard macOS setups with SIP enabled. Modifies and re-signs the main executable with hardened runtime.
- **`framework`**: Used in environments where SIP is disabled, injecting via an internal framework library while keeping the main binary signature untouched.

## Verified Functionality

- [x] Application launches normally with existing profile and Spaces
- [x] Web browsing (HTTPS navigation, JavaScript, local storage persistence)
- [x] Extensions, bookmarks, and pinned tabs preserved
- [x] Local auth guard suppresses cloud sign-out triggers
- [x] Clean restoration returns exact original files
