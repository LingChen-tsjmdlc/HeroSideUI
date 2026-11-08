"""Popover 公共动态 API mixin：状态查询、视觉 setter 与主题同步。"""

from ...core import ThemeProvider
from ._constants import VALID_PLACEMENTS


class _PopoverApiMixin:
    """Popover 公共动态 API mixin。

    Note:
        依赖宿主的 _color/_size/_placement 等属性与 update/close 等方法。
    """

    # ============================================================
    # 状态查询
    # ============================================================
    def is_open(self) -> bool:
        """返回 popover 当前是否处于打开状态。

        Returns:
            bool: 打开返回 True，否则 False。
        """
        return self._is_open

    def toggle(self):
        """根据当前打开状态切换 popover：开则关、关则开。"""
        if self._is_open:
            self.close()
        else:
            self.open()

    # ============================================================
    # 视觉属性 setter
    # ============================================================
    def set_color(self, color: str):
        """设置 popover 底色主题色。

        Args:
            color: HeroUI 调色板名（default/primary/secondary/...）。
        """
        self._color = color
        self.update()
        self._apply_content_text_color()
        self._sync_trigger_style()

    def set_trigger_variant(self, variant: str):
        """设置触发控件的视觉 variant，并同步给 trigger。

        Args:
            variant: flat/bordered/shadow/...，依 trigger 支持情况而定。
        """
        self._trigger_variant = variant
        self._sync_trigger_style()

    def set_arrow(self, enabled: bool):
        """开启/关闭指向 trigger 的箭头，并刷新布局边距。

        Args:
            enabled: True 显示箭头。
        """
        self._arrow = enabled
        self._outer.setContentsMargins(*self._frame_margins())
        self.update()

    def set_size(self, size: str):
        """设置 popover 尺寸档位。

        Args:
            size: sm/md/lg 等尺寸 token。
        """
        self._size = size
        self.update()

    def set_radius(self, radius: str):
        """设置 popover 圆角档位。

        Args:
            radius: none/sm/md/lg/full 等圆角 token。
        """
        self._radius = radius
        self.update()

    def set_shadow(self, shadow: str):
        """设置 popover 阴影档位，并刷新布局边距。

        Args:
            shadow: 阴影 token（对应 POPOVER_SHADOWS 配置键）。
        """
        self._shadow = shadow
        self._outer.setContentsMargins(*self._frame_margins())
        self.update()

    def set_placement(self, placement: str):
        """设置弹出方向；非法值将被忽略。

        Args:
            placement: 12 种 placement 之一（top/bottom/.../right-end）。
        """
        if placement in VALID_PLACEMENTS:
            self._placement = placement
            self._actual_placement = placement
            self._outer.setContentsMargins(*self._frame_margins())
            self.update()

    def set_backdrop(self, kind: str):
        """设置遮罩层类型。

        Args:
            kind: transparent（穿透）/ opaque（半黑）/ blur（模糊快照）。
        """
        self._backdrop_kind = kind

    def set_is_disabled(self, disabled: bool):
        """设置是否禁用；若已打开则立即关闭。

        Args:
            disabled: True 禁用交互。
        """
        self._is_disabled = disabled
        if disabled and self._is_open:
            self.close()

    # ============================================================
    # 主题
    # ============================================================
    def set_theme(self, theme: str):
        """设置主题模式（auto/light/dark）。

        Args:
            theme: auto 订阅 ThemeProvider 广播；light/dark 固定。

        Note:
            仅刷新自身裸 QLabel 文字色；trigger 自身订阅 ThemeProvider，
            由其自治刷新，popover 不插手覆盖 trigger 状态。
        """
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
        """ThemeProvider 广播回调，应用新主题。

        Args:
            theme: 由 ThemeProvider 广播的目标主题（light/dark）。
        """
        self._theme = theme
        # 同 set_theme:只刷自家裸 QLabel,trigger 由它自己处理。
        self._apply_content_text_color()
        self.update()

    @staticmethod
    def _resolve_theme(mode: str) -> str:
        """解析主题模式为实际主题。

        Args:
            mode: auto/light/dark。

        Returns:
            str: light 或 dark。
        """
        if mode in ("light", "dark"):
            return mode
        return ThemeProvider.instance().current_theme

    # ============================================================
    # trigger 样式同步
    # ============================================================
    def _sync_trigger_style(self):
        """把 color/variant 同步给 trigger；绝不调 set_theme，trigger 主题自治。

        Note:
            传实际主题会把 auto 的 Button 注销出 ThemeProvider，切暗色时
            文字停留亮色规则导致低对比。
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
        """兼容旧名的 trigger 样式同步入口，等同 _sync_trigger_style。"""
        self._sync_trigger_style()
