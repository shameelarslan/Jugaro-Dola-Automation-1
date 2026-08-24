"""
Account Manager — Manages Facebook accounts metadata & profile locations.
Ensures stable account_id mapping deterministically to data/accounts/{account_id}/user_data/.
"""

from pathlib import Path
from config import ACCOUNTS_DIR

class AccountManager:
    """
    Facebook Account Manager.
    Maps account_id deterministically to persistent browser profile paths.
    Primary test account: test_account_01.
    """
    def __init__(self):
        self.default_account_id = "test_account_01"

    def get_account_profile_dir(self, account_id: str = "test_account_01") -> Path:
        """Returns deterministic persistent profile directory for specified account_id."""
        return (ACCOUNTS_DIR / account_id / "user_data").resolve()

    def get_accounts(self):
        """Returns list of configured accounts with deterministic profile directories."""
        return [
            {
                "account_id": "test_account_01",
                "name": "Test Account 01",
                "profile_dir": str(self.get_account_profile_dir("test_account_01")),
                "status": "LIVE",
            }
        ]
