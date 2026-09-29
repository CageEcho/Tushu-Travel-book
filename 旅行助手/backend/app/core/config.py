"""应用配置：从项目根目录 .env 读取，不含任何密钥回显。"""
import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[2]  # backend/
PROJECT_ROOT = BACKEND_DIR.parent

# 优先加载项目根目录 .env，其次 backend/.env
for _p in (PROJECT_ROOT / ".env", BACKEND_DIR / ".env"):
    if _p.exists():
        load_dotenv(_p)
        break

DATA_DIR = PROJECT_ROOT / "data"
ASSETS_DIR = DATA_DIR / "assets"
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"


class Settings:
    def __init__(self) -> None:
        self.baidu_map_ak: str = os.getenv("BAIDU_MAP_AK", "").strip()
        self.deepseek_api_key: str = os.getenv("DEEPSEEK_API_KEY", "").strip()
        self.deepseek_model: str = os.getenv("DEEPSEEK_MODEL", "deepseek-chat").strip()
        self.deepseek_base_url: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").strip()
        self.database_url: str = os.getenv("DATABASE_URL", f"sqlite:///{DATA_DIR / 'tripflow.db'}")
        self.allow_origins: str = os.getenv("ALLOW_ORIGINS", "*")
        # 唤起百度地图 App：每段最多途经点数（超出拆段）、调用来源 src
        self.baidu_nav_max_via: int = int(os.getenv("BAIDU_NAV_MAX_VIA", "15") or 15)
        self.baidu_uri_src: str = os.getenv("BAIDU_URI_SRC", "webapp.tripflow.tripflow").strip()


settings = Settings()


def ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
