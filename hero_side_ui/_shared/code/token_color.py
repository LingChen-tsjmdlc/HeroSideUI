"""pygments token 到语法配色的映射，供代码展示与代码编辑共用。"""


def token_color(ttype, syntax: dict[str, str]) -> str:
    """把 pygments token 类型映射到语义色。

    Args:
        ttype: pygments token 类型。
        syntax: 主题的语法配色字典。

    Returns:
        对应语义键的十六进制色；未命中时返回 text 色。
    """
    from pygments.token import (
        Comment,
        Error,
        Keyword,
        Name,
        Number,
        Operator,
        Punctuation,
        String,
        Token,
    )

    if ttype in Comment:
        return syntax["comment"]
    if ttype in String:
        return syntax["string"]
    if ttype in Number:
        return syntax["number"]
    if ttype in Keyword:
        return syntax["keyword"]
    if ttype in Name.Function:
        return syntax["function"]
    if ttype in Name.Class:
        return syntax["class"]
    if ttype in Name.Decorator:
        return syntax["decorator"]
    if ttype in Name.Builtin:
        return syntax["builtin"]
    if ttype in Name.Constant:
        return syntax["constant"]
    if ttype in Operator:
        return syntax["operator"]
    if ttype in Punctuation:
        return syntax["punctuation"]
    if ttype in Error:
        return syntax["error"]
    if ttype in Name:
        return syntax["name"]
    if ttype in Token:
        return syntax["text"]
    return syntax["text"]
