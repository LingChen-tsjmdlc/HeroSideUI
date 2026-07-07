"""CodeBlock 组件示例 —— 语法高亮 / 标题栏 / 复制按钮 / 自动换行 / 多 tab / 行高亮。"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QVBoxLayout

from hero_side_ui import CodeBlock
from _base import DemoBase


PY_CODE = '''import asyncio


async def fetch(url: str) -> dict:
    """拉取远程 JSON。"""
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            return await resp.json()


# 入口
if __name__ == "__main__":
    data = asyncio.run(fetch("https://api.example.com/data"))
    print(data)
'''

JSON_CODE = '''{
  "firstName": "John",
  "lastName": "Smith",
  "age": 25,
  "roles": ["admin", "editor"]
}'''

CSS_CODE = '''.code-block {
  border-radius: 16px;
  background: #1d1f21;
  padding: 12px 16px;
}'''

TS_CODE = '''type CodeBlockProps = {
  language: string;
  filename?: string;
};

export const CodeBlock = ({ language, filename }: CodeBlockProps) => {
  const [copied, setCopied] = useState(false);
  return <div className="rounded-2xl" />;
};'''


class CodeBlockDemo(DemoBase):
    component_name = "CodeBlock"

    def build_content(self, layout: QVBoxLayout, labels_bag: list):
        layout.addWidget(self._section_title("基础（Python，带文件名 + 行号）"))
        layout.addWidget(CodeBlock(PY_CODE, language="python", filename="fetch.py"))

        layout.addWidget(self._section_title("行高亮（第 4~6 行）"))
        layout.addWidget(
            CodeBlock(PY_CODE, language="python", filename="highlight.py", highlight_lines=[4, 5, 6])
        )

        layout.addWidget(self._section_title("JSON（无文件名，显示语言名）"))
        layout.addWidget(CodeBlock(JSON_CODE, language="json"))

        layout.addWidget(self._section_title("自定义字号（font_size=18）"))
        layout.addWidget(CodeBlock(PY_CODE, language="python", filename="big.py", font_size=18))

        layout.addWidget(self._section_title("多 Tab 切换"))
        layout.addWidget(
            CodeBlock(
                tabs=[
                    {"name": "component.tsx", "code": TS_CODE, "language": "typescript"},
                    {"name": "style.css", "code": CSS_CODE, "language": "css"},
                    {"name": "data.json", "code": JSON_CODE, "language": "json"},
                ]
            )
        )


if __name__ == "__main__":
    CodeBlockDemo.run()
