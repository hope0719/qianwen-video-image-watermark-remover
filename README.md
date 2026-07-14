# 千问图片去水印（Qianwen Watermark Remover）

> 从千问（Qwen）的分享链接中直接提取**无水印原图**的轻量工具。

## 这是什么

千问在生成 / 分享图片时，分享页面会**同时返回「带水印」和「无水印」两个版本**的图片地址。本工具的作用就是跳过水印版本，直接抓取无水印原图的真实地址并下载到本地 —— 全程不需要任何 AI 模型或人工擦除。

支持两种分享链接格式：

- `activity.qianwen.com/r/...`（活动 / 外部分享页）
- `www.qianwen.com/share/chat/...`（对话分享页）

## 工作原理（简述）

千问返回的图片数据里同时带了两个字段，我们只需取「无水印」那一个：

| 链接格式 | 无水印字段（用它） | 带水印字段（别用） |
| --- | --- | --- |
| activity 分享页 | `images[].url` | `images[].downloadUrl` |
| 对话分享页 | `display_list[].image` | `display_list[].watermark_image` |

工具会自动识别链接类型，定位无水印字段并下载。

## 安装

```bash
git clone https://github.com/hope0719/qianwen-watermark-remover.git
cd qianwen-watermark-remover
pip install -r qianwen_watermark_remover/requirements.txt
```

依赖只有一个：`httpx`。

## 使用

### 命令行

```bash
python qianwen_watermark_remover/run.py "<千问分享链接>" [输出目录]
```

示例：

```bash
# activity 链接
python qianwen_watermark_remover/run.py "https://activity.qianwen.com/r/ai-studio-mobile/qwen-external-share?shareId=xxx"

# 对话分享链接，并指定输出目录
python qianwen_watermark_remover/run.py "https://www.qianwen.com/share/chat/abc123?biz_id=ai_qwen" ./my_images
```

### 作为库调用

```python
import asyncio
from qianwen_watermark_remover import parse_qianwen, download_images

async def main():
    images = await parse_qianwen("<千问分享链接>")
    print(f"找到 {len(images)} 张无水印图片")
    download_images(images, output_dir="./output")

asyncio.run(main())
```

## 目录结构

```
qianwen-watermark-remover/
├── README.md                       # 本说明
├── .gitignore
└── qianwen_watermark_remover/
    ├── __init__.py                 # 包入口（导出核心函数）
    ├── qianwen_remover.py          # 核心解析模块（两种链接格式）
    ├── run.py                      # 命令行入口
    ├── requirements.txt            # 依赖
    └── README.md                   # 模块级说明
```

## 注意事项

- 无水印图片 URL 带 `auth_key` 时效参数，过期后无法下载，请尽快保存。
- 仅支持图片，暂不支持视频。
- 仅供学习交流使用，请遵守千问平台相关协议，勿用于侵权用途。
