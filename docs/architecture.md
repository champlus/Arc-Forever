# Architecture Overview

Arc Forever keeps Arc Browser usable offline by replacing remote authentication checks with a local identity guard.

## How It Works

1. **Pre-check & Safety Backup**
   - Verifies the installed Arc build and local user authentication cache.
   - Backs up original binaries and signature resources to `~/Library/Application Support/Arc Forever/Backups`.

2. **Binary Injection**
   - Inserts a `LC_LOAD_DYLIB` load command into the Mach-O header to load `ArcForeverGuard.dylib`.
   - Compiles the guard locally as a universal (`arm64` + `x86_64`) library using Apple Command Line Tools.

3. **Runtime Local Authentication**
   - Intercepts Firebase authentication callbacks in process memory.
   - Returns the cached local user identity so remote server invalidation cannot trigger forced sign-out.
   - Suppresses background update and forced sign-out feature flags at runtime without modifying saved preferences.

4. **One-Click Restoration**
   - Running `restore` validates original file hashes and restores untouched application files, cleanly removing the guard and patch receipt.

## Scope

- **Local Operation**: Official cloud features (such as Arc Sync) remain inactive once server infrastructure is retired.
- **Data Integrity**: Existing Spaces, tabs, history, and extensions stay in their original locations without migration.
