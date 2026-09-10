"""Drawer 组件测试"""

from __future__ import annotations

import pytest
from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication, QPushButton, QWidget

from hero_side_ui import Drawer


@pytest.fixture
def host(qtbot) -> QWidget:
    """宿主窗口（不 show，避免测试期间弹真实窗口）。"""
    w = QWidget()
    qtbot.addWidget(w)
    w.resize(800, 600)
    return w


def _add_fixed(d: Drawer, w: int, h: int) -> QWidget:
    """塞一块固定尺寸的子 widget，让面板 sizeHint 确定（w+48, h+48）。"""
    box = QWidget()
    box.setFixedSize(w, h)
    d.add_widget(box)
    return box


def _make(host: QWidget, **kw) -> Drawer:
    """默认关掉动画 —— 断言只关心终态，不引入动画时序。"""
    kw.setdefault("disable_animation", True)
    return Drawer(host=host, **kw)


def _press(widget: QWidget, pos: QPoint) -> None:
    """在 widget 上派发一次左键按下（不依赖窗口可见性与命中测试）。"""
    ev = QMouseEvent(
        QEvent.Type.MouseButtonPress,
        QPointF(pos),
        QPointF(pos),  # globalPos（与 localPos 同值即可，测试不关心屏幕坐标）
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    QApplication.sendEvent(widget, ev)


def test_defaults(host):
    d = Drawer(host=host)
    assert d.size() == "md"
    assert d.radius() == "lg"
    assert d.placement() == "right"
    assert d.is_open() is False
    assert d.is_dismissable() is True
    assert d.is_keyboard_dismiss_disabled() is False
    assert d.disable_animation() is False
    assert d.backdrop() == "opaque"
    assert d.isHidden() is True


@pytest.mark.parametrize(
    "kw",
    [
        {"size": "6xl"},
        {"radius": "xl"},
        {"placement": "center"},
        {"backdrop": "frost"},
        {"size": 0},
        {"size": -10},
        {"size": True},
        {"size": None},
        {"size": 1.5j},
    ],
)
def test_invalid_tokens_raise(host, kw):
    with pytest.raises(ValueError):
        Drawer(host=host, **kw)


def test_opens_on_construct_when_is_open(host):
    d = _make(host, is_open=True)
    assert d.is_open() is True
    assert d.isHidden() is False


@pytest.mark.parametrize(
    "placement,expected",
    [
        ("left", (0, 0, 448, 600)),    # 宽度固定为档位（内容宽 hint 348 < 448 也不缩）
        ("right", (352, 0, 448, 600)),
        ("top", (0, 0, 800, 248)),     # 高度内容自适应（内容 hint 248 < 448）
        ("bottom", (0, 352, 800, 248)),
    ],
)
def test_panel_geometry_by_placement(host, placement, expected):
    """左右抽屉宽度固定为 size 档；上下抽屉高度 = min(内容 hint, 档位, 宿主)。"""
    d = _make(host, placement=placement, size="md")
    _add_fixed(d, 300, 200)
    d.set_is_open(True)
    g = d._panel.geometry()
    assert (g.x(), g.y(), g.width(), g.height()) == expected


def test_size_caps_at_host(host):
    """5xl(1024) 超过宿主宽 800 时按宿主钳制。"""
    d = _make(host, size="5xl", placement="right")
    d.set_is_open(True)
    assert d._panel.width() == 800


def test_full_size_fills_host(host):
    d = _make(host, size="full")
    d.set_is_open(True)
    assert d._panel.geometry() == host.rect()


@pytest.mark.parametrize(
    "size,placement,expected",
    [
        (600, "right", (200, 0, 600, 600)),   # 数字 = 强制宽度（左右）
        (600, "left", (0, 0, 600, 600)),
        (200, "bottom", (0, 400, 800, 200)),  # 数字 = 强制高度（上下），不看内容
        (200, "top", (0, 0, 800, 200)),
        (1200, "right", (0, 0, 800, 600)),    # 超过宿主按宿主钳制
    ],
)
def test_numeric_size(host, size, placement, expected):
    d = _make(host, size=size, placement=placement)
    assert d.size() == size
    d.set_is_open(True)
    # getRect() 返回 tuple，必须与 tuple 比较（与 list 比较恒 False）
    assert d._panel.geometry().getRect() == expected


def test_numeric_size_forces_slide_axis(host):
    """数字 size 强制控制滑出轴长度：内容再多/再少都不变（自适应只属于档位）。"""
    d = _make(host, size=200, placement="top")
    _add_fixed(d, 300, 900)  # 内容想要 hint 948
    d.set_is_open(True)
    assert d._panel.height() == 200  # 仍强制 200
    assert d._panel.width() == 800   # 贴边轴照常铺满


def test_numeric_size_normalized_to_int(host):
    d = _make(host, size=250.9)
    assert d.size() == 250


def test_set_size_switches_between_token_and_number(host):
    d = _make(host, size="md", placement="right")
    d.set_is_open(True)
    assert d._panel.width() == 448  # 左右宽度固定为档位
    d.set_size(300)
    assert d.size() == 300
    assert d._panel.width() == 300


def test_slide_axis_adapts_to_content(host):
    """上下抽屉高度 = min(内容 sizeHint, size 上限, 宿主高)，空内容 80 兜底；
    打开中追加内容必须自动重排（外层布局缓存要失效）。"""
    # 空内容：hint 48 → 兜底 80（padding×2 + 关闭按钮）
    d = _make(host, size="md", placement="top")
    d.set_is_open(True)
    assert d._panel.height() == 80
    # 打开中追加内容 → 自动重排
    _add_fixed(d, 300, 200)  # hint 248
    assert d._panel.height() == 248
    # 超大内容被 size 档封顶
    _add_fixed(d, 300, 900)  # hint 1160
    assert d._panel.height() == 448


def test_horizontal_width_fixed_regardless_of_content(host):
    """左右抽屉宽度固定为 size 档，不随内容伸缩。"""
    d = _make(host, size="md", placement="right")
    _add_fixed(d, 100, 200)  # 内容宽 hint 148 < 448
    d.set_is_open(True)
    assert d._panel.width() == 448


@pytest.mark.parametrize("kind", ["opaque", "blur"])
def test_backdrop_created_when_not_transparent(host, kind):
    d = _make(host, backdrop=kind)
    d.set_is_open(True)
    bd = d._backdrop
    assert bd is not None
    # getRect() 返回 tuple，必须与 tuple 比较
    assert bd.geometry().getRect() == (0, 0, host.width(), host.height())
    # 遮罩必须压在 Drawer 下面（host 内容之上、Drawer 之下）
    kids = host.children()
    assert kids.index(bd) < kids.index(d)
    # disable_animation 时直接推到不透明，不走淡入
    assert bd._fade.progress_value() == 1.0


def test_transparent_backdrop_creates_nothing(host):
    d = _make(host, backdrop="transparent")
    d.set_is_open(True)
    assert d._backdrop is None


def test_backdrop_above_pre_existing_children(host):
    """回归：Drawer 晚于 host 已有子 widget 创建时，首次打开遮罩不能被压到内容之下。"""
    content = QWidget(host)
    content.setGeometry(0, 0, 800, 600)
    content.show()
    d = _make(host, backdrop="opaque")
    d.set_is_open(True)
    kids = host.children()
    bd = d._backdrop
    assert kids.index(bd) > kids.index(content)  # 遮罩盖住已有内容
    assert kids.index(d) > kids.index(bd)  # Drawer 又在遮罩之上


def test_panel_paints_background(host):
    """面板是 QWidget 子类，QSS 背景必须开 WA_StyledBackground 才会绘制。"""
    d = _make(host)
    assert d._panel.testAttribute(Qt.WidgetAttribute.WA_StyledBackground) is True


def test_content_top_aligned(host):
    """内容从顶部堆叠（HeroUI drawer 是 flex-start），不做垂直居中。"""
    d = _make(host)
    assert bool(d._panel._content_layout.alignment() & Qt.AlignmentFlag.AlignTop)


def test_custom_close_button_sized_and_placed(host):
    """回归：从未显示的自定义按钮 width() 是 640x480 默认值，
    放置时必须按 sizeHint 收敛并贴右上角，不能铺满面板块。"""
    d = _make(host, placement="right")
    custom = QPushButton("关闭")
    d.set_close_button(custom)
    d.set_is_open(True)
    panel = d._panel
    assert custom.width() < 640  # 没被 640 默认值撑爆
    assert 0 <= custom.x() <= panel.width() - custom.width()
    assert custom.y() >= 0
    # 用户锁定过尺寸的按钮应被尊重
    fixed = QPushButton("X")
    fixed.setFixedSize(48, 28)
    d.set_close_button(fixed)
    assert (fixed.width(), fixed.height()) == (48, 28)


def test_backdrop_destroyed_after_close(host):
    d = _make(host, backdrop="opaque")
    d.set_is_open(True)
    assert d._backdrop is not None
    d.set_is_open(False)
    assert d._backdrop is None
    assert d.isHidden() is True


def test_set_backdrop_while_open(host):
    d = _make(host, backdrop="transparent")
    d.set_is_open(True)
    assert d._backdrop is None
    d.set_backdrop("blur")
    assert d.backdrop() == "blur"
    assert d._backdrop is not None
    assert d.isHidden() is False
    d.set_backdrop("transparent")
    assert d._backdrop is None


def test_set_backdrop_invalid(host):
    d = _make(host)
    with pytest.raises(ValueError):
        d.set_backdrop("frost")


def test_reposition_on_placement_change(host):
    d = _make(host, placement="right", size="md")
    d.set_is_open(True)
    assert d._panel.x() == 352
    d.set_placement("left")
    assert d._panel.x() == 0


def test_backdrop_click_closes(host):
    d = _make(host, placement="right", size="md")
    d.set_is_open(True)
    _press(d, QPoint(10, 10))  # 左侧遮罩区
    assert d.is_open() is False


def test_backdrop_click_ignored_when_not_dismissable(host):
    d = _make(host, is_dismissable=False)
    d.set_is_open(True)
    _press(d, QPoint(10, 10))
    assert d.is_open() is True


def test_escape_closes(host):
    d = _make(host)
    d.set_is_open(True)
    d._on_escape()
    assert d.is_open() is False


def test_escape_disabled_by_keyboard_flag(host):
    d = _make(host, is_keyboard_dismiss_disabled=True)
    d.set_is_open(True)
    d._on_escape()
    assert d.is_open() is True


def test_escape_disabled_by_dismissable(host):
    d = _make(host, is_dismissable=False)
    d.set_is_open(True)
    d._on_escape()
    assert d.is_open() is True


def test_stacked_drawers_esc_closes_top_only(host):
    """双抽屉叠加时只有栈顶启用 Esc（同键多快捷键会触发 Qt 二义性全失效）；
    关掉栈顶后 Esc 归还下层。"""
    a = _make(host, placement="right")
    b = _make(host, placement="top")
    a.set_is_open(True)
    b.set_is_open(True)
    assert a._esc.isEnabled() is False  # 非栈顶
    assert b._esc.isEnabled() is True
    b._on_escape()
    assert b.is_open() is False
    assert a.is_open() is True
    assert a._esc.isEnabled() is True  # Esc 归还栈顶
    a._on_escape()
    assert a.is_open() is False


def test_signals(host):
    d = _make(host)
    seen: list = []
    d.open_changed.connect(seen.append)
    d.closed.connect(lambda: seen.append("closed"))
    d.set_is_open(True)
    d.set_is_open(False)
    assert seen == [True, False, "closed"]


def test_callbacks(host):
    events: list = []
    d = Drawer(
        host=host,
        disable_animation=True,
        on_open_change=lambda v: events.append(("change", v)),
        on_close=lambda: events.append(("close",)),
    )
    d.set_is_open(True)
    d.set_is_open(False)
    assert events == [("change", True), ("change", False), ("close",)]


def test_content_api(host):
    d = _make(host)
    lay = d.content_widget().layout()
    assert lay.count() == 0

    first = QWidget()
    d.add_widget(first)
    assert lay.count() == 1

    second = QWidget()
    d.set_content(second)
    assert lay.count() == 1
    assert lay.itemAt(0).widget() is second

    d.clear_content()
    assert lay.count() == 0


def test_hide_close_button(host):
    d = _make(host, hide_close_button=True)
    assert d._panel._close_btn is None
    d.set_hide_close_button(False)
    assert d._panel._close_btn is not None


def test_custom_close_button_closes_drawer(host):
    btn = QPushButton("close")
    d = _make(host, close_button=btn)
    assert d._panel._close_btn is btn
    d.set_is_open(True)
    btn.click()
    assert d.is_open() is False


def test_set_theme(host):
    d = _make(host)
    for mode in ("dark", "light", "auto"):
        d.set_theme(mode)
    assert d.is_open() is False
