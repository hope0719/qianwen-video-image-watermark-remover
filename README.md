# 千问视频图片去水印（Qianwen Video & Image Watermark Remover）

> 从千问（Qwen）的分享链接中直接提取**无水印原图与原视频**的轻量工具。

## 这是什么

千问在生成 / 分享图片或视频时，分享页面会同时返回「带水印」和「无水印」两个版本。本工具的作用就是绕过水印版本，直接抓取无水印原图的真实地址并下载到本地——**图片、视频都能去水印**，无需任何 AI 模型或人工处理。

支持两种分享链接格式：
- `activity.qianwen.com/r/...`（活动 / 外部分享页）
- `www.qianwen.com/share/chat/...`（对话分享页）

## 工作原理（简述）

千问返回的媒体数据里同时带了两个字段，本工具自动识别链接类型，取「无水印」字段下载即可：

| 链接格式 | 图片无水印字段（用它） | 视频无水印字段（用它） | 带水印字段（别用） |
|---|---|---|---|
| activity 分享页 | `images[].url` | `playInfo.url` | `images[].downloadUrl` / `playInfo.downloadUrl` |
| 对话分享页 | `display_list[].image` | `display_list[].video` | `watermark_image` / `download_video` |

## 安装

```bash
git clone https://github.com/hope0719/qianwen-video-image-watermark-remover.git
cd qianwen-video-image-watermark-remover
pip install -r qianwen_watermark_remover/requirements.txt
```

依赖仅一个：`httpx`。

## 使用

命令行：

```bash
python qianwen_watermark_remover/run.py "<千问分享链接>" [输出目录]
```

示例：

```bash
# activity 链接（图片 + 视频混合）
python qianwen_watermark_remover/run.py "https://activity.qianwen.com/r/ai-studio-mobile/qwen-external-share?shareId=xxx"

# 对话分享链接，指定输出目录
python qianwen_watermark_remover/run.py "https://www.qianwen.com/share/chat/abc123?biz_id=ai_qwen" ./my_output
```

作为库调用：

```python
import asyncio
from qianwen_watermark_remover import parse_qianwen, download_media

async def main():
    result = await parse_qianwen("<千问分享链接>")  # 自动识别链接格式
    print(f"标题: {result['title']}")
    print(f"图片 {len(result['images'])} 张, 视频 {len(result['videos'])} 个")

    # 直接拿 URL（不下载）
    for img in result["images"]:
        print(f"  图片 {img['width']}x{img['height']} | {img['url'][:80]}...")

    # 下载到本地
    download_media(result, output_dir="./output")

asyncio.run(main())
```

## 目录结构

```
qianwen-video-image-watermark-remover/
├── README.md                       # 本说明
├── .gitignore
└── qianwen_watermark_remover/
    ├── qianwen_remover.py          # 核心解析模块（图片 + 视频，两种链接格式）
    ├── run.py                      # 命令行入口
    ├── requirements.txt            # 依赖
    ├── __init__.py                 # 包导出
    └── README.md                   # 模块级说明
```

## 注意事项

- 无水印媒体 URL 带 `auth_key` 时效参数，过期后无法下载，请尽快保存。
- 视频直接下载为 `.mp4`，无需额外转码（已是无水印源文件）。
- 仅供学习交流使用，请遵守千问平台相关协议，勿用于侵权用途。
