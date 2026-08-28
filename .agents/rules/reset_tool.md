# Rule: "reset tool" Command Handler

Whenever the USER says the exact phrase **`reset tool`** (or asks to reset/restore the tool to this perfect golden state):

1. **DO NOT modify or corrupt the workflow, backend, or UI settings.**
2. Immediately execute the Golden Snapshot restore script:
   `python "data/golden_snapshot/restore.py"`
3. Verify that all components are 100% restored to this **Master Golden State**:
   - **Supabase Cloud Backend**: Multi-User Auth, Session Persistence, Auto-Profiles, RLS Security.
   - **Admin Approval System**: Default `Pending` status for new signups, Admin Waqas instant `Active`, Admin Approval buttons in Super Dashboard.
   - **👑 Cloud Super Admin Dashboard**: Modern high-contrast KPI cards (Total Users, Pending Approvals, All-Time Videos, Today's Videos), Leaderboard table, Live telemetry feed, Block/Unblock toggle.
   - **Modern Left Sidebar**: Clean navigation without scrollbars, `✨ About Developer` dialog with Waqas Shaukat creator bio, `💬 Direct Support & Contact` dialog with WhatsApp & Facebook links.
   - **🪪 Bottom SaaS User Profile Card**: Gradient avatar initials, user name, `🟢 Free License Activated` glowing pill, interactive Account Details popup.
   - **Automation Engine**: Playwright native driver, auto prompt suffix ` 15 seconds Video Ratio 9:16`, isolated download pipeline (zero cross-job overwriting), automatic watermark removal/blur, `WaqasAutomation_...` prefix output naming, and session release on Stop Automation.
## Snapshot Update Rule:
- **DO NOT automatically save or overwrite the Golden Snapshot.**
- ONLY update or save `data/golden_snapshot` when the USER explicitly requests: *"snapshot update karo"*, *"golden snapshot save karo"*, or similar explicit commands.
