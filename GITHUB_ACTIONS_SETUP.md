# GitHub Actions - Fully Automatic Release Sync

## ✅ What This Does

**Automatically syncs GitHub releases to Supabase** without any manual work!

### Triggers:
1. 🎯 **When you create/publish a release** - Instantly syncs
2. ⏰ **Every 6 hours** - Checks for new releases automatically  
3. 🔧 **Manual button click** - Run anytime from GitHub UI

---

## 🚀 Setup (1-Minute)

### Step 1: Add GitHub Secrets
In your GitHub repository settings:
- Go to **Settings** → **Secrets and variables** → **Actions**
- Add 2 new secrets:

| Secret Name | Value |
|---|---|
| `SUPABASE_URL` | Your Supabase project URL |
| `SUPABASE_KEY` | Your Supabase anon/service key |

**How to find these:**
1. Go to [Supabase Console](https://app.supabase.com)
2. Select your project
3. Click **Settings** → **API**
4. Copy `Project URL` and `anon/public` key

### Step 2: Done! ✨
The workflow file is already at: `.github/workflows/sync-releases.yml`

Just push to GitHub:
```bash
git add .github/workflows/sync-releases.yml
git commit -m "Add GitHub Actions release sync workflow"
git push origin main
```

---

## 📋 How It Works

**Scenario 1: You Release v2.1.4**
```
1. Create GitHub release "v2.1.4"
2. Upload MSI/EXE files
3. Add changelog
4. Click "Publish release" ← GitHub Actions auto-triggers!
   ↓
5. Action fetches release data
6. Syncs to Supabase automatically
7. Admins get pop-up instantly! 🎉
```

**Scenario 2: 6-Hour Auto-Check**
```
Every 6 hours:
1. GitHub Actions runs automatically
2. Checks for new releases on GitHub
3. Syncs any new ones to Supabase
4. No manual action needed!
```

**Scenario 3: Manual Run (Anytime)**
```
Go to: GitHub Repo → Actions → "Sync Releases to Supabase"
Click: "Run workflow" button
Boom! Runs immediately
```

---

## 🔍 Monitor Workflow

### View Logs:
1. Go to your GitHub repo
2. Click **Actions** tab
3. Click **"Sync Releases to Supabase"**
4. Click latest run
5. See real-time logs ✅

### Success Log Example:
```
🔄 Starting GitHub → Supabase release sync...
Found 1 releases on GitHub
✅ Updated release v2.1.4 in Supabase
✅ Sync complete! 1 releases synced
```

---

## 🎯 Configuration

### Change Sync Interval
Edit `.github/workflows/sync-releases.yml` line 11:

```yaml
schedule:
  - cron: '0 */6 * * *'  # Every 6 hours
  # - cron: '0 * * * *'  # Every hour
  # - cron: '0 0 * * *'  # Every day at midnight
```

[Cron format](https://crontab.guru/)

### Add More Admin Emails
Edit `scripts/auto_release_sync.py` line 19:
```python
ADMIN_EMAILS = [
    "shameelarslanali786@gmail.com",
    "new_admin@example.com",  # Add here
]
```

---

## ⚙️ Workflow Details

```yaml
Triggers:
├─ 🎯 When release is published (immediate)
├─ ⏰ Every 6 hours (automatic)
└─ 🔧 Manual button click (on-demand)

Steps:
├─ Checkout your code
├─ Setup Python 3.11
├─ Install dependencies
├─ Run auto_release_sync.py
└─ Save logs (if any errors)

Environment:
└─ Secrets: SUPABASE_URL, SUPABASE_KEY
```

---

## 🚨 Troubleshooting

### "Workflow failed: Authentication failed"
- Check `SUPABASE_URL` and `SUPABASE_KEY` are correct
- Make sure key has database access
- Regenerate key if needed

### "No releases synced"
- Check that release tag matches semantic versioning (v2.1.4)
- Verify release has MSI or EXE file
- Check workflow logs for errors

### "Workflow not triggering on release"
- Make sure workflow file exists: `.github/workflows/sync-releases.yml`
- Confirm file is on `main` branch
- GitHub may take 1-2 minutes to recognize new workflow

---

## 📊 Comparison: All 3 Methods

| Feature | Manual | Task Scheduler | GitHub Actions |
|---------|--------|---|---|
| **Setup Time** | 0 min | 5 min | 1 min |
| **Triggers** | You run it | Every 6 hours | Release + 6hrs + manual |
| **Best For** | Testing | Local machine | Teams/CI-CD |
| **Requires** | Script + Python | Windows + Python | GitHub only |
| **Cost** | Free | Free | Free |
| **Visibility** | Terminal | Windows logs | GitHub Actions UI |
| **Automation** | ❌ None | ✅ 100% | ✅ 100% |

**👍 Recommended: GitHub Actions** (best automation + visibility)

---

## 🎓 Next Steps

1. ✅ Add secrets to GitHub
2. ✅ Push workflow file
3. ✅ Create a test release
4. ✅ Watch GitHub Actions run
5. ✅ Verify Supabase synced correctly
6. ✅ Test admin gets pop-up

**Fully automatic! 🚀**
