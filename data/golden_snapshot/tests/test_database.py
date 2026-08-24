import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.storage.database import db
from app.utils.logger import log_info

def test_database_initialization():
    log_info("Testing SQLite database metrics query...", tag="TEST_DB")
    metrics = db.get_metrics()
    log_info(f"Database Metrics: {metrics}", tag="TEST_DB")
    assert isinstance(metrics, dict)
    assert "total_accounts" in metrics
    log_info("Database test passed cleanly.", tag="TEST_DB")

if __name__ == "__main__":
    test_database_initialization()
