import os
import sys
import hashlib
import subprocess

# 1. Disk-Priority Module Finder
class DiskPriorityFinder:
    def find_spec(self, fullname, path, target=None):
        if fullname == "app" or fullname.startswith("app."):
            for finder in sys.meta_path:
                if finder is not self and hasattr(finder, 'find_spec') and 'PathFinder' in finder.__class__.__name__:
                    try:
                        spec = finder.find_spec(fullname, path, target)
                        if spec is not None:
                            return spec
                    except Exception:
                        pass
        return None

if not any(isinstance(f, DiskPriorityFinder) for f in sys.meta_path):
    sys.meta_path.insert(0, DiskPriorityFinder())

# 2. Self-Healing Executable Hash Integrity Check
def _check_and_heal_executable():
    try:
        if not getattr(sys, 'frozen', False):
            return

        app_exe = sys.executable
        if not app_exe or not os.path.exists(app_exe):
            return

        base_dir = os.path.dirname(os.path.abspath(app_exe))
        internal_dir = os.path.join(base_dir, "_internal")
        helper_exe = os.path.join(internal_dir, "UpdateHelper.exe")
        ref_exe = os.path.join(internal_dir, "WaqasAutomationPro.exe")

        if not os.path.exists(helper_exe) or not os.path.exists(ref_exe):
            return

        def _get_hash(p):
            with open(p, "rb") as f:
                return hashlib.sha256(f.read()).hexdigest().lower()

        curr_hash = _get_hash(app_exe)
        ref_hash = _get_hash(ref_exe)

        if curr_hash != ref_hash:
            # Running executable is outdated! Self-heal using UpdateHelper
            DETACHED_FLAGS = 0x00000008 | 0x00000200 if os.name == 'nt' else 0
            curr_pid = os.getpid()
            subprocess.Popen(
                [helper_exe, "--source", internal_dir, "--target", base_dir, "--exe", os.path.basename(app_exe), "--pid", str(curr_pid)],
                creationflags=DETACHED_FLAGS,
                close_fds=True
            )
            sys.exit(0)
    except Exception:
        pass

_check_and_heal_executable()