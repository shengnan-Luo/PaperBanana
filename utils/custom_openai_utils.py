# ==================== 自定义 OpenAI 兼容 Provider 扩展 ====================

custom_openai_provider = None

def init_custom_openai_provider(api_key: str, base_url: str = "https://api.openai.com"):
    """用指定的 API Key 和 Base URL 初始化自定义 OpenAI 兼容 Provider（供界面动态传入）。"""
    global custom_openai_provider
    if not api_key:
        return
    from providers.openai_compatible import OpenAICompatibleProvider
    custom_openai_provider = OpenAICompatibleProvider(api_key=api_key, base_url=base_url)
    print(f"已通过界面初始化自定义 OpenAI 兼容 Provider (base_url={base_url})")


async def call_custom_openai_text_with_retry_async(
    model_name, contents, config, max_attempts=5, retry_delay=5, error_context=""
):
    """
    通过自定义 OpenAI 兼容 Provider 进行文本生成。

    Args:
        model_name: 模型名称（如 "gpt-4"）
        contents: 通用内容列表
        config: 配置字典或对象，需包含 system_instruction, temperature, max_output_tokens
        max_attempts: 最大重试次数
        retry_delay: 重试间隔
        error_context: 错误上下文
    """
    print(f"[DEBUG] call_custom_openai_text: model={model_name}, provider={'已初始化' if custom_openai_provider else '未初始化'}")
    if custom_openai_provider is None:
        raise RuntimeError("自定义 OpenAI 兼容 Provider 未初始化，请检查配置。")

    # 从 config 中提取参数（兼容 types.GenerateContentConfig 和 dict）
    if hasattr(config, 'system_instruction'):
        system_prompt = config.system_instruction or ""
        temperature = config.temperature
        max_output_tokens = config.max_output_tokens
        print(f"[DEBUG] call_custom_openai_text: 从 GenerateContentConfig 提取参数")
    elif isinstance(config, dict):
        system_prompt = config.get("system_prompt", "")
        temperature = config.get("temperature", 1.0)
        max_output_tokens = config.get("max_output_tokens", 50000)
        print(f"[DEBUG] call_custom_openai_text: 从 dict 提取参数")
    else:
        system_prompt = ""
        temperature = 1.0
        max_output_tokens = 50000
        print(f"[DEBUG] call_custom_openai_text: 使用默认参数, config type={type(config)}")

    return await custom_openai_provider.generate_text(
        model_name=model_name,
        contents=contents,
        system_prompt=system_prompt,
        temperature=temperature,
        max_output_tokens=max_output_tokens,
        max_attempts=max_attempts,
        retry_delay=retry_delay,
        error_context=error_context,
    )


async def call_custom_openai_image_with_retry_async(
    model_name, prompt, config, max_attempts=5, retry_delay=30, error_context=""
):
    """
    通过自定义 OpenAI 兼容 Provider 进行图像生成。

    Args:
        model_name: 图像模型名称（如 "dall-e-3"）
        prompt: 图像描述提示词
        config: 配置字典，需包含 aspect_ratio, quality 等
        max_attempts: 最大重试次数
        retry_delay: 重试间隔
        error_context: 错误上下文
    """
    print(f"[DEBUG] call_custom_openai_image: model={model_name}, config={config}, provider={'已初始化' if custom_openai_provider else '未初始化'}")
    if custom_openai_provider is None:
        raise RuntimeError("自定义 OpenAI 兼容 Provider 未初始化，请检查配置。")

    aspect_ratio = config.get("aspect_ratio", "16:9")
    quality = config.get("quality", "standard")
    image_urls = config.get("image_urls", None)

    return await custom_openai_provider.generate_image(
        model_name=model_name,
        prompt=prompt,
        aspect_ratio=aspect_ratio,
        quality=quality,
        image_urls=image_urls,
        max_attempts=max_attempts,
        retry_delay=retry_delay,
        error_context=error_context,
    )
