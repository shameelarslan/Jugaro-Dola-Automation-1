import sys
import os
from pathlib import Path

# Enable Disk-Priority Module Loader for PyInstaller frozen runtime
if getattr(sys, 'frozen', False):
    exe_dir = os.path.abspath(os.path.dirname(sys.executable))
    internal_dir = os.path.join(exe_dir, '_internal')
    for d in [exe_dir, internal_dir]:
        if d not in sys.path:
            sys.path.insert(0, d)

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

    sys.meta_path.insert(0, DiskPriorityFinder())
else:
    BASE_DIR = Path(__file__).resolve().parent
    sys.path.insert(0, str(BASE_DIR))

from app.main import main

if __name__ == "__main__":
    main()
