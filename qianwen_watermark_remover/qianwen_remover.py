"""
千问图片去水印解析器
支持两种链接格式：
  1. activity.qianwen.com 分享链接
  2. www.qianwen.com/share/chat 对话链接
"""

import re
import json
import os
import subprocess
from typing import Optional

import httpx


# ─── activity.qianwen.com 链接解析 ───────────────────────────


async def parse_activity_link(url: str) -> list[dict]:
    """
    解析 activity.qianwen.com/r/ai-studio-mobile/qwen-external-share 格式的链接。

    原理：GET 请求页面，从 SSR 渲染的 __INITIAL_PROPS__ 中提取图片数据。
    无水印字段：images[].url
    带水印字段：images[].downloadUrl（切勿使用）
    """
    headers = {
        "origin": "https://activity.qianwen.com",
        "user-agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/146.0.0.0 Safari/537.36 Edg/146.0.0.0"
        ),
    }

    async with httpx.AsyncClient(follow_redirects=True) as client:
        response = await client.get(url, headers=headers)
        html = response.text

    match = re.search(r"window\.__INITIAL_PROPS__\s*=\s*(\{.*?\});", html, re.DOTALL)
    if not match:
        raise ValueError("无法从页面中提取 __INITIAL_PROPS__ 数据，链接可能已失效")

    props = json.loads(match.group(1))
    data = props["initialData"]["data"]

    title = data.get("title", "未知")
    images_raw = data.get("images", [])

    # 主图也加入列表（如果不在 images 中）
    main_image = data.get("image", {})
    if main_image and main_image.get("url"):
        if not any(img.get("url") == main_image.get("url") for img in images_raw):
            images_raw.insert(0, main_image)

    result = []
    for img in images_raw:
        result.append(
            {
                "url": img["url"],  # 无水印
                "width": img.get("width"),
                "height": img.get("height"),
                "title": title,
            }
        )

    return result


# ─── www.qianwen.com/share/chat 链接解析 ─────────────────────


async def parse_share_chat_link(url: str) -> list[dict]:
    """
    解析 www.qianwen.com/share/chat/{share_id} 格式的链接。

    原理：POST 调用 chat2-api.qianwen.com/api/v1/share/info 获取对话数据，
    从 response_messages 中找到 multi_load/iframe 类型消息，
    再从 display_list 中提取 image 字段（无水印）。
    带水印字段：display_list[].watermark_image（切勿使用）
    """
    # 从 URL 中提取 share_id
    match = re.search(r"/share/chat/([a-f0-9]+)", url)
    if not match:
        raise ValueError("无法从链接中提取 share_id")
    share_id = match.group(1)

    headers = {
        "origin": "https://www.qianwen.com",
        "user-agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/146.0.0.0 Safari/537.36 Edg/146.0.0.0"
        ),
    }
    json_data = {"share_id": share_id, "biz_id": "ai_qwen"}

    async with httpx.AsyncClient() as client:
        api_url = "https://chat2-api.qianwen.com/api/v1/share/info"
        response = await client.post(api_url, json=json_data, headers=headers)
        data = response.json()

    records = data["data"]["session"]["record_list"]

    image_list = []
    for record in records:
        for msg in record.get("response_messages", []):
            if msg.get("mime_type") != "multi_load/iframe":
                continue

            multi_load = msg["meta_data"]["multi_load"]
            for item in multi_load:
                display_list = item.get("content", {}).get("display_list", [])
                for d in display_list:
                    if "image" in d and d["image"]:
                        for img in d["image"]:
                            image_list.append(
                                {
                                    "url": img["url"],  # 无水印
                                    "width": img.get("width"),
                                    "height": img.get("height"),
                                    "title": item.get("content", {}).get(
                                        "prompt", "未知"
                                    ),
                                }
                            )

    return image_list


# ─── 自动识别 + 下载 ──────────────────────────────────────────


def detect_link_type(url: str) -> str:
    """自动识别链接类型"""
    if "activity.qianwen.com" in url:
        return "activity"
    elif "qianwen.com/share/chat" in url:
        return "share_chat"
    else:
        raise ValueError(f"不支持的链接格式: {url}")


async def parse_qianwen(url: str) -> list[dict]:
    """
    自动识别链接格式并解析无水印图片。
    返回 [{"url": ..., "width": ..., "height": ..., "title": ...}, ...]
    """
    link_type = detect_link_type(url)
    if link_type == "activity":
        return await parse_activity_link(url)
    else:
        return await parse_share_chat_link(url)


def download_images(
    images: list[dict],
    output_dir: str = "./output",
    prefix: str = "qianwen",
) -> list[str]:
    """
    下载无水印图片到本地。
    返回已下载文件的路径列表。
    """
    os.makedirs(output_dir, exist_ok=True)
    saved = []

    for i, img in enumerate(images):
        url = img["url"]
        ext = "png" if ".png" in url else "jpg"
        filename = f"{prefix}_no_watermark_{i + 1}.{ext}"
        filepath = os.path.join(output_dir, filename)

        subprocess.run(
            ["curl", "-s", "--noproxy", "*", "-o", filepath, url],
            capture_output=True,
        )

        size = os.path.getsize(filepath) if os.path.exists(filepath) else 0
        w, h = img.get("width", "?"), img.get("height", "?")
        status = "成功" if size > 1000 else "失败"
        print(f"  图片 {i + 1}: {filename} | {w}x{h} | {size / 1024:.1f} KB | {status}")
        saved.append(filepath)

    return saved
