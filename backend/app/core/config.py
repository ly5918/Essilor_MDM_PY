"""应用配置：从环境变量 / .env 读取，指向现有 ruoyi_plus 数据库。"""
import os


def _load_dotenv(path=".env"):
    """极简 .env 解析（避免额外依赖）。"""
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    except FileNotFoundError:
        pass


_load_dotenv()

class Settings:
    # 现有数据库（复用原表与数据）
    DB_HOST: str = os.getenv("DB_HOST", "127.0.0.1")
    DB_PORT: int = int(os.getenv("DB_PORT", "3306"))
    DB_USER: str = os.getenv("DB_USER", "root")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "root")
    DB_NAME: str = os.getenv("DB_NAME", "ruoyi_plus")
    DB_CHARSET: str = os.getenv("DB_CHARSET", "utf8mb4")

    # 后端服务端口（前端 /dev-api 代理目标）
    PORT: int = int(os.getenv("PORT", "8000"))

    # JWT（cmd-poc 为 mock 登录，鉴权为可选；保留以便标准登录路径可用）
    JWT_SECRET: str = os.getenv("JWT_SECRET", "essilor-cmd-poc-secret")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 8

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"mysql+aiomysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset={self.DB_CHARSET}"
        )


settings = Settings()
