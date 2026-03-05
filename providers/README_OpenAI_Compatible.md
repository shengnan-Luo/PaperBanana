# OpenAI 兼容 API 服务商集成指南

本项目现已支持所有兼容 OpenAI API 格式的服务商，包括但不限于：

- OpenAI 官方 API
- Azure OpenAI
- 各种开源模型服务（如 Ollama、LocalAI、vLLM 等）
- 第三方 API 代理服务

## 快速开始

### 1. 基本用法

```python
from providers import create_provider, create_custom_openai_provider

# 方法 1: 使用工厂函数
provider = create_provider(
    "openai_compatible",
    api_key="your-api-key",
    base_url="https://api.your-provider.com",  # 替换为实际的 API 地址
    organization="your-org-id",  # 可选
    timeout=120  # 可选，默认 120 秒
)

# 方法 2: 使用便捷函数
provider = create_custom_openai_provider(
    api_key="your-api-key",
    base_url="https://api.your-provider.com",
    model_name="your-model-name"  # 仅用于标识
)
```

### 2. 文本生成

```python
import asyncio

async def generate_text_example():
    # 创建 provider
    provider = create_custom_openai_provider(
        api_key="sk-your-api-key",
        base_url="https://api.openai.com",  # 或其他兼容服务
        model_name="gpt-4"
    )

    # 准备内容
    contents = [
        {"type": "text", "text": "请解释什么是机器学习"}
    ]

    # 生成文本
    results = await provider.generate_text(
        model_name="gpt-4",  # 实际使用的模型名
        contents=contents,
        system_prompt="你是一个专业的AI助手",
        temperature=0.7,
        max_output_tokens=1000
    )

    print(results[0])

    # 记得关闭 session
    await provider.close()

# 运行示例
# asyncio.run(generate_text_example())
```

### 3. 图像生成

```python
async def generate_image_example():
    # 创建 provider
    provider = create_custom_openai_provider(
        api_key="sk-your-api-key",
        base_url="https://api.openai.com",
        model_name="dall-e-3"
    )

    # 生成图像
    results = await provider.generate_image(
        model_name="dall-e-3",
        prompt="一只可爱的小猫在花园里玩耍",
        aspect_ratio="16:9",  # 支持 1:1, 16:9, 9:16, 4:3, 3:4
        quality="standard"  # 或 "hd"
    )

    # results[0] 是 base64 编码的图像数据
    image_b64 = results[0]

    # 记得关闭 session
    await provider.close()

# 运行示例
# asyncio.run(generate_image_example())
```

## 常见服务商配置

### OpenAI 官方

```python
provider = create_custom_openai_provider(
    api_key="sk-your-openai-key",
    base_url="https://api.openai.com",
    model_name="gpt-4"
)
```

### Azure OpenAI

```python
provider = create_custom_openai_provider(
    api_key="your-azure-key",
    base_url="https://your-resource.openai.azure.com",
    model_name="gpt-4"
)
```

### Ollama (本地部署)

```python
provider = create_custom_openai_provider(
    api_key="ollama",  # Ollama 通常不需要真实的 key
    base_url="http://localhost:11434",
    model_name="llama2"
)
```

### 其他第三方服务

```python
# 示例：某个第三方 API 代理
provider = create_custom_openai_provider(
    api_key="your-proxy-key",
    base_url="https://api.your-proxy.com",
    model_name="gpt-3.5-turbo"
)
```

## 支持的功能

### 文本生成
- ✅ 纯文本对话
- ✅ 多模态输入（文本 + 图片）
- ✅ 系统提示词
- ✅ 温度控制
- ✅ Token 限制
- ✅ 自动重试机制

### 图像生成
- ✅ 文本到图像
- ✅ 多种宽高比
- ✅ 质量控制
- ✅ 自动下载并转换为 base64
- ❌ 图像到图像（OpenAI API 限制）

## 错误处理

provider 内置了完善的错误处理机制：

- **4xx 客户端错误**：立即失败，不重试（如 API key 错误、模型不存在等）
- **5xx 服务器错误**：自动重试，指数退避
- **网络错误**：自动重试
- **超时错误**：自动重试

## 注意事项

1. **API Key 安全**：请妥善保管您的 API 密钥，不要在代码中硬编码
2. **费用控制**：使用付费服务时请注意 token 消耗和费用
3. **速率限制**：不同服务商有不同的速率限制，请合理控制请求频率
4. **模型支持**：确保您使用的模型名称在目标服务商中存在
5. **Session 管理**：使用完毕后记得调用 `await provider.close()` 关闭连接

## 集成到项目中

要在现有项目中使用新的 provider，只需要：

1. 在配置文件中添加新的 provider 配置
2. 使用 `create_provider("openai_compatible", ...)` 创建实例
3. 按照现有的接口调用 `generate_text()` 和 `generate_image()` 方法

新的 provider 完全兼容现有的 `BaseProvider` 接口，可以无缝替换。
