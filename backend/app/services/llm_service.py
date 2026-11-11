"""
LLM调用服务
使用LiteLLM封装统一的LLM调用接口
"""
import asyncio
import json
import logging
import os
from typing import Optional, Dict, Any
from fastapi import HTTPException

# ── 修复 Python 3.13 + Windows SSL 证书崩溃 ──
# 注：主入口 run_server.py 已全局 monkey-patch ssl.SSLContext._load_windows_store_certs
# 此处保留 certifi 环境变量作为备用（当 llm_service 被单独导入时）
try:
    import certifi
    _cafile = certifi.where()
    os.environ["SSL_CERT_FILE"] = _cafile
    os.environ["REQUESTS_CA_BUNDLE"] = _cafile
except ImportError:
    pass

# 导入配置
from app.core.config import settings


logger = logging.getLogger(__name__)


class LLMService:
    """LLM调用服务"""

    ERROR_CODE_HEADER = "X-LLM-Error-Code"
    PUBLIC_ERROR_MESSAGES = {
        "insufficient_balance": "模型服务余额不足，请联系管理员充值或切换模型后重试",
        "authentication_failed": "模型服务认证失败，请联系管理员检查 API 密钥",
        "rate_limited": "模型服务请求过于频繁，请稍后重试",
        "connection_failed": "模型服务暂时无法连接，请稍后重试",
        "invalid_response": "模型返回格式异常，请重新处理；如持续失败请联系管理员",
        "service_unavailable": "模型服务暂时不可用，请稍后重试或联系管理员",
    }

    @staticmethod
    def _classify_provider_error(exc: Exception) -> tuple[str, int, bool]:
        """Return a stable public category without exposing provider internals."""
        message = str(exc).lower()
        if any(token in message for token in (
            "insufficient balance", "insufficient_balance", "余额不足",
            "insufficient quota", "billing hard limit",
        )):
            return "insufficient_balance", 503, False
        if any(token in message for token in (
            "invalid api key", "incorrect api key", "authentication",
            "unauthorized", "invalid credential", "permission denied",
        )):
            return "authentication_failed", 503, False
        if any(token in message for token in (
            "rate limit", "too many requests", "ratelimit",
        )):
            return "rate_limited", 503, True
        if any(token in message for token in (
            "timeout", "timed out", "connection error", "connection refused",
            "network error", "service unavailable", "bad gateway",
        )):
            return "connection_failed", 503, True
        return "service_unavailable", 500, False

    @staticmethod
    def public_error_message(exc: Exception) -> str:
        """Extract only messages created by this service for task persistence."""
        if isinstance(exc, HTTPException):
            code = (exc.headers or {}).get(LLMService.ERROR_CODE_HEADER)
            if code in LLMService.PUBLIC_ERROR_MESSAGES:
                return LLMService.PUBLIC_ERROR_MESSAGES[code]
        return LLMService.PUBLIC_ERROR_MESSAGES["service_unavailable"]

    @staticmethod
    def _is_retryable_http_error(exc: HTTPException) -> bool:
        code = (exc.headers or {}).get(LLMService.ERROR_CODE_HEADER)
        return code in {"rate_limited", "connection_failed"}
    
    @staticmethod
    async def call_llm(
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        model: Optional[str] = None
    ) -> str:
        """
        调用LLM获取响应
        
        Args:
            prompt: 用户提示词
            system_prompt: 系统提示词
            temperature: 温度参数
            max_tokens: 最大token数
            model: 使用的模型
            
        Returns:
            LLM响应文本
        """
        try:
            # 这里先实现一个模拟版本，后续接入真实的LiteLLM
            # 在生产环境中，使用以下代码：
            #
            from litellm import completion
            
            # 使用配置中的模型，如果传入了 model 则覆盖
            use_model = model or settings.llm_model
            
            # 使用自定义 endpoint 时，自动追加 provider 前缀
            # LiteLLM 需要通过前缀识别 provider（如 openai/、anthropic/）
            # 豆包/火山方舟使用 OpenAI 兼容 API，故用 openai/ 前缀
            if use_model and settings.llm_api_endpoint and "/" not in use_model:
                use_model = f"openai/{use_model}"
            
            # 设置环境变量供 LiteLLM 使用（兼容旧版调用方式）
            if settings.llm_api_key:
                os.environ["OPENAI_API_KEY"] = settings.llm_api_key
            if settings.llm_api_endpoint:
                os.environ["OPENAI_API_BASE"] = settings.llm_api_endpoint
            
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            # 构建 LiteLLM 参数
            litellm_params = {
                "model": use_model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens
            }
            
            # 如果配置了自定义 endpoint，添加到参数中
            if settings.llm_api_endpoint:
                litellm_params["api_base"] = settings.llm_api_endpoint
            if settings.llm_api_key:
                litellm_params["api_key"] = settings.llm_api_key
            
            # SSL 验证配置（修复 ASN1: NOT_ENOUGH_DATA 错误）
            # 部分自定义 endpoint（如火山方舟）在某些网络环境下可能出现 SSL 握手异常
            ssl_verify = getattr(settings, 'llm_ssl_verify', True)
            litellm_params["ssl_verify"] = ssl_verify
            if not ssl_verify:
                # 同时设置环境变量以兼容底层 openai 库
                os.environ["OPENAI_SSL_VERIFY"] = "false"
            
            response = await asyncio.to_thread(completion, **litellm_params)
            return response.choices[0].message.content
            
            # 临时模拟返回用于调试前后端连通性的开发测试
            # mock_response = LLMService._get_mock_response(prompt)
            # return mock_response
            
        except Exception as e:
            error_code, status_code, _ = LLMService._classify_provider_error(e)
            log = logger.warning if error_code != "service_unavailable" else logger.exception
            log(
                "LLM provider request failed; category=%s error_type=%s model=%s",
                error_code,
                type(e).__name__,
                use_model if 'use_model' in locals() else None,
            )
            raise HTTPException(
                status_code=status_code,
                detail=LLMService.PUBLIC_ERROR_MESSAGES[error_code],
                headers={LLMService.ERROR_CODE_HEADER: error_code},
            ) from e
    
    @staticmethod
    async def call_llm_json(
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 3000,
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        调用LLM并返回JSON格式结果
        
        Args:
            prompt: 用户提示词
            system_prompt: 系统提示词
            temperature: 温度参数
            max_tokens: 最大token数
            model: 使用的模型
            
        Returns:
            解析后的JSON字典
        """
        # 确保系统提示词要求JSON输出
        json_system_prompt = "你是一个专业的JSON输出助手。所有回答必须是合法的JSON格式，不要包含任何Markdown标记或其他说明文字。"
        if system_prompt:
            json_system_prompt = f"{json_system_prompt}\n\n{system_prompt}"
        
        retry_count = max(0, int(settings.llm_json_retries))
        last_error: Optional[Exception] = None

        for attempt in range(retry_count + 1):
            request_system_prompt = json_system_prompt
            if attempt:
                request_system_prompt += (
                    "\n\nThe previous response was invalid. Return one complete "
                    "JSON object without Markdown or explanatory text."
                )
            try:
                response_text = await LLMService.call_llm(
                    prompt=prompt,
                    system_prompt=request_system_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    model=model,
                )
                if not isinstance(response_text, str) or not response_text.strip():
                    raise ValueError("LLM returned an empty response")

                try:
                    parsed = json.loads(response_text.strip())
                except json.JSONDecodeError:
                    parsed = json.loads(LLMService._extract_json(response_text))

                if isinstance(parsed, str):
                    parsed = json.loads(parsed.strip())
                if not isinstance(parsed, dict):
                    raise TypeError(
                        "LLM JSON root must be an object, got "
                        f"{type(parsed).__name__}"
                    )
                return parsed
            except HTTPException as exc:
                last_error = exc
                logger.warning(
                    "LLM JSON request failed; attempt=%d/%d status_code=%s",
                    attempt + 1,
                    retry_count + 1,
                    exc.status_code,
                )
                if not LLMService._is_retryable_http_error(exc) or attempt >= retry_count:
                    raise
            except (json.JSONDecodeError, TypeError, ValueError, AttributeError) as exc:
                last_error = exc
                logger.warning(
                    "LLM JSON response invalid; attempt=%d/%d error_type=%s",
                    attempt + 1,
                    retry_count + 1,
                    type(exc).__name__,
                )

            if attempt < retry_count:
                await asyncio.sleep(0.25 * (attempt + 1))

        logger.error(
            "LLM JSON parsing exhausted retries; attempts=%d error_type=%s",
            retry_count + 1,
            type(last_error).__name__ if last_error else "unknown",
        )
        raise HTTPException(
            status_code=500,
            detail="模型返回格式异常，请重新处理；如持续失败请联系管理员",
            headers={LLMService.ERROR_CODE_HEADER: "invalid_response"},
        )
    
    @staticmethod
    def _extract_json(text: str) -> str:
        """
        从文本中提取JSON部分，并尝试修复常见LLM输出问题

        Args:
            text: 包含JSON的文本

        Returns:
            提取并修复后的JSON字符串
        """
        if not isinstance(text, str) or not text.strip():
            return ""

        # 查找第一个 { 和最后一个 }
        start_idx = text.find('{')
        end_idx = text.rfind('}')

        if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
            text = text[start_idx:end_idx + 1]

        # 尝试多种修复策略
        return LLMService._repair_json(text)

    @staticmethod
    def _repair_json(text: str) -> str:
        """尝试修复JSON常见问题"""
        import re

        # 策略1: 尝试 json_repair 库
        try:
            from json_repair import repair_json
            repaired = repair_json(text, return_objects=False)
            # 验证可解析
            json.loads(repaired)
            return repaired
        except Exception:
            pass

        # 策略2: 自动补全截断的JSON（缺括号）
        # 计算括号差值
        open_braces = text.count('{') - text.count('}')
        open_brackets = text.count('[') - text.count(']')

        # 检查是否在字符串中间截断 -- 引号不匹配
        in_string = text.count('"') % 2 != 0

        repaired = text.rstrip()

        # 移除行末可能截断的半截字符串（最后一个不完整引号之后的内容）
        if in_string:
            # 去掉最后一个不完整字符串
            last_quote = repaired.rfind('"')
            if last_quote > 0:
                # 检查是不是 key 的一部分
                colon_after = repaired.find(':', last_quote)
                if colon_after == -1 or re.search(r'\S', repaired[last_quote+1:]):
                    repaired = repaired[:last_quote].rstrip().rstrip(',')

        # 去掉尾部逗号
        repaired = repaired.rstrip().rstrip(',')

        # 补全缺失的括号
        repaired += ']' * open_brackets
        repaired += '}' * open_braces

        return repaired
    
    @staticmethod
    def _get_mock_response(prompt: str) -> str:
        """
        获取模拟响应（用于开发测试）
        
        Args:
            prompt: 提示词
            
        Returns:
            模拟响应
        """
        # 根据提示词内容返回不同的模拟响应
        if "简历" in prompt and "抽取" in prompt:
            # 简历结构化抽取模拟响应
            return json.dumps({
                "name": "张伟",
                "phone": "13800138000",
                "email": "zhangwei@example.com",
                "location": "北京",
                "age": 32,
                "birth_date": "1994-05-15",
                "position": "高级软件工程师",
                "technical_area": "后端开发",
                "total_exp": "8年",
                "education": [
                    {
                        "period": "2012.09 - 2016.07",
                        "school": "清华大学",
                        "degree": "本科",
                        "major": "计算机科学与技术"
                    },
                    {
                        "period": "2016.09 - 2019.07",
                        "school": "北京大学",
                        "degree": "硕士",
                        "major": "软件工程"
                    }
                ],
                "work": [
                    {
                        "company": "阿里巴巴",
                        "period": "2019.07 - 2022.08",
                        "role": "软件工程师",
                        "tasks": "负责电商平台后端开发，参与订单系统设计，优化数据库查询性能，提升系统响应速度50%"
                    },
                    {
                        "company": "字节跳动",
                        "period": "2022.09 - 至今",
                        "role": "高级软件工程师",
                        "tasks": "主导推荐系统后端架构设计，带领5人团队完成多个核心功能迭代，系统日活用户提升30%"
                    }
                ],
                "project": [
                    {
                        "company": "阿里巴巴",
                        "period": "2020.03 - 2021.06",
                        "name": "双十一订单系统重构",
                        "role": "核心开发",
                        "tasks": "负责订单创建和查询模块重构，使用Redis缓存优化热点数据，系统承载能力提升200%"
                    }
                ],
                "tech_skills": "Python, Java, Go, MySQL, Redis, Kafka, Docker, Kubernetes",
                "lang_skills": "英语",
                "lang_skills_level": "流利",
                "training_exp": "AWS认证解决方案架构师",
                "summary": "8年后端开发经验，精通分布式系统设计，善于解决复杂技术问题，具有良好的团队协作能力",
                "language": "CN"
            }, ensure_ascii=False)
        else:
            # 默认响应
            return json.dumps({"message": "这是一个模拟响应"}, ensure_ascii=False)
