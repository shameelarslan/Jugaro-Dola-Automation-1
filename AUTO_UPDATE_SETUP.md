# Auto-Update Release Sync Setup Guide

## ✅ What's Automated

Whenever you release a new version on GitHub:

1. **Automatic Detection** - System checks GitHub releases API every 6 hours
2. **Auto-Sync to Supabase** - Downloads new release info and stores in database
3. **Admin Notification** - All admin users get pop-up update notification
4. **One-Click Install** - Users click "Download & Install" → Auto-installs latest version

---

## 🔧 Setup Options

### Option 1: Manual Sync (On-Demand)
Run this whenever you release a new version:
```batch
cd D:\Jugaro-Dola-Automation-1
py scripts\auto_release_sync.py
```

Or double-click:
```
scripts\sync_github_releases.bat
```

---

### Option 2: Automatic Sync Every 6 Hours (Windows Task Scheduler)

**Step 1:** Open PowerShell as Administrator
```powershell
# Right-click PowerShell → Run as Administrator
```

**Step 2:** Navigate to project folder
```powershell
cd D:\Jugaro-Dola-Automation-1
```

**Step 3:** Run setup script
```powershell
powershell -ExecutionPolicy Bypass -File "scripts\setup_auto_sync_task.ps1"
```

**Result:** Task "WaqasAutomation_ReleaseSync" will run every 6 hours automatically

---

### Option 3: GitHub Actions (CI/CD - Fully Automatic)

Add this to `.github/workflows/sync-releases.yml`:

```yaml
name: Sync Releases to Supabase

on:
  release:
    types: [published, created]
  schedule:
    - cron: '0 */6 * * *'  # Every 6 hours

jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install supabase python-dotenv packaging
      - name: Sync releases
        env:
          SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          SUPABASE_KEY: ${{ secrets.SUPABASE_KEY }}
        run: python scripts/auto_release_sync.py
```

---

## 🎯 How It Works

### When You Release:
1. Create release on GitHub with version tag (e.g., `v2.1.3`)
2. Upload MSI/EXE installer files
3. Add changelog in release notes

### What Happens Automatically:
1. Sync script detects new release on GitHub
2. Extracts version, download URL, changelog
3. Creates entry in Supabase `app_releases` table
4. **All admins** get pop-up: "Update v2.1.3 available"
5. Click "Download & Install" → Auto-installs

---

## 📋 Configuration

Edit admin emails in `scripts/auto_release_sync.py`:

```python
ADMIN_EMAILS = [
    "shameelarslanali786@gmail.com",
    "admin2@example.com",  # Add more admins
]
```

---

## ✨ Features

| Feature | Status |
|---------|--------|
| GitHub API Integration | ✅ Automatic |
| Supabase Sync | ✅ Automatic |
| Admin Targeting | ✅ Configurable |
| Download Progress | ✅ Visual bar |
| Automatic Install | ✅ Background |
| Changelog Display | ✅ Beautiful popup |
| Mandatory Updates | ✅ Force update option |

---

## 🚀 Testing

**Manually test sync right now:**
```bash
cd D:\Jugaro-Dola-Automation-1
py scripts\auto_release_sync.py
```

**Expected output:**
```
🔄 Starting GitHub → Supabase release sync...
Found X releases on GitHub
✅ Updated/Created release v2.1.3 in Supabase
✅ Sync complete! X releases synced
```

---

## 📝 Release Checklist

When releasing new version:

- [ ] Create GitHub release with version tag (v2.1.3)
- [ ] Upload MSI and EXE installer files
- [ ] Add comprehensive changelog
- [ ] Run `py scripts\auto_release_sync.py` (or let scheduler do it)
- [ ] Verify in Supabase `app_releases` table
- [ ] Check that admins see update pop-up

---

## 🐛 Troubleshooting

**"No releases synced"**
- Check GitHub token/permissions
- Verify `ADMIN_EMAILS` are correct in script
- Check Supabase connection

**"Download fails during install"**
- Verify GitHub release download URL is public
- Check installer file exists in release assets
- Check admin user's internet connection

**"Task Scheduler won't create task"**
- Run PowerShell as Administrator
- Use correct project path in script
- Check Windows permissions

---

## 📞 Support

Questions? Check:
- `app/core/updater.py` - Update engine
- `app/gui/dialogs/update_dialog.py` - UI popup
- `scripts/auto_release_sync.py` - Sync logic
