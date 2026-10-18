"""全局配置"""
from pydantic import model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # === App ===
    APP_NAME: str = "多Agent学习系统"
    DEBUG: bool = True

    # === Auth / JWT ===
    AUTH_ENABLED: bool = False
    JWT_SECRET: str = ""              # JWT 签名密钥（AUTH_ENABLED=true 时必填）
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 10080   # 默认 7 天

    # === Database ===
    DATABASE_URL: str = ""

    # === LLM Provider ===
    LLM_PROVIDER: str = "deepseek"   # deepseek / longcat / spark

    # === OpenAI 兼容接口（主 provider） ===
    OPENAI_API_KEY: str = ""          # 硅基流动 SiliconFlow 等 OpenAI 兼容 API Key
    OPENAI_BASE_URL: str = ""         # 第三方代理地址 (阿里云百炼/Azure/OpenRouter 等)，留空用官方
    ANTHROPIC_API_KEY: str = ""
    DEFAULT_STRONG_MODEL: str = "gpt-4o"
    DEFAULT_LIGHT_MODEL: str = "gpt-4o-mini"
    MAX_REVIEW_ITERATIONS: int = 3
    AGENT_TIMEOUT_SECONDS: int = 120

    # === DeepSeek（默认，OpenAI 兼容，走硅基流动 SiliconFlow） ===
    DEEPSEEK_API_KEY: str = ""        # 留空时复用 OPENAI_API_KEY
    DEEPSEEK_BASE_URL: str = ""       # 留空时复用 OPENAI_BASE_URL

    # === Longcat（备用） ===
    LONGCAT_API_KEY: str = ""
    LONGCAT_BASE_URL: str = ""
    LONGCAT_MODEL: str = ""

    # === 分档模型（逻辑档位 -> 实际模型 ID） ===
    MODEL_FAST: str = "Qwen/Qwen2.5-32B-Instruct"
    MODEL_STANDARD: str = "deepseek-ai/DeepSeek-V3"
    MODEL_CODE: str = "Qwen/Qwen3-Coder-30B-A3B-Instruct"
    MODEL_STRONG: str = "deepseek-ai/DeepSeek-V3.2"

    # === Cache ===
    CACHE_TTL_MINUTES: int = 5
    RESOURCE_CACHE_HOURS: int = 24

    # ============================================================
    # Chroma 向量库
    # ============================================================
    CHROMA_URL: str = "http://localhost:8000"
    CHROMA_COLLECTION: str = "edu_knowledge"

    # ============================================================
    # Redis
    # ============================================================
    REDIS_URL: str = "redis://localhost:6379/0"

    # === Embedding 模型 ===
    # 模式 1: 远程 API (OpenAI 兼容) — 填写 EMBEDDING_BASE_URL + EMBEDDING_API_KEY
    # 模式 2: 本地模型 (sentence-transformers) — EMBEDDING_BASE_URL 留空
    EMBEDDING_MODEL: str = "BAAI/bge-m3"
    EMBEDDING_BASE_URL: str = ""   # 留空 = 用本地 sentence-transformers
    EMBEDDING_API_KEY: str = ""    # 远程 API Key (可与 OPENAI_API_KEY 相同)
    EMBEDDING_DIM: int = 1024      # embedding 维度 (bge-m3=1024, MiniLM=384, text-embedding-3-small=1536)

    # ============================================================
    # 知识图谱
    # ============================================================
    MASTERY_THRESHOLD: float = 0.6
    MAX_CHAT_HISTORY: int = 20

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    @model_validator(mode="after")
    def _apply_llm_defaults(self):
        # DeepSeek 复用 OpenAI 兼容接口的 Key（.env 中硅基流动 Key 填在 OPENAI_API_KEY）
        if not self.DEEPSEEK_API_KEY:
            self.DEEPSEEK_API_KEY = self.OPENAI_API_KEY
        if not self.DEEPSEEK_BASE_URL:
            self.DEEPSEEK_BASE_URL = self.OPENAI_BASE_URL
        return self

    @model_validator(mode="after")
    def _validate_auth_config(self) -> "Settings":
        """开启鉴权时必须配置有效的 JWT_SECRET，否则启动即失败 (fail-fast)"""
        if self.AUTH_ENABLED:
            secret = (self.JWT_SECRET or "").strip()
            # 拒绝空值以及任何 "change-me..." 占位值 (含仓库 .env 中的示例)
            if not secret or "change-me" in secret.lower():
                raise ValueError(
                    "AUTH_ENABLED=true 但未配置有效的 JWT_SECRET，"
                    "请通过环境变量 JWT_SECRET 设置一个强随机密钥后再启动"
                )
        return self


settings = Settings()


# ============================================================
# 讯飞星火 WebSocket 配置（备用 provider，未填写 Key 时不会启用）
# ============================================================
SPARK_APP_ID: str = ""
SPARK_API_KEY: str = ""
SPARK_API_SECRET: str = ""
SPARK_URLS: dict = {
    "lite": "wss://spark-api.xf-yun.com/v1.1/chat",
    "x1.5": "wss://spark-api.xf-yun.com/v2.1/chat",
    "pro": "wss://spark-api.xf-yun.com/v3.1/chat",
    "ultra": "wss://spark-api.xf-yun.com/v3.5/chat",
}
