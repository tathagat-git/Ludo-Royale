"""Central configuration – everything comes from environment variables."""
import os


class Settings:
    APP_NAME = "Ludo Royale"
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me-in-production")
    ACCESS_TOKEN_DAYS = int(os.getenv("ACCESS_TOKEN_DAYS", "7"))
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/ludo.db")
    # comma separated list; only needed when frontend is hosted on another origin
    CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if o.strip()]
    TURN_SECONDS = int(os.getenv("TURN_SECONDS", "30"))     # human turn timer
    BOT_DELAY = float(os.getenv("BOT_DELAY", "0.9"))        # "thinking" time of bots
    FRONTEND_DIST = os.getenv("FRONTEND_DIST", "")          # defaults to ../frontend/dist


settings = Settings()
