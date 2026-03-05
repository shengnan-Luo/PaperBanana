"""
OpenAI 兼容 API Provider
支持所有兼容 OpenAI API 格式的服务商（如 OpenAI、Azure OpenAI、各种开源模型服务等）
"""

import asyncio
import base64
from typing import List, Dict, Any, Optional

import aiohttp

from .base import BaseProvider


class ClientError(Exception):
    """4xx 客户端错误，不应重试（如 400 Bad Request、401 Unauthorized）"""
    pass


class OpenAICompatibleProvider(BaseProvider):
    """
    OpenAI 兼容 API Provider

    支持所有使用 OpenAI API 格式的服务商：
    - 文本模型: 通过 /v1/chat/completions
    - 图像模型: 通过 /v1/images/generations
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.openai.com",
        organization: Optional[str] = None,
        timeout: int = 120,
    ):
        """
        初始化 OpenAI 兼容 Provider

        Args:
            api_key: API 密钥
            base_url: API 基础 URL，默认为 OpenAI 官方
            organization: 组织 ID（可选）
            timeout: 请求超时时间（秒）
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.organization = organization
        self.timeout = timeout
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """获取共享的 aiohttp session，避免每次请求都创建新 session"""
        if self._session is None or self._session.closed:
            connector = aiohttp.TCPConnector(limit=30)
            self._session = aiohttp.ClientSession(connector=connector)
        return self._session

    async def close(self):
        """关闭共享 session"""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    def _get_headers(self) -> Dict[str, str]:
        """构建请求头"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        if self.organization:
            headers["OpenAI-Organization"] = self.organization
        return headers

    # ==================== 内容格式转换 ====================

    def _convert_contents_to_messages(
        self,
        contents: List[Dict[str, Any]],
        system_prompt: str = "",
    ) -> List[Dict[str, Any]]:
        """
        将通用内容列表转换为 OpenAI 兼容的 messages 格式

        通用格式（项目中使用的）:
        [
            {"type": "text", "text": "..."},
            {"type": "image", "source": {"type": "base64", "data": "...", "media_type": "image/jpeg"}},
            {"type": "image", "image_base64": "..."},  # 简化格式
        ]

        转换为 OpenAI 格式:
        [
            {"role": "system", "content": "..."},
            {"role": "user", "content": [
                {"type": "text", "text": "..."},
                {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,..."}},
            ]},
        ]
        """
        messages = []

        # system prompt
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        # 构建 user message 的 content 部分
        user_parts = []
        has_image = False

        for item in contents:
            item_type = item.get("type", "")

            if item_type == "text":
                user_parts.append({"type": "text", "text": item["text"]})

            elif item_type == "image":
                has_image = True
                # 两种图片格式：source 嵌套格式 和 image_base64 直接格式
                source = item.get("source", {})
                if source.get("type") == "base64":
                    media_type = source.get("media_type", "image/jpeg")
                    data = source.get("data", "")
                    data_url = f"data:{media_type};base64,{data}"
                    user_parts.append({
                        "type": "image_url",
                        "image_url": {"url": data_url},
                    })
                elif "image_base64" in item:
                    data_url = f"data:image/jpeg;base64,{item['image_base64']}"
                    user_parts.append({
                        "type": "image_url",
                        "image_url": {"url": data_url},
                    })

        # 如果没有图片，可以简化为纯文本
        if not has_image and len(user_parts) == 1:
            messages.append({"role": "user", "content": user_parts[0]["text"]})
        else:
            messages.append({"role": "user", "content": user_parts})

        return messages

    # ==================== HTTP 请求封装 ====================

    async def _post_json(self, url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """发送 POST 请求并返回 JSON 响应"""
        print(f"[DEBUG] [OpenAI兼容] POST {url}")
        print(f"[DEBUG] [OpenAI兼容]   🔗 请求端点: {url}")
        print(f"[DEBUG] [OpenAI兼容]   model={payload.get('model', 'N/A')}, payload keys={list(payload.keys())}")

        session = await self._get_session()
        async with session.post(
            url,
            json=payload,
            headers=self._get_headers(),
            timeout=aiohttp.ClientTimeout(total=self.timeout),
        ) as resp:
            status = resp.status
            body = await resp.json()
            print(f"[DEBUG] [OpenAI兼容]   响应 status={status}, keys={list(body.keys()) if isinstance(body, dict) else type(body)}")

            if status >= 400:
                error_msg = body.get("error", body) if isinstance(body, dict) else body
                print(f"[DEBUG] [OpenAI兼容]   ❌ 错误详情: {error_msg}")
                # 4xx 客户端错误不重试，直接抛出特定异常
                if 400 <= status < 500 and status != 429:
                    raise ClientError(f"HTTP {status}: {error_msg}")

            resp.raise_for_status()
            return body

    async def _download_image_as_base64(self, url: str) -> Optional[str]:
        """从 URL 下载图片并转换为 base64"""
        try:
            session = await self._get_session()
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                resp.raise_for_status()
                image_data = await resp.read()
                return base64.b64encode(image_data).decode("utf-8")
        except Exception as e:
            print(f"下载图片失败 ({url}): {e}")
            return None

    # ==================== 文本生成 ====================

    async def generate_text(
        self,
        model_name: str,
        contents: List[Dict[str, Any]],
        system_prompt: str = "",
        temperature: float = 1.0,
        max_output_tokens: int = 50000,
        max_attempts: int = 3,
        retry_delay: float = 5,
        error_context: str = "",
    ) -> List[str]:
        """
        通过 /v1/chat/completions 生成文本

        兼容 OpenAI Chat Completions API 格式
        """
        url = f"{self.base_url}/v1/chat/completions"

        # 构建请求体
        messages = self._convert_contents_to_messages(contents, system_prompt)
        payload = {
            "model": model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_output_tokens,
        }

        # 计算内容摘要
        content_types = [item.get("type", "?") for item in contents]
        sys_len = len(system_prompt) if system_prompt else 0
        print(f"[DEBUG] [OpenAI兼容 文本] 请求: model={model_name}, temp={temperature}, max_tokens={max_output_tokens}")
        print(f"[DEBUG] [OpenAI兼容 文本]   内容: {content_types}, system_prompt 长度={sys_len}")

        for attempt in range(max_attempts):
            try:
                response = await self._post_json(url, payload)

                # 提取文本响应
                choices = response.get("choices", [])
                if choices:
                    text = choices[0].get("message", {}).get("content", "")
                    if text.strip():
                        usage = response.get("usage", {})
                        print(f"[DEBUG] [OpenAI兼容 文本] ✓ 成功, 响应长度={len(text)}, usage={usage}")
                        return [text]

                print(f"[OpenAI兼容 文本] 响应为空，{retry_delay}s 后重试...")
                if attempt < max_attempts - 1:
                    await asyncio.sleep(retry_delay)

            except ClientError as e:
                # 4xx 客户端错误，立即失败不重试（模型名错误、参数错误等）
                context_msg = f" ({error_context})" if error_context else ""
                print(f"[OpenAI兼容 文本] ❌ 客户端错误{context_msg}: {e}。不再重试。")
                return ["Error"]

            except Exception as e:
                context_msg = f" ({error_context})" if error_context else ""
                current_delay = min(retry_delay * (2 ** attempt), 30)
                print(
                    f"[OpenAI兼容 文本] 第 {attempt + 1} 次尝试失败{context_msg}: {e}。"
                    f"{current_delay}s 后重试..."
                )
                if attempt < max_attempts - 1:
                    await asyncio.sleep(current_delay)
                else:
                    print(f"[OpenAI兼容 文本] 全部 {max_attempts} 次尝试失败{context_msg}")

        return ["Error"]

    # ==================== 图像生成 ====================

    async def generate_image(
        self,
        model_name: str,
        prompt: str,
        aspect_ratio: str = "16:9",
        quality: str = "standard",
        image_urls: Optional[List[str]] = None,
        max_attempts: int = 3,
        retry_delay: float = 30,
        poll_interval: float = 3,
        error_context: str = "",
    ) -> List[str]:
        """
        通过 /v1/chat/completions 生成图像（自定义实现）

        注意：这里使用 chat/completions 而不是标准的 images/generations
        因为某些API服务商将图像生成也通过chat接口实现
        """
        url = f"{self.base_url}/v1/chat/completions"

        # 构建请求体 - 使用chat格式而不是images格式
        # 优化提示词以确保模型理解这是图像生成任务
        system_message = "You are an image generation AI. When given a description, you must generate an image and return the result in markdown format: ![Generated Image](URL). Do not provide text explanations, only generate and return the image URL in the specified format."

        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": f"Generate an image based on this description: {prompt}"}
        ]

        payload = {
            "model": model_name,
            "messages": messages,
            "temperature": 0.3,  # 降低温度以获得更一致的输出
            "max_tokens": 200,   # 限制输出长度，避免冗长的文本回复
        }

        print(f"[DEBUG] [OpenAI兼容 图像] 请求: model={model_name}, aspect_ratio={aspect_ratio}, quality={quality}")
        if image_urls:
            print(f"[DEBUG] [OpenAI兼容 图像]   注意: 忽略 image_urls 参数（当前实现不支持）")
        print(f"[DEBUG] [OpenAI兼容 图像]   prompt 长度={len(prompt)}, 前100字: {prompt[:100]}...")

        for attempt in range(max_attempts):
            try:
                response = await self._post_json(url, payload)

                # 从chat响应中提取内容
                choices = response.get("choices", [])
                if choices:
                    content = choices[0].get("message", {}).get("content", "")
                    if content.strip():
                        print(f"[OpenAI兼容 图像] 图像生成成功，内容长度: {len(content)}")

                        # 检查是否包含图像URL（markdown格式）
                        import re
                        url_match = re.search(r'!\[.*?\]\((https?://[^\)]+)\)', content)
                        if url_match:
                            image_url = url_match.group(1)
                            print(f"[OpenAI兼容 图像] 发现图像URL，开始下载: {image_url[:80]}...")
                            b64_image = await self._download_image_as_base64(image_url)
                            if b64_image:
                                return [b64_image]
                            else:
                                print(f"[OpenAI兼容 图像] 图片下载失败")
                        else:
                            # 假设返回的是base64编码的图像数据
                            print(f"[OpenAI兼容 图像] 尝试作为base64数据处理")
                            return [content]
                    else:
                        print(f"[OpenAI兼容 图像] 响应内容为空")
                else:
                    print(f"[OpenAI兼容 图像] 响应中无choices")

                # 如果失败，等待后重试
                context_msg = f" ({error_context})" if error_context else ""
                print(f"[OpenAI兼容 图像] 第 {attempt + 1} 次尝试未成功{context_msg}")
                if attempt < max_attempts - 1:
                    await asyncio.sleep(retry_delay)

            except ClientError as e:
                # 4xx 客户端错误，立即失败不重试
                context_msg = f" ({error_context})" if error_context else ""
                print(f"[OpenAI兼容 图像] ❌ 客户端错误{context_msg}: {e}。不再重试。")
                return ["Error"]

            except Exception as e:
                context_msg = f" ({error_context})" if error_context else ""
                current_delay = min(retry_delay * (2 ** attempt), 60)
                print(
                    f"[OpenAI兼容 图像] 第 {attempt + 1} 次尝试失败{context_msg}: {e}。"
                    f"{current_delay}s 后重试..."
                )
                if attempt < max_attempts - 1:
                    await asyncio.sleep(current_delay)
                else:
                    print(f"[OpenAI兼容 图像] 全部 {max_attempts} 次尝试失败{context_msg}")

        return ["Error"]
