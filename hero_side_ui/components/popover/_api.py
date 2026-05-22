"""Popover 公共动态 API mixin（私有）。

负责：
- 状态查询：`is_open / toggle`
- 视觉属性 setter：`set_color / set_size / set_radius / set_shadow /
  set_placement / set_backdrop / set_arrow / set_trigger_variant /
  set_is_disabled`
- 主题：`set_theme / _apply_provider_theme / _resolve_theme`
- trigger 样式同步：`_sync_trigger_style`（兼容旧名 `_sync_trigger_color`）

迁出原因：这些方法纯属"对外可调的状态变更"，不参与 open/close 生命周期主流程，
集中到 mixin 让 popover.py 主体只保留构造 + open/close/finalize 核心生命周期。
"""

from ...core import ThemeProvider
from ._constants import VALID_PLACEMENTS


class _PopoverApiMixin:
    """Popover 公共动态 API mixin。

    依赖宿主类提供：
      - 属性：`_color / _size / _radius / _shadow / _placement /
        _actual_placement / _backdrop_kind / _arrow / _trigger_variant /
        _is_disabled / _theme / _theme_mode / _trigger / _outer / _is_open`
      - 方法：`update / _frame_margins / close / _apply_content_text_color`
    """

    # ============================================================
    # 状态查询
    # ============================================================
    def is_open(self) -> bool:
        return self._is_open

    def toggle(self):
        if self._is_open:
            self.close()
        else:
            self.open()

    # ============================================================
    # 视觉属性 setter
    # ============================================================
    def set_color(self, color: str):
        self._color = color
        self.update()
        self._apply_content_text_color()
        self._sync_trigger_style()

    def set_trigger_variant(self, variant: str):
        self._trigger_variant = variant
        self._sync_trigger_style()

    def set_arrow(self, enabled: bool):
        self._arrow = enabled
        self._outer.setContentsMargins(*self._frame_margins())
        self.update()

    def set_size(self, size: str):
        self._size = size
        self.update()

    def set_radius(self, radius: str):
        self._radius = radius
        self.update()

    def set_shadow(self, shadow: str):
        self._shadow = shadow
        self._outer.setContentsMargins(*self._frame_margins())
        self.update()

    def set_placement(self, placement: str):
        if placement in VALID_PLACEMENTS:
            self._placement = placement
            self._actual_placement = placement
            self._outer.setContentsMargins(*self._frame_margins())
            self.update()

    def set_backdrop(self, kind: str):
        self._backdrop_kind = kind

    def set_is_disabled(self, disabled: bool):
        self._is_disabled = disabled
        if disabled and self._is_open:
            self.close()

    # ============================================================
    # 主题
    # ============================================================
    def set_theme(self, theme: str):
        if theme == "auto":
            self._theme_mode = "auto"
            self._theme = self._resolve_theme("auto")
            ThemeProvider.instance().register(self)
        else:
            if self._theme_mode == "auto":
                ThemeProvider.instance().unregister(self)
            self._theme_mode = theme
            self._theme = theme
        # 主题变化后:内容里的"裸 QLabel"文字色是我们 setStyleSheet 写死的 hex,
        # 不会自动跟主题切换 → 必须显式重刷。
        # 注意:不在这里 _sync_trigger_style() —— trigger(Button) 自己订阅了
        # ThemeProvider,会自治刷新 theme;popover 在 attach 时已做过一次性
        # color/variant 默认同步,主题切换不该再插手覆盖 trigger 状态。
        self._apply_content_text_color()
        self.update()

    def _apply_provider_theme(self, theme: str):
        """ThemeProvider 广播专用"""
        self._theme = theme
        # 同 set_theme:只刷自家裸 QLabel,trigger 由它自己处理。
        self._apply_content_text_color()
        self.update()

    @staticmethod
    def _resolve_theme(mode: str) -> str:
        if mode in ("light", "dark"):
            return mode
        return ThemeProvider.instance().current_theme

    # ============================================================
    # trigger 样式同步
    # ============================================================
    def _sync_trigger_style(self):
        """把 popover 的 color/variant 同步给 trigger。

        6 种色（default / primary / secondary / success / warning / danger）全部透传。
        但**绝不调用 trigger.set_theme(self._theme)**：如果 trigger 原本是
        theme="auto" 的 Button，传入实际主题 "light" 会把它注销出 ThemeProvider，
        后续切 dark 时按钮文字仍停留在亮色规则，暗色背景下会变成低对比灰色。
        trigger 的主题应由它自己监听 ThemeProvider 自治刷新。
        """
        if self._trigger is None:
            return

        if hasattr(self._trigger, "set_color"):
            try:
                self._trigger.set_color(self._color)
            except Exception:
                pass
        if hasattr(self._trigger, "set_variant"):
            try:
                self._trigger.set_variant(self._trigger_variant)
            except Exception:
                pass

    # 兼容旧名
    def _sync_trigger_color(self):
        self._sync_trigger_style()
