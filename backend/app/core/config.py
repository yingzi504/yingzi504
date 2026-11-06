"""
应用配置管理
使用 pydantic-settings 从 .env 文件加载配置
"""
from pydantic_settings import BaseSettings
from typing import Optional, List
from pathlib import Path
from ipaddress import ip_address
from urllib.parse import urlsplit
import tempfile


BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """应用配置"""
    
    # 服务配置
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True
    
    # CORS 配置。局域网共享地址由私网地址和受限前端端口共同约束，
    # 避免 DHCP 更换本机 IP 后需要反复修改配置。
    cors_origins: str = "http://localhost:3000,http://localhost:5173,http://localhost:5174,http://localhost:5175"
    cors_allow_private_network: bool = True
    cors_private_ports: str = "5173,5174,5175"
    
    # 文件上传配置
    max_upload_size_mb: int = 10
    upload_dir: str = "uploads"
    output_dir: str = "output"

    @staticmethod
    def _resolve_storage_path(value: str) -> Path:
        path = Path(value)
        if path.is_absolute():
            return path.resolve()
        return (BACKEND_DIR / path).resolve()

    @property
    def upload_path(self) -> Path:
        return self._resolve_storage_path(self.upload_dir)

    @property
    def output_path(self) -> Path:
        return self._resolve_storage_path(self.output_dir)
    
    # 数据库配置
    database_url: str = "sqlite:///./data/resume.db"
    
    # LLM 配置
    llm_config_name: str = ""
    llm_provider: str = "litellm"
    llm_model: Optional[str] = None
    llm_api_type: str = "chat-completions"
    llm_api_endpoint: Optional[str] = None
    llm_api_key: Optional[str] = None
    llm_api_base: Optional[str] = None
    llm_tool_calling: bool = True
    llm_vision: bool = True
    llm_max_input_tokens: int = 128000
    llm_max_output_tokens: int = 16000
    llm_json_retries: int = 2
    # SSL 证书验证（默认开启；某些自定义 endpoint 可能需要关闭）
    llm_ssl_verify: bool = True
    
    # API 版本化配置（步骤4.7）
    api_version: str = "v1"
    api_version_int: int = 1
    deprecated_versions: str = ""  # 逗号分隔的已废弃版本列表，如 "v0"

    # 应用配置
    environment: str = "development"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# 全局配置实例
settings = Settings()


def ensure_storage_directories(config: Settings = settings) -> None:
    """Create configured storage directories and verify they are writable."""
    for path in (config.upload_path, config.output_path):
        path.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(prefix=".write-probe-", dir=path):
            pass


def get_settings() -> Settings:
    """获取配置实例"""
    return settings


def configured_cors_origins(config: Settings = settings) -> list[str]:
    """Return normalized explicitly configured browser origins."""
    return [
        origin.strip().rstrip("/")
        for origin in config.cors_origins.split(",")
        if origin.strip()
    ]


def _private_frontend_ports(config: Settings = settings) -> set[int]:
    ports = set()
    for value in config.cors_private_ports.split(","):
        value = value.strip()
        if value:
            ports.add(int(value))
    return ports


def private_network_origin_regex(config: Settings = settings) -> str | None:
    """Build the CORS regex for private IPv4 frontend development origins."""
    if not config.cors_allow_private_network:
        return None
    ports = "|".join(str(port) for port in sorted(_private_frontend_ports(config)))
    if not ports:
        return None
    private_ipv4 = (
        r"(?:10(?:\.\d{1,3}){3}"
        r"|192\.168(?:\.\d{1,3}){2}"
        r"|172\.(?:1[6-9]|2\d|3[01])(?:\.\d{1,3}){2})"
    )
    return rf"^https?://{private_ipv4}:(?:{ports})$"


def is_allowed_browser_origin(
    origin: str | None,
    request_base_url: str | None = None,
    config: Settings = settings,
) -> bool:
    """Validate a state-changing request origin against the sharing policy."""
    if not origin:
        return True
    normalized = origin.rstrip("/")
    allowed = set(configured_cors_origins(config))
    if request_base_url:
        allowed.add(request_base_url.rstrip("/"))
    if normalized in allowed:
        return True
    if not config.cors_allow_private_network:
        return False
    try:
        parsed = urlsplit(normalized)
        host = parsed.hostname
        port = parsed.port
        address = ip_address(host) if host else None
    except ValueError:
        return False
    return bool(
        parsed.scheme in {"http", "https"}
        and parsed.netloc
        and not parsed.path
        and not parsed.query
        and not parsed.fragment
        and address
        and address.version == 4
        and address.is_private
        and port in _private_frontend_ports(config)
    )
