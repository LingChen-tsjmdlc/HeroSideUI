# tests/animation — 动画基元测试

对应源码：`hero_side_ui/animation/`

## 这层测什么

animation 模块封装了所有可复用的"动画样板"和绘制基元，被组件层广泛复用。这层测的是**动画的接口契约 + 状态机**，不验证视觉效果。

| 建议文件                     | 被测对象                                        | 关注点                                                                                                                    |
| ---------------------------- | ----------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| `test_tween.py`              | `tween_value` / `tween_geometry` / `stop_tween` | `start==end` 不启动返回 None；先 stop 旧再起新；finished 后 runner_attr 清回 None；on_finished 被调用；多次连续调用不泄漏 |
| `test_ripple.py`             | `RippleOverlay`                                 | `trigger(pos)` 后 active；duration 内 widget 仍 alive；finished 后自身被 deleteLater                                      |
| `test_press_scale.py`        | `PressScaleEffect`                              | press → scale<1.0；release → scale==1.0；嵌套到子 effect 时不冲突                                                         |
| `test_collapse.py`           | `CollapseAnimation`                             | expand/collapse 切换；目标高度可达；信号 `finished` 发射；进行中再次 toggle 反向                                          |
| `test_label_float.py`        | `LabelFloatAnimation`                           | resting↔floated 切换；progress ∈ [0,1]；插值回调被调                                                                      |
| `test_underline_expand.py`   | `UnderlineBar`                                  | progress 控制宽度比例；颜色变更立即生效                                                                                   |
| `test_fade_scale.py`         | `FadeScaleAnimation`                            | opacity 0→1；scale 0.95→1；close 反向                                                                                     |
| `test_indeterminate.py`      | `IndeterminateBarAnimation` / `SpinAnimation`   | 循环动画在 stop() 后停止；loop 计数；周期对齐                                                                             |
| `test_stripe_flow.py`        | `StripeFlowAnimation`                           | offset 单调推进；stop 后立即冻结                                                                                          |
| `test_backdrop_fade.py`      | `BackdropFade`                                  | alpha 0→target；close 反向                                                                                                |
| `test_check_draw.py`         | `paint_animated_check` / `CheckDrawAnimation`   | progress=0 不画；progress=1 完整对勾；中间值描出部分线段；driver 的 expand/collapse 切换                                  |
| `test_padding_squeeze.py`    | `PaddingSqueezeAnimation`                       | margin 插值正确；finished 时停                                                                                            |
| `test_pixmap_scale_proxy.py` | `PixmapScaleProxy`                              | 子 widget 的 paint 被缩放代理；scale=1.0 时透明                                                                           |

## 这层 _不_ 测什么

- ❌ 动画在某个真实组件里的视觉表现（例如 Button 的按压回弹）→ 由 `tests/components/test_button.py` 测"按压后状态恢复"，视觉靠 examples
- ❌ 像素级颜色断言 / 视觉回归 → 放 `tools/visual_regression/`（如未来引入）

## 测试写法范式

### 1. tween_value：值跳变 + runner 生命周期

```python
import pytest
from PySide6.QtCore import QObject
from PySide6.QtGui import QColor
from hero_side_ui.animation import tween_value, stop_tween


class Owner(QObject):
    pass


def test_start_equals_end_returns_none(qtbot):
    owner = Owner()
    captured = []
    anim = tween_value(owner, "_r", QColor("#fff"), QColor("#fff"),
                       captured.append, duration=100)
    assert anim is None
    assert getattr(owner, "_r", None) is None
    assert captured == []


def test_runner_cleared_after_finish(qtbot):
    owner = Owner()
    captured = []
    anim = tween_value(owner, "_r", 0.0, 1.0, captured.append, duration=50)
    assert owner._r is anim
    qtbot.wait(120)
    assert owner._r is None
    # 起止值都被发射过
    assert captured[0] == pytest.approx(0.0, abs=0.05)
    assert captured[-1] == pytest.approx(1.0, abs=0.01)


def test_consecutive_calls_stop_previous(qtbot):
    owner = Owner()
    a1 = tween_value(owner, "_r", 0.0, 1.0, lambda v: None, duration=500)
    a2 = tween_value(owner, "_r", 1.0, 0.0, lambda v: None, duration=500)
    # a1 应该被 stop，owner 持有 a2
    assert owner._r is a2
    qtbot.wait(20)
    assert a1.state() == a1.State.Stopped
```

要点：

- `qtbot.wait(duration + 缓冲)` 给动画跑完的窗口（缓冲 50~100ms 足够）。
- runner_attr 是否清回 None 是必查项 —— 漏清就是 GC 引用泄漏。

### 2. paintEvent / 绘制函数：用 QImage + QPainter 直接画

```python
from PySide6.QtGui import QImage, QPainter, QColor
from hero_side_ui.animation import paint_animated_check


def test_check_progress_0_paints_nothing(qtbot):
    img = QImage(40, 40, QImage.Format_ARGB32)
    img.fill(QColor("white"))
    p = QPainter(img)
    paint_animated_check(p, img.rect(), color=QColor("black"),
                         progress=0.0, line_width=2)
    p.end()
    # 中心仍是白色
    assert img.pixelColor(20, 20).name() == "#ffffff"


def test_check_progress_1_paints_full(qtbot):
    img = QImage(40, 40, QImage.Format_ARGB32)
    img.fill(QColor("white"))
    p = QPainter(img)
    paint_animated_check(p, img.rect(), color=QColor("black"),
                         progress=1.0, line_width=3)
    p.end()
    # 描线区域应有黑色像素
    has_black = any(
        img.pixelColor(x, y).red() < 50
        for x in range(40) for y in range(40)
    )
    assert has_black
```

### 3. Overlay/Effect 类：parent widget + signal 监听

```python
def test_ripple_emits_finished(qtbot):
    from PySide6.QtWidgets import QPushButton
    from hero_side_ui.animation import RippleOverlay
    btn = QPushButton("X"); qtbot.addWidget(btn); btn.resize(120, 36)
    ripple = RippleOverlay(btn)
    with qtbot.waitSignal(ripple.finished, timeout=1500):
        ripple.trigger(btn.rect().center())
```

要点：

- 动画测试**永远不要 `time.sleep`** —— 用 `qtbot.wait(ms)` 或 `qtbot.waitSignal`，否则事件循环不跑，QPropertyAnimation 不会推进。
- 动画对象的销毁很容易引爆 access violation（Windows 上）。**测试退出前必须让动画自然 finished 或调 stop()**，conftest 的 `_stop_all_timers_and_animations` 是兜底网，不能依赖它替你擦屁股。
