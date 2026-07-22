"""
config.py
---------
Central configuration. All values are read from environment variables so
nothing sensitive (DB password, JWT secret) is hard-coded.

Used by: db.py, app.py, auth.py
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

class Config:
    DB_HOST = os.environ.get("DB_HOST", "localhost")
    DB_PORT = int(os.environ.get("DB_PORT", 3306))
    DB_USER = os.environ.get("DB_USER", "root")
    DB_PASSWORD = os.environ.get("DB_PASSWORD", "MySql@123")
    DB_NAME = os.environ.get("DB_NAME", "wareflow_db")

    JWT_SECRET = os.environ.get("JWT_SECRET", "change-this-in-production")
    JWT_EXPIRY_MINUTES = int(os.environ.get("JWT_EXPIRY_MINUTES", 480))  # 8 hr shift

    # Ordered list of production stage names, used to determine which stage
    # comes next when a batch stage's target quantity is reached.
    # Override with a comma-separated STAGE_ORDER env var if your line differs.
    STAGE_ORDER = os.environ.get(
        "STAGE_ORDER",
        "Cutting,Assembly,Finishing,Packing"
    ).split(",")

    # Thresholds used by background jobs
    DELAY_CHECK_INTERVAL_MINUTES = int(os.environ.get("DELAY_CHECK_INTERVAL_MINUTES", 15))
    LOW_STOCK_CHECK_INTERVAL_MINUTES = int(os.environ.get("LOW_STOCK_CHECK_INTERVAL_MINUTES", 15))
    DEMAND_FORECAST_INTERVAL_HOURS = int(os.environ.get("DEMAND_FORECAST_INTERVAL_HOURS", 24))
