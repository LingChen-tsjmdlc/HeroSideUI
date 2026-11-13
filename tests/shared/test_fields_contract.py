"""输入类 Mixin 对宿主的要求：逐个宿主校验，而不是只测 Mixin 本身。"""

import ast
import inspect
import textwrap

import pytest

from hero_side_ui import DateInput, Input, NumberInput, TimeInput
from hero_side_ui._shared.fields import InputLayoutMixin, InputStylingMixin


def host_requirements(mixin: type) -> dict[str, set[str]]:
    """返回 Mixin 每个方法读取、但 Mixin 自身没有定义或赋值的 self 属性。"""
    cls = ast.parse(textwrap.dedent(inspect.getsource(mixin))).body[0]
    methods = [n for n in cls.body if isinstance(n, ast.FunctionDef)]
    defined = {m.name for m in methods}

    def self_attrs(tree, ctx):
        return {
            n.attr
            for n in ast.walk(tree)
            if isinstance(n, ast.Attribute)
            and isinstance(n.value, ast.Name)
            and n.value.id == "self"
            and isinstance(n.ctx, ctx)
        }

    assigned = self_attrs(cls, ast.Store)
    return {m.name: self_attrs(m, ast.Load) - defined - assigned for m in methods}


@pytest.mark.parametrize("mixin", [InputLayoutMixin, InputStylingMixin])
@pytest.mark.parametrize("factory", [Input, NumberInput, DateInput, TimeInput])
def test_host_provides_attributes_read_by_inherited_mixin_methods(qtbot, factory, mixin):
    if not issubclass(factory, mixin):
        pytest.skip("host does not use this mixin")
    host = factory(label="label")
    qtbot.addWidget(host)

    missing = []
    for method, attrs in host_requirements(mixin).items():
        owner = next(c for c in type(host).__mro__ if method in vars(c))
        if owner is not mixin:
            continue
        missing += [f"{method} needs {a}" for a in sorted(attrs) if not hasattr(host, a)]
    assert not missing, f"{factory.__name__} breaks the {mixin.__name__} contract: {missing}"


def test_requirement_scan_lists_host_attributes():
    needs = set().union(*host_requirements(InputLayoutMixin).values())
    assert {"_wrapper", "_inside_label", "_label_anim"} <= needs
