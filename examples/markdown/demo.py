"""Markdown 组件示例 —— 覆盖 markdown.com.cn 速查表全部语法 + 自定义渲染。

分三块：
1. 基础语法：标题 / 段落换行 / 粗斜删粗斜体 / 引用(含嵌套) / 有序无序嵌套列表 /
   行内代码 / 分隔线 / 链接(行内·自动·引用式) / 图片。
2. 扩展语法：表格(列对齐, 走 Table 组件) / 围栏代码块 / 任务列表 / 脚注(角标 hover
   Tooltip + 底部定义列表) / 定义列表 / 转义字符。
3. 自定义渲染：inline_overrides 行内 HTML / block_renderers 块级 widget /
   inline_styles 声明式行内样式（连续框选）。

解析器启用 commonmark + table + strikethrough + footnote。任务列表 / 定义列表
属其它扩展插件，未启用时按纯文本呈现，此处一并写入用于观察真实渲染。
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from hero_side_ui import Button, Card, CardBody, Markdown
from _base import DemoBase


BASIC = """# 一级标题 H1

## 二级标题 H2

### 三级标题 H3

#### 四级标题 H4

##### 五级标题 H5

###### 六级标题 H6

这是一个普通段落。段落之间用空行分隔。
这一行与上一行之间只有软换行，会被合并到同一段。

若要强制换行，在行尾加两个空格：  
这一行就换行了。

**粗体文本**、*斜体文本*、***粗体加斜体***、~~删除线文本~~，
以及行内代码 `pip install herosideui`。

> 这是一段引用块。
>
> 引用块内可以有 **粗体** 与多段落。
>
> > 这是嵌套的二级引用块。

---

无序列表：

- 第一项
- 第二项，带 `code`
- 第三项
  - 嵌套子项 A
  - 嵌套子项 B
    - 更深一层

有序列表：

1. 第一步
2. 第二步
   1. 子步骤 2.1
   2. 子步骤 2.2
3. 第三步

有序 / 无序混合嵌套：

1. 外层有序第一项
   - 内层无序 A
   - 内层无序 B
2. 外层有序第二项

链接：

- 行内链接：[HeroSideUI 仓库](https://github.com/LingChen-tsjmdlc/HeroSideUI)
- 自动链接：<https://markdown.com.cn>
- 引用式链接：[Markdown 教程][md]

[md]: https://markdown.com.cn "Markdown 中文教程"

图片：

![占位图片示例](https://myoctocat.com/assets/images/base-octocat.svg)
"""

EXTENDED = """## 扩展语法

### 表格（列对齐：左 / 居中 / 右）

| 名称 | 角色 | 状态 |
| :--- | :--: | ---: |
| Tony | CEO | Active |
| Sarah | CTO | Active |
| Mike | 设计 | Paused |

### 围栏代码块（带语言标记）

```python
def hello(name: str) -> str:
    return f"Hello, {name}!"
```

```json
{
  "firstName": "John",
  "lastName": "Smith",
  "age": 25
}
```

### 任务列表

- [x] 已完成的任务
- [ ] 待办任务一
- [ ] 待办任务二

### 脚注

这是一句带脚注的话[^1]，脚注引用是可 hover 的上标角标[^2]。

[^1]: 这里是第一条脚注的内容，鼠标悬停角标即可看到。
[^2]: 第二条脚注：脚注定义会汇总到文档底部。

### 定义列表

术语
: 术语的定义内容

### 转义字符

使用反斜杠转义：\\*这段不会变成斜体\\*，\\`这不是代码\\`。
"""

SAMPLE_2 = """## 动态更新后的内容

`set_markdown()` 调用后整树重建。

- 列表项一
- 列表项二

> 引用块也在。
"""

CUSTOM = """## 自定义渲染示例

这段正文里的 **粗体被改成了红色**、*斜体被改成了紫色*，
还有一个 [绿色链接](https://github.com/LingChen-tsjmdlc/HeroSideUI)。

> 这个引用块被换成了一个 Card 外壳。
>
> 内部内容仍由默认渲染器生成。
"""

STYLE_SAMPLE = """## inline_styles 声明式样式

这段正文包含 **粗体**、*斜体*、~~删除线~~、行内代码 `uv sync`，
还有一个 [HeroSideUI 链接](https://github.com/LingChen-tsjmdlc/HeroSideUI)。

一次配置样式，全程连续框选、可复制——不拆任何 widget。
"""


def _build_custom_md() -> Markdown:
    # ① 行内 override：返回 HTML 片段（行内随文字流动，只能改样式不能换 widget）
    # 自行拼 HTML 时必须补齐该格式的固有样式（em 的 font-style:italic、
    # strong 的 font-weight），否则只改颜色会把斜体/加粗一起丢掉。
    inline_overrides = {
        "strong": lambda c: f"<span style='color:#f31260; font-weight:700'>{c.children}</span>",
        "em": lambda c: f"<span style='color:#7828c8; font-style:italic'>{c.children}</span>",
        "link": lambda c: f"<a href='{c.href}' style='color:#17c964'>{c.children}</a>",
    }

    # ② 块级 override：返回任意 QWidget（块级独占整行，可整块替换）
    def quote_as_card(ctx):
        card = Card(parent=ctx.parent)
        body = CardBody()
        for child in ctx.render_children(body):   # 插槽 children
            body.layout().addWidget(child)
        card.add_body(body)
        return card

    return Markdown(
        CUSTOM,
        inline_overrides=inline_overrides,
        block_renderers={"blockquote": quote_as_card},
    )


class MarkdownDemo(DemoBase):
    component_name = "Markdown"

    def build_content(self, layout: QVBoxLayout, labels_bag: list):
        self._md = Markdown(BASIC)

        # 切换内容按钮，验证 set_markdown 动态重建
        bar = QWidget()
        bar_lay = QHBoxLayout(bar)
        bar_lay.setContentsMargins(0, 0, 0, 0)
        bar_lay.setSpacing(12)
        btn_a = Button("完整文档", color="primary")
        btn_b = Button("简短内容", color="secondary")
        btn_a.clicked.connect(lambda: self._md.set_markdown(BASIC))
        btn_b.clicked.connect(lambda: self._md.set_markdown(SAMPLE_2))
        bar_lay.addWidget(btn_a)
        bar_lay.addWidget(btn_b)
        bar_lay.addStretch()

        layout.addWidget(self._section_title("基础语法全覆盖"))
        layout.addWidget(bar)
        layout.addWidget(self._md)

        layout.addWidget(self._section_title("扩展语法（表格 / 代码块 / 任务列表 / 脚注 / 定义列表 / 转义）"))
        layout.addWidget(Markdown(EXTENDED))

        layout.addWidget(self._section_title("自定义渲染（行内样式 + 块级 widget）"))
        layout.addWidget(_build_custom_md())

        layout.addWidget(
            self._section_title("inline_styles 声明式行内样式（连续框选）")
        )
        layout.addWidget(
            Markdown(
                STYLE_SAMPLE,
                inline_styles={
                    "strong": {"color": "danger"},
                    "em": {"color": "secondary"},
                    "code": {"bg": "primary-100", "fg": "primary-700"},
                    "link": {"color": "success", "underline": "always"},
                },
            )
        )


if __name__ == "__main__":
    MarkdownDemo.run()
