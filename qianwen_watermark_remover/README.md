# 千问图片去水印工具

从千问（Qwen）分享链接中提取无水印原图。

## 原理

千问在返回图片数据时会同时给出无水印和带水印两个版本的 URL，本工具直接取无水印字段：

| 链接格式 | 数据获取方式 | 无水印字段 | 带水印字段（勿用） |
|---|---|---|---|
| `activity.qianwen.com/r/...` | GET 页面，从 SSR `__INITIAL_PROPS__` 提取 | `images[].url` | `images[].downloadUrl` |
| `www.qianwen.com/share/chat/...` | POST `chat2-api.qianwen.com/api/v1/share/info` | `display_list[].image` | `display_list[].watermark_image` |

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
from qianwen_remover import parse_qianwen, download_images

async def main():
    url = "https://www.qianwen.com/share/chat/xxx"
    images = await parse_qianwen(url)  # 自动识别链接格式
    print(f"找到 {len(images)} 张无水印图片")

    # 仅获取 URL，不下载
    for img in images:
        print(f"  {img['width']}x{img['height']} | {img['url'][:80]}...")

    # 下载到本地
    download_images(images, output_dir="./output")

asyncio.run(main())
```

## 文件说明

```
qianwen_watermark_remover/
├── qianwen_remover.py   # 核心解析模块（两种链接格式的解析逻辑）
├── run.py               # 命令行入口
└── README.md            # 本文件
```

## 注意事项

- 图片 URL 中包含 `auth_key` 参数，有时效性，过期后无法下载。
- 仅支持图片，暂不支持视频。
- 仅供学习交流使用。
