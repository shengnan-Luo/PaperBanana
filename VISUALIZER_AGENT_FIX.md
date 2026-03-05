# 修复 VisualizerAgent 以支持 custom_openai provider

## 问题
VisualizerAgent 在第202行抛出 "Unsupported model" 错误，因为没有支持 custom_openai provider。

## 解决方案
需要在 `agents/visualizer_agent.py` 的第132-202行之间添加 custom_openai 的支持。

## 修复代码
在第163行 `elif "gemini" in self.model_name:` 之前添加以下代码：

```python
elif self.exp_config.provider == "custom_openai":
    if cfg["use_image_generation"]:
        # 自定义 OpenAI 兼容图像生成
        aspect_ratio = "1:1"
        if "additional_info" in data and "rounded_ratio" in data["additional_info"]:
            aspect_ratio = data["additional_info"]["rounded_ratio"]

        response_list = await generation_utils.call_custom_openai_image_with_retry_async(
            model_name=self.model_name,
            prompt=prompt_text,
            config={
                "aspect_ratio": aspect_ratio,
                "quality": "standard",
            },
            max_attempts=5,
            retry_delay=30,
        )
    else:
        # 自定义 OpenAI 兼容文本生成（用于代码生成）
        response_list = await generation_utils.call_custom_openai_text_with_retry_async(
            model_name=self.exp_config.model_name,
            contents=content_list,
            config={
                "system_prompt": self.system_prompt,
                "temperature": self.exp_config.temperature,
                "max_output_tokens": cfg["max_output_tokens"],
            },
            max_attempts=5,
            retry_delay=30,
        )
```

## 临时解决方案
如果无法修改文件，可以：
1. 在界面中选择 "gemini" 或 "evolink" provider
2. 或者将图像模型名称改为包含 "gemini" 的名称（如 "gemini-image"）

## 完整修复
还需要类似地修复其他代理文件：
- `agents/critic_agent.py`
- `agents/stylist_agent.py`
- `agents/retriever_agent.py`
- 等等

每个代理文件都需要在其 provider 路由逻辑中添加 `elif self.exp_config.provider == "custom_openai":` 分支。
