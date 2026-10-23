# Architecture Overview

Arc Forever keeps Arc Browser working offline on macOS by replacing remote authentication checks with a lightweight local identity guard.

## How It Works

1. **Pre-check & Automatic Backup**
   - Verifies the installed Arc build and cached local session state.
   - Saves a backup of original binaries and signature resources under `~/Library/Application Support/Arc Forever/Backups`.

2. **Universal Binary Injection**
   - Compiles `ArcForeverGuard.dylib` locally as a universal (`arm64` + `x86_64`) library using Apple Command Line Tools.
   - Adds an `LC_LOAD_DYLIB` load command into the Mach-O header.

3. **Runtime Local Session Guard**
   - Intercepts Firebase authentication callbacks in process memory and serves the cached local user profile.
   - Prevents remote token expiration from triggering forced sign-out.
   - Disables forced sign-out and update prompts at runtime.

4. **Lossless Restoration**
   - Running `python3 arc_forever.py restore` verifies original file hashes and restores the untouched application files.
