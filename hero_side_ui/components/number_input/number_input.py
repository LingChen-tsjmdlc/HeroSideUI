"""NumberInput：Input 全套外框 + 数值层（stepper、键盘滚轮步进、min/max
夹取、千分位与 percent/currency 格式化）。

对齐 react-stately：空值步进从 0 或最近边界起步；percent 语义为值即显示
数字。stepper 插入 wrapper 布局末尾（同官方 innerWrapper 追加方式）。
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QWidget

from ...themes import HEROUI_COLORS, NUMBER_INPUT_MIN_WIDTHS
from ..input.input import Input
from ._stepper import _NumberStepper

__all__ = ["NumberInput"]

# 货币符号映射：覆盖 SWIFT 2025-02 全球支付占比前 20（合计约 99%）
# 另补 INR/BRL/RUB/TWD/PHP/IDR/VND/ILS 等主要经济体货币；
# 未收录的货币回退为「代码 + 空格」前缀
_CURRENCY_SYMBOLS = {
    # SWIFT 支付占比前 20
    "USD": "$",  # 48.95%
    "EUR": "€",  # 22.25%
    "GBP": "£",  # 6.89%
    "CNY": "¥",  # 4.33%
    "JPY": "¥",  # 3.68%
    "CAD": "C$",  # 2.44%
    "HKD": "HK$",  # 1.88%
    "AUD": "A$",  # 1.51%
    "SGD": "S$",  # 1.38%
    "CHF": "CHF ",  # 0.95%（Intl 同款带空格前缀）
    "SEK": "kr",  # 0.82%
    "PLN": "zł",  # 0.80%
    "NOK": "kr",  # 0.61%
    "DKK": "kr",  # 0.38%
    "NZD": "NZ$",  # 0.35%
    "ZAR": "R",  # 0.28%
    "THB": "฿",  # 0.27%
    "MXN": "MX$",  # 0.26%
    "HUF": "Ft",  # 0.22%
    "MYR": "RM",  # 0.20%
    "KRW": "₩",
    # SWIFT 榜外但经济体量/使用人数靠前
    "INR": "₹",
    "RUB": "₽",
    "TRY": "₺",
    "BRL": "R$",
    "TWD": "NT$",
    "PHP": "₱",
    "IDR": "Rp",
    "VND": "₫",
    "ILS": "₪",
}

# 步进累积的浮点误差收敛位数（0.1 + 0.2 → 0.30000000000000004）
_STEP_ROUND_DIGITS = 10


class NumberInput(Input):
    """HeroUI 风格数字输入，继承 Input 全部 API。

    Args:
        value: 初始数值；None 为空。
        min_value: 值域下界。
        max_value: 值域上界。
        step: 步进长度，默认 1。
        hide_stepper: 隐藏右侧步进按钮组。
        is_wheel_disabled: 关闭滚轮步进。
        format_options: 格式化子集（style/currency/小数位/分组）。

    Signals:
        value_changed: 可解析发 float，空/非法发 None。
    """

    value_changed = Signal(object)

    _object_name = "heroNumberInput"

    def __init__(
        self,
        label: str = "",
        value: float | None = None,
        placeholder: str = "",
        variant: str = "flat",
        color: str = "default",
        size: str = "md",
        radius: str | None = None,
        label_placement: str = "inside",
        min_value: float | None = None,
        max_value: float | None = None,
        step: float = 1.0,
        hide_stepper: bool = False,
        is_wheel_disabled: bool = False,
        format_options: dict | None = None,
        is_disabled: bool = False,
        is_invalid: bool = False,
        is_required: bool = False,
        is_readonly: bool = False,
        is_clearable: bool = False,
        full_width: bool = True,
        description: str = "",
        error_message: str = "",
        start_content=None,
        end_content=None,
        on_start_content_click=None,
        on_end_content_click=None,
        theme: str = "auto",
        parent: QWidget | None = None,
    ):
        if step == 0:
            raise ValueError("step must not be 0")

        self._min_value = min_value
        self._max_value = max_value
        self._step = float(step)
        self._hide_stepper = hide_stepper
        self._is_wheel_disabled = is_wheel_disabled
        self._format_options = dict(format_options) if format_options else {}
        self._numeric_value: float | None = None
        self._last_emitted = "unset"
        self._auto_invalid = False
        self._user_invalid = is_invalid

        super().__init__(
            label=label,
            value="",
            placeholder=placeholder,
            variant=variant,
            color=color,
            size=size,
            radius=radius,
            label_placement=label_placement,
            is_disabled=is_disabled,
            is_invalid=is_invalid,
            is_required=is_required,
            is_readonly=is_readonly,
            is_clearable=is_clearable,
            full_width=full_width,
            description=description,
            error_message=error_message,
            start_content=start_content,
            end_content=end_content,
            on_start_content_click=on_start_content_click,
            on_end_content_click=on_end_content_click,
            theme=theme,
            parent=parent,
        )

        # ---- stepper：插到 wrapper 布局末尾（clear 按钮之后，对齐官方位置）----
        self._stepper = _NumberStepper(button_size=18, parent=self._wrapper)
        self._wrapper.layout().addWidget(self._stepper, 0, Qt.AlignmentFlag.AlignVCenter)
        self._stepper.stepped.connect(self._step_by)

        # ---- 数值层事件 ----
        self.line_edit.textChanged.connect(self._on_number_text_changed)
        self.line_edit.editingFinished.connect(self._on_commit_text)

        self._apply_styles()

        if value is not None:
            self.set_value(value)

    # ============================================================
    # 格式化与解析
    # ============================================================
    def _fraction_digits(self) -> tuple:
        """(min_fd, max_fd)：currency 默认 2/2，其余 0/3（对齐 Intl 默认）。"""
        fo = self._format_options
        if fo.get("style") == "currency":
            return (
                fo.get("minimum_fraction_digits", 2),
                fo.get("maximum_fraction_digits", 2),
            )
        return (
            fo.get("minimum_fraction_digits", 0),
            fo.get("maximum_fraction_digits", 3),
        )

    def _currency_symbol(self, code: str) -> str:
        """查货币符号映射；未收录回退「代码 + 空格」前缀。

        Args:
            code: ISO 货币代码（如 USD）。

        Returns:
            str: 货币符号或回退前缀。
        """
        return _CURRENCY_SYMBOLS.get(code, code + " ")

    def _format_number(self, v: float) -> str:
        """数值 → 显示文本（分组分隔符 / 百分号 / 货币前缀）。"""
        fo = self._format_options
        min_fd, max_fd = self._fraction_digits()
        use_grouping = fo.get("use_grouping", True)
        body = f"{v:,.{max_fd}f}" if use_grouping else f"{v:.{max_fd}f}"
        # 收掉 min_fd 之外的尾随 0（Intl 行为：实际位数在 min/max 之间自适应）
        if "." in body:
            integer, frac = body.rsplit(".", 1)
            frac = frac.rstrip("0")
            if len(frac) < min_fd:
                frac = frac.ljust(min_fd, "0")
            body = integer + ("." + frac if frac else "")
        if fo.get("style") == "percent":
            return body + "%"
        if fo.get("style") == "currency":
            return self._currency_symbol(fo.get("currency", "USD")) + body
        return body

    def _parse_number(self, text: str) -> float | None:
        """显示文本 → 数值；空或解析失败返回 None。"""
        fo = self._format_options
        strip_chars = {",", " "}
        if fo.get("style") == "percent":
            strip_chars.add("%")
        if fo.get("style") == "currency":
            strip_chars.update(self._currency_symbol(fo.get("currency", "USD")))
        s = "".join(ch for ch in text.strip() if ch not in strip_chars)
        if s in ("", "-", "+", "."):
            return None
        try:
            return float(s)
        except ValueError:
            return None

    # ============================================================
    # 数值状态
    # ============================================================
    def _clamp(self, v: float) -> float:
        """把值夹到 [min_value, max_value] 区间内。

        Args:
            v: 待夹取的数值。

        Returns:
            float: 夹取后的数值。
        """
        if self._min_value is not None:
            v = max(v, self._min_value)
        if self._max_value is not None:
            v = min(v, self._max_value)
        return v

    def value(self) -> float | None:
        """当前数值；文本为空或不可解析时返回 None。"""
        return self._numeric_value

    def set_value(self, value: float | None):
        """设置数值（会夹取并格式化）；None 等价清空。"""
        if value is None:
            self.line_edit.clear()
            return
        self.line_edit.setText(self._format_number(self._clamp(float(value))))

    def _emit_value(self, v: float | None):
        """值有变化才发信号（None 与 float 的比较语义天然正确）。"""
        if v != self._last_emitted:
            self._last_emitted = v
            self.value_changed.emit(v)

    def _on_number_text_changed(self, text: str):
        """文本实时变化：解析数值、记忆、必要时撤掉自动标红，并广播 value_changed。"""
        v = self._parse_number(text)
        self._numeric_value = v
        if v is not None and self._auto_invalid:
            # 用户把非法文本修好了 → 撤掉自动标红
            self._auto_invalid = False
            self._is_invalid = self._user_invalid
            self._apply_styles()
        self._emit_value(v)

    def _on_commit_text(self):
        """blur / 回车提交：非法标红不改写，合法则夹取并按格式回显。"""
        text = self.line_edit.text()
        v = self._parse_number(text)
        if v is None:
            if text.strip():
                # 非法文本：标红提示，绝不静默改写用户输入
                self._auto_invalid = True
                self._is_invalid = True
                self._apply_styles()
            elif self._auto_invalid:
                self._auto_invalid = False
                self._is_invalid = self._user_invalid
                self._apply_styles()
            return
        clamped = self._clamp(v)
        if self._auto_invalid:
            self._auto_invalid = False
            self._is_invalid = self._user_invalid
            self._apply_styles()
        formatted = self._format_number(clamped)
        if text != formatted:
            self.line_edit.setText(formatted)
        else:
            # 文本已规范化（含被夹取但文本恰好相同的场景），手动同步一次
            self._numeric_value = clamped
            self._emit_value(clamped)

    # ============================================================
    # 步进
    # ============================================================
    def _step_by(self, direction: int):
        """±step 一步；空值从 0（或最近值域边界）起步。"""
        if self._is_disabled or self._is_readonly:
            return
        base = self._numeric_value
        if base is None:
            base = self._clamp(0.0)
        new = round(base + direction * self._step, _STEP_ROUND_DIGITS)
        new = self._clamp(new)
        self.line_edit.setText(self._format_number(new))
        self.line_edit.setFocus()

    def set_step(self, step: float):
        """设置步进长度（不可为 0）。

        Args:
            step: 步进长度。

        Raises:
            ValueError: step 为 0 时。
        """
        if step == 0:
            raise ValueError("step must not be 0")
        self._step = float(step)

    def set_min_value(self, min_value: float | None):
        """设置值域下界并重新夹取已有值。

        Args:
            min_value: 下界；None 表示无下界。
        """
        self._min_value = min_value
        self._resync_to_bounds()

    def set_max_value(self, max_value: float | None):
        """设置值域上界并重新夹取已有值。

        Args:
            max_value: 上界；None 表示无上界。
        """
        self._max_value = max_value
        self._resync_to_bounds()

    def _resync_to_bounds(self):
        """值域变化后把已有值拉回界内。"""
        if self._numeric_value is None:
            return
        clamped = self._clamp(self._numeric_value)
        if clamped != self._numeric_value:
            self.line_edit.setText(self._format_number(clamped))

    def set_hide_stepper(self, hide: bool):
        """隐藏/显示右侧步进按钮组（并触发样式刷新）。

        Args:
            hide: True 隐藏 stepper。
        """
        self._hide_stepper = hide
        self._apply_styles()

    # ============================================================
    # 状态 setter 联动 stepper
    # ============================================================
    def set_is_disabled(self, disabled: bool):
        """设置禁用态并联动 stepper 按钮可用性。"""
        super().set_is_disabled(disabled)
        self._stepper.set_buttons_enabled(not disabled and not self._is_readonly)

    def set_is_readonly(self, readonly: bool):
        """设置只读态并联动 stepper 按钮可用性。"""
        super().set_is_readonly(readonly)
        self._stepper.set_buttons_enabled(not self._is_disabled and not readonly)

    def set_is_invalid(self, invalid: bool):
        """设置错误态（记录用户显式标红，覆盖自动标红）。"""
        self._user_invalid = invalid
        super().set_is_invalid(invalid)

    # ============================================================
    # 事件：上下键 / Esc / 滚轮
    # ============================================================
    def eventFilter(self, obj, event):
        """拦截输入框的上下键/Esc/滚轮，驱动步进与清空（聚焦时滚轮才步进）。"""
        if obj is self.line_edit:
            if event.type() == QEvent.Type.KeyPress:
                if event.key() == Qt.Key.Key_Up:
                    self._step_by(1)
                    return True
                if event.key() == Qt.Key.Key_Down:
                    self._step_by(-1)
                    return True
                if (
                    event.key() == Qt.Key.Key_Escape
                    and self._is_clearable
                    and not self._is_disabled
                    and not self._is_readonly
                    and self.line_edit.text()
                ):
                    self.line_edit.clear()
                    return True
            elif event.type() == QEvent.Type.Wheel:
                # 对齐 react-aria：滚轮仅在输入框聚焦时步进
                if (
                    not self._is_wheel_disabled
                    and not self._is_disabled
                    and not self._is_readonly
                    and self.line_edit.hasFocus()
                ):
                    self._step_by(1 if event.angleDelta().y() > 0 else -1)
                    return True
        return super().eventFilter(obj, event)

    # ============================================================
    # 样式：stepper 图标色 / 尺寸 / 可用性跟随组件状态
    # ============================================================
    def _apply_styles(self):
        """样式下发：调父类后额外设置 stepper 图标色 / 尺寸 / 可用性 / 可见性。"""
        super()._apply_styles()
        if not hasattr(self, "_stepper"):
            # 父类 __init__ 首次调用时 stepper 还没建
            return
        is_dark = self._theme == "dark"
        colors = HEROUI_COLORS.get(self._color, HEROUI_COLORS["default"])
        dc = HEROUI_COLORS["default"]
        if self._color == "default":
            icon_color = QColor(dc[400] if is_dark else dc[500])
        else:
            # 语义色：DEFAULT 档即 500 阶（HEROUI_COLORS 只有 int 键 50~900）
            icon_color = QColor(colors[500])
        self._stepper.set_icon_color(icon_color)

        outside = self._label_placement in ("outside", "outside-left", "outside-top")
        self._stepper.set_button_size(14 if outside else 18)
        self._stepper.set_buttons_enabled(not self._is_disabled and not self._is_readonly)
        self._stepper.setVisible(not self._hide_stepper)

    def _size_config(self) -> dict:
        """取 Input 尺寸表并把 min_width 换为数字档（60/70/80）。"""
        cfg = dict(super()._size_config())
        cfg["min_width"] = NUMBER_INPUT_MIN_WIDTHS.get(self._size, NUMBER_INPUT_MIN_WIDTHS["md"])
        return cfg
