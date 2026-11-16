"""全库唯一的建议宽度。

官方 HeroUI 没有任何像素默认宽度，宽度全由外层容器给；官方文档示例里输入类组件
压倒性地写 max-w-xs（= 320px）。Qt 里没人撑的铺满型控件会缩成一条线，
所以补这一个数，只当 sizeHint，不当最小宽度，用户设宽直接生效。
"""

SUGGESTED_WIDTH = 320

__all__ = ["SUGGESTED_WIDTH"]
