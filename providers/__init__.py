"""
Provider 包 - 管理不同 API 提供商的接口
"""

from .base import BaseProvider
from .evolink import EvolinkProvider
from .openai_compatible import OpenAICompatibleProvider


def create_provider(provider_name: str, **kwargs) -> BaseProvider:
    """
    工厂函数：根据名称创建 provider 实例

    Args:
        provider_name: 提供商名称 ("evolink", "openai", "custom" 等)
        **kwargs: 传递给 provider 构造函数的参数

    Returns:
        BaseProvider 实例
    """
    providers = {
        "evolink": EvolinkProvider,
        "openai": OpenAICompatibleProvider,
        "openai_compatible": OpenAICompatibleProvider,
        "custom": OpenAICompatibleProvider,  # 自定义 OAI 兼容服务商
    }

    if provider_name not in providers:
        raise ValueError(
            f"未知的 provider: {provider_name}。"
            f"可用的 provider: {list(providers.keys())}"
        )

    return providers[provider_name](**kwargs)


def create_custom_openai_provider(
    api_key: str,
    base_url: str,
    model_name: str,
    organization: str = None,
    timeout: int = 120,
) -> OpenAICompatibleProvider:
    """
    便捷函数：创建自定义 OpenAI 兼容 provider

    Args:
        api_key: API 密钥
        base_url: API 基础 URL
        model_name: 模型名称（用于标识，实际使用时还需要在调用时指定）
        organization: 组织 ID（可选）
        timeout: 请求超时时间（秒）

    Returns:
        OpenAICompatibleProvider 实例
    """
    return OpenAICompatibleProvider(
        api_key=api_key,
        base_url=base_url,
        organization=organization,
        timeout=timeout,
    )
