# 千问视频图片去水印工具

从千问（Qwen）分享链接中提取无水印原图与原视频。

## 原理

千问在返回媒体数据时会同时给出无水印和带水印两个版本，本工具直接取无水印字段：

| 链接格式 | 数据获取方式 | 图片无水印字段 | 视频无水印字段 | 带水印字段（勿用） |
|---|---|---|---|---|
| `activity.qianwen.com/r/...` | GET 页面，从 SSR `__INITIAL_PROPS__` 提取 | `images[].url` | `playInfo.url` | `downloadUrl` 系列 |
| `www.qianwen.com/share/chat/...` | POST `chat2-api.qianwen.com/api/v1/share/info` | `display_list[].image` | `display_list[].video` | `watermark_image` / `download_video` |

## 依赖

```bash
pip install httpx
```

## 使用

### 命令行

```bash
python run.py <千问分享链接> [输出目录]
```

示例：

```bash
# activity 链接
python run.py "https://activity.qianwen.com/r/ai-studio-mobile/qwen-external-share?shareId=xxx"

# share/chat 链接
python run.py "https://www.qianwen.com/share/chat/abc123?biz_id=ai_qwen" ./my_images
```

### 作为库调用

```python
import asyncio
from qianwen_remover import parse_qianwen, download_media

async def main():
    result = await parse_qianwen(url)  # 自动识别链接格式，返回 {"title","images","videos"}
    print(f"找到 {len(result['images'])} 张图片, {len(result['videos'])} 个视频")

    # 仅获取 URL，不下载
    for img in result["images"]:
        print(f"  {img['width']}x{img['height']} | {img['url'][:80]}...")

    # 下载到本地（图片 + 视频）
    download_media(result, output_dir="./output")

asyncio.run(main())
```

## 文件说明

```
qianwen_watermark_remover/
├── qianwen_remover.py   # 核心解析模块（图片 + 视频，两种链接格式的解析逻辑）
├── run.py               # 命令行入口
├── requirements.txt     # 依赖
├── __init__.py          # 包导出
└── README.md            # 本文件
```

## 注意事项

- 媒体 URL 中包含 `auth_key` 参数，有时效性，过期后无法下载。
- 视频直接保存为 `.mp4`，无需额外转码。
- 仅供学习交流使用。
