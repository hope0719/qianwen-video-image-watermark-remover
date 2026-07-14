"""
千问视频图片去水印解析器
支持两种链接格式：
  1. activity.qianwen.com 分享链接（图片 + 视频）
  2. www.qianwen.com/share/chat 对话链接（图片 + 视频）

原理：千问在返回媒体数据时，会同时给出「带水印」和「无水印」两个版本。
本工具直接取无水印字段下载即可：
  - 图片无水印字段：images[].url / display_list[].image
  - 视频无水印字段：playInfo.url / display_list[].video
  - （切勿使用 downloadUrl / watermark_image / download_video 等带水印字段）
"""

import re
import json
import os
import subprocess

import httpx


# ─── activity.qianwen.com 链接解析 ───────────────────────────


async def parse_activity_link(url: str) -> dict:
    """
    解析 activity.qianwen.com/r/ai-studio-mobile/qwen-external-share 格式的链接。

    原理：GET 请求页面，从 SSR 渲染的 __INITIAL_PROPS__ 中提取数据。
    图片无水印字段：images[].url（非 downloadUrl）
    视频无水印字段：playInfo.url（非 downloadUrl）

    返回 {"title": ..., "images": [...], "videos": [...]}
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
    result = {"title": title, "images": [], "videos": []}

    # 提取图片（url 字段为无水印，downloadUrl 为有水印）
    images_raw = data.get("images") or []
    main_image = data.get("image") or {}
    if main_image and main_image.get("url"):
        if not any(img.get("url") == main_image.get("url") for img in images_raw):
            images_raw.insert(0, main_image)

    for img in images_raw:
        result["images"].append(
            {
                "url": img["url"],
                "width": img.get("width"),
                "height": img.get("height"),
            }
        )

    # 提取视频（playInfo.url 为无水印，downloadUrl 为有水印）
    play_info = data.get("playInfo") or {}
    if play_info.get("url"):
        result["videos"].append(
            {
                "url": play_info["url"],
                "width": play_info.get("videoWidth"),
                "height": play_info.get("videoHeight"),
            }
        )

    return result


# ─── www.qianwen.com/share/chat 链接解析 ─────────────────────


async def parse_share_chat_link(url: str) -> dict:
    """
    解析 www.qianwen.com/share/chat/{share_id} 格式的链接。

    原理：POST 调用 chat2-api.qianwen.com/api/v1/share/info 获取对话数据，
    从 response_messages 中找到 multi_load/iframe 类型消息，
    再从 display_list 中提取 image 字段（图片无水印）和 video 字段（视频无水印）。
    带水印字段：watermark_image / download_video（切勿使用）

    返回 {"title": ..., "images": [...], "videos": [...]}
    """
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
    result = {"title": "未知", "images": [], "videos": []}

    for record in records:
        for msg in record.get("response_messages", []):
            if msg.get("mime_type") != "multi_load/iframe":
                continue

            multi_load = msg["meta_data"]["multi_load"]
            for item in multi_load:
                content = item.get("content", {})
                prompt = content.get("prompt", "未知")
                if result["title"] == "未知":
                    result["title"] = prompt

                display_list = content.get("display_list", [])
                for d in display_list:
                    # 图片：image 字段为无水印
                    if "image" in d and d["image"]:
                        for img in d["image"]:
                            result["images"].append(
                                {
                                    "url": img["url"],
                                    "width": img.get("width"),
                                    "height": img.get("height"),
                                }
                            )

                    # 视频：video 字段为无水印，download_video 为有水印
                    if "video" in d and d["video"]:
                        for vid in d["video"]:
                            result["videos"].append(
                                {
                                    "url": vid["url"],
                                    "width": None,
                                    "height": None,
                                }
                            )

    return result


# ─── 自动识别 + 下载 ──────────────────────────────────────────


def detect_link_type(url: str) -> str:
    """自动识别链接类型"""
    if "activity.qianwen.com" in url:
        return "activity"
    elif "qianwen.com/share/chat" in url:
        return "share_chat"
    else:
        raise ValueError(f"不支持的链接格式: {url}")


async def parse_qianwen(url: str) -> dict:
    """
    自动识别链接格式并解析无水印图片和视频。
    返回 {"title": ..., "images": [...], "videos": [...]}
    """
    link_type = detect_link_type(url)
    if link_type == "activity":
        return await parse_activity_link(url)
    else:
        return await parse_share_chat_link(url)


def download_media(
    result: dict,
    output_dir: str = "./output",
    prefix: str = "qianwen",
) -> list[str]:
    """
    下载无水印图片和视频到本地。
    返回已下载文件的路径列表。
    """
    os.makedirs(output_dir, exist_ok=True)
    saved = []

    # 下载图片
    for i, img in enumerate(result["images"]):
        url = img["url"]
        ext = "png" if ".png" in url else "jpg"
        filename = f"{prefix}_image_{i + 1}.{ext}"
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

    # 下载视频
    for i, vid in enumerate(result["videos"]):
        url = vid["url"]
        filename = f"{prefix}_video_{i + 1}.mp4"
        filepath = os.path.join(output_dir, filename)
        subprocess.run(
            ["curl", "-s", "--noproxy", "*", "-o", filepath, url],
            capture_output=True,
        )
        size = os.path.getsize(filepath) if os.path.exists(filepath) else 0
        status = "成功" if size > 10000 else "失败"
        print(f"  视频 {i + 1}: {filename} | {size / 1024 / 1024:.2f} MB | {status}")
        saved.append(filepath)

    return saved
