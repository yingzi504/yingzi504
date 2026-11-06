"""
TTL 缓存工具 — 步骤4.8

简单的内存缓存实现，用于缓存高频查询结果（如文件列表、统计汇总），
减少磁盘 IO 和重复数据库查询。

用法:
    cache = TTLCache(ttl_seconds=300)  # 5分钟过期
    result = cache.get("key")
    if result is None:
        result = expensive_operation()
        cache.set("key", result)
"""

import time
import threading
from typing import Any, Dict, Optional, Tuple


class TTLCache:
    """带过期时间的内存缓存"""

    def __init__(self, ttl_seconds: int = 300):
        """
        Args:
            ttl_seconds: 缓存项过期时间（秒），默认 5 分钟
        """
        self._ttl = ttl_seconds
        self._store: Dict[str, Tuple[float, Any]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        """获取缓存值，过期返回 None"""
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            timestamp, value = entry
            if time.monotonic() - timestamp > self._ttl:
                del self._store[key]
                return None
            return value

    def set(self, key: str, value: Any) -> None:
        """设置缓存值"""
        with self._lock:
            self._store[key] = (time.monotonic(), value)

    def invalidate(self, key: str = None) -> None:
        """使指定 key 或全部缓存失效"""
        with self._lock:
            if key is None:
                self._store.clear()
            elif key in self._store:
                del self._store[key]

    def __len__(self) -> int:
        with self._lock:
            # 清理过期项
            now = time.monotonic()
            self._store = {
                k: v for k, v in self._store.items()
                if now - v[0] <= self._ttl
            }
            return len(self._store)


# 全局缓存实例
# 文件列表缓存：5 分钟 TTL（文件列表变化不频繁）
output_list_cache = TTLCache(ttl_seconds=300)
# 统计缓存：3 分钟 TTL（统计数据允许短暂延迟）
statistics_cache = TTLCache(ttl_seconds=180)
