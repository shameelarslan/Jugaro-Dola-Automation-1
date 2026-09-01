# Mandatory Application Release & Update Workflow Rule

Whenever a new version, feature, bugfix, or UI update is requested to be released:

## ⚠️ STRICT EXECUTION ORDER:

### 1. Sync & Build Production Installer
1. Sync all modified files (`ui/`, `app/`, `sitecustomize.py`, `data/app_version.txt`) into:
   - `dist/WaqasAutomationPro/ui/` & `dist/WaqasAutomationPro/_internal/ui/`
   - `dist/WaqasAutomationPro/app/` & `dist/WaqasAutomationPro/_internal/app/`
   - `dist/WaqasAutomationPro/data/` & `dist/WaqasAutomationPro/_internal/data/`
2. Compile the full **`WaqasAutomationPro_vX.X.X_Setup.exe` (~118MB)** Windows Setup using Inno Setup (`python scripts/compile_installer.py`).
3. Package the **`update_vX.X.X.zip`** fast patch zip.

### 2. Synchronize Git & GitHub Releases First
1. Commit and push all source changes to the `main` branch of both repositories:
   - `shameelarslan/Jugaro-Dola-Automation`
   - `shameelarslan/Jugaro-Dola-Automation-1`
2. Create GitHub Release tag `vX.X.X` on both repositories.
3. Upload **BOTH** assets to GitHub Releases on both repositories:
   - `WaqasAutomationPro_vX.X.X_Setup.exe` (~118 MB installer)
   - `update_vX.X.X.zip` (patch package)
4. Verify via GitHub CLI (`gh release view vX.X.X`) that the `.exe` is 100% uploaded and accessible.

### 3. Deploy Cloud In-App Update to Installed Admins (ONLY AFTER GITHUB IS READY)
1. ONLY AFTER the `.exe` and release are live on GitHub:
   - Upload `update_vX.X.X.zip` to Supabase Storage (`releases` bucket).
   - Register or update the release in Supabase `app_releases` table (`is_active = True`, `is_mandatory = True`, `target_email = '*'`).
2. This ensures that any admin user receiving the in-app update notification downloads the latest verified build containing all new tabs, charts, and features.
