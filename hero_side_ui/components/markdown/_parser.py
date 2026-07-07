"""markdown-it-py 封装：Markdown 文本 → SyntaxTreeNode 树。

启用 CommonMark + GFM 表格 + 删除线 + 脚注 + 任务列表。表格/删除线为内置规则，
脚注 / 任务列表来自 mdit_py_plugins（可选依赖）：未安装时静默降级，相应标记按
纯文本呈现，其余语法照常，绝不因缺插件崩溃。

只做解析，不碰任何 Qt 对象。
"""

from __future__ import annotations

from markdown_it import MarkdownIt
from markdown_it.tree import SyntaxTreeNode


def _build_parser() -> MarkdownIt:
    """构造解析器：CommonMark 基础 + 表格 + 删除线 + 脚注 + 任务列表，关闭原始 html 透传。"""
    md = MarkdownIt("commonmark")
    md.enable(["table", "strikethrough"])
    try:
        from mdit_py_plugins.footnote import footnote_plugin

        md.use(footnote_plugin)
    except Exception:
        pass  # 未装 mdit_py_plugins：脚注降级为纯文本，其余不受影响
    try:
        from mdit_py_plugins.tasklists import tasklists_plugin

        md.use(tasklists_plugin)
    except Exception:
        pass  # 未装插件：任务列表降级为普通列表
    # 不渲染用户内嵌的原始 HTML —— 避免把 <script> 之类直接塞进富文本
    md.options["html"] = False
    return md


_PARSER = _build_parser()


def parse(text: str) -> SyntaxTreeNode:
    """把 Markdown 文本解析为 SyntaxTreeNode 根节点。"""
    tokens = _PARSER.parse(text or "")
    return SyntaxTreeNode(tokens)


__all__ = ["parse"]
