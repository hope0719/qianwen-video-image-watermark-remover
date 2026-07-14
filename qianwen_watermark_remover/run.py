#!/usr/bin/env python3
"""
千问图片去水印 — 命令行工具

用法:
  python run.py <千问分享链接> [输出目录]

示例:
  python run.py "https://activity.qianwen.com/r/ai-studio-mobile/qwen-external-share?shareId=xxx"
  python run.py "https://www.qianwen.com/share/chat/abc123?biz_id=ai_qwen" ./my_images
"""

import asyncio
import sys
import os

# 确保能 import 同目录下的模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from qianwen_remover import parse_qianwen, download_images


async def main():
    if len(sys.argv) < 2:
        print("用法: python run.py <千问分享链接> [输出目录]")
        print()
        print("支持的链接格式:")
        print(
            "  1. https://activity.qianwen.com/r/ai-studio-mobile/qwen-external-share?shareId=..."
        )
        print("  2. https://www.qianwen.com/share/chat/{id}?biz_id=ai_qwen")
        sys.exit(1)

    url = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "./output"

    # 清除代理环境变量，避免沙箱代理干扰
    for key in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY"):
        os.environ.pop(key, None)

    print(f"正在解析链接: {url[:80]}...")

    try:
        images = await parse_qianwen(url)
    except Exception as e:
        print(f"解析失败: {e}")
        sys.exit(1)

    if not images:
        print("未找到图片")
        sys.exit(1)

    print(f"共找到 {len(images)} 张无水印图片\n")
    print("开始下载:")

    saved = download_images(images, output_dir=output_dir)

    print(f"\n完成！{len(saved)} 张图片已保存到: {output_dir}")


if __name__ == "__main__":
    asyncio.run(main())
