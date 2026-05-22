"""_Backdrop — Popover 弹出时的全屏遮罩层（私有，可选启用）。"""

from PySide6.QtCore import Signal
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QWidget

from ...animation import BackdropFade


# ============================================================
# Backdrop
# ============================================================
class _Backdrop(QWidget):
    """遮罩层 — 作为 **host window 的子 widget**，只覆盖 host 的客户区；
    不会遮到其他应用、其他屏幕。

    kind:
        transparent — 透明遮罩（只用于拦截/不拦截点击）
        opaque      — 黑色 50% 遮罩
        blur        — 对 host 客户区做静态截屏 + 高斯模糊作为背景，再叠 30% 黑

    淡入淡出由 `BackdropFade` 驱动（paintEvent 里 `setOpacity(progress)`）。

    **static snapshot 说明**：`blur` 模式默认是 `show()` 之前 `prepare_blur_snapshot`
    抓一次高质量高斯（QGraphicsBlurEffect QualityHint）；之后 host 内容变化不会
    自动反映到 backdrop 上。这对 Popover 短期开关场景已够用。

    **滚动重抓场景**（blur）：由外部（Popover）在滚动节流帧调 `refresh_blur_fast()`。
    `blur_quality` 4 档（其中前 3 档都是金字塔 box blur，按中心极限定理 N 次盒滤波
    叠加趋近高斯；level 越高边缘越柔和但成本线性增）：

    | 档位         | 算法                              | 帧时（1080p） |
    | ------------ | --------------------------------- | ------------- |
    | ``low``      | 2 级金字塔                        | ~5-7ms        |
    | ``fast``（默认） | 3 级金字塔                    | ~8-12ms       |
    | ``great``    | 4 级金字塔                        | ~12-16ms      |
    | ``high``     | QGraphicsBlurEffect QualityHint   | ~30-60ms      |

    边际收益：3→4 级肉眼可辨（fast→great 推荐升档场景）；4→真高斯（``high``）
    柔和度仍有提升但代价跳变。默认 ``fast`` 是甜区。**注意：曾有 5 级金字塔档
    （balanced）已删除——CLT 上 N=10 已超过真高斯的视觉模糊度，反而失真。**
    """

    # blur_quality → 金字塔级数映射；'high' 走 QGraphicsBlurEffect 不在此表。
    _PYRAMID_LEVELS = {"low": 2, "fast": 3, "great": 4}
    _VALID_QUALITY = ("low", "fast", "great", "high")

    clicked = Signal()
    # backdrop 上的滚轮 — 由 Popover 决定如何处理（关闭 / 转发 / 二者都做）。
    # 不在 backdrop 内直接 close()/转发：backdrop 不知道祖先 ScrollArea 在哪，
    # 也不知道 close_on_scroll 配置。把决策权交给 Popover。
    #
    # 参数是 QPoint（angleDelta）——不传递原 QWheelEvent 对象：
    # Qt event 对象生命周期只在派发栈内有效，同步 signal 下虽然 OK 但诡异。
    # 只传足够让 Popover 重建 QWheelEvent 转发给 ScrollArea 的信息。
    wheel_scrolled = Signal(object)  # 携带 angleDelta(QPoint)

    def __init__(
        self,
        kind: str = "transparent",
        host: Optional[QWidget] = None,
        blur_quality: str = "fast",
    ):
        # 关键：parent = host，不是独立顶层窗口
        super().__init__(host)
        self._kind = kind
        self._host = host
        # blur_quality 4 档；非法直接抛错（参考 FontProvider 的 6 档 token，
        # 诚实优于花哨；外部传错应该爆炸而不是默默降级）。
        if blur_quality not in self._VALID_QUALITY:
            raise ValueError(
                f"blur_quality must be one of {self._VALID_QUALITY}, got {blur_quality!r}"
            )
        self._blur_quality = blur_quality
        self._blur_pixmap: Optional["QPixmap"] = None
        # 在 host.grab() 期间抑制自己的 paintEvent：避免抢到包含
        # backdrop 本身的 snapshot（黑底+模糊会叠加到下一帧中，造成“越滚越黑”累积 bug）。
        self._suppress_paint = False

        # 作为 host 的子 widget，不需要 window flags
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        # transparent 模式不拦截点击（事件穿透）
        self.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents, kind == "transparent"
        )

        # 淡入淡出 —— 复用通用 BackdropFade 动画
        self._fade = BackdropFade(owner=self, duration_in=260, duration_out=200)

        # host resize 监听：window 缩放时如果不同步 backdrop 几何 + blur snapshot，
        # 会出现“穿帮”——backdrop 还停在旧尺寸（变大露底；变小不致命但 pixmap 拉伸
        # 视觉糊烂）。装 eventFilter 监听 host Resize → 节流到下一帧统一处理。
        # _resize_pending 用于合并同一帧多次 Resize 事件，避免重复 grab 浪费 CPU。
        self._resize_pending = False
        if host is not None:
            host.installEventFilter(self)

    def eventFilter(self, obj, event):
        """监听 host 的 Resize：节流 → 同步 backdrop 几何 + blur 重抓。"""
        from PySide6.QtCore import QEvent, QTimer

        if obj is self._host and event.type() == QEvent.Type.Resize:
            if not self._resize_pending:
                self._resize_pending = True
                QTimer.singleShot(0, self._on_host_resized)
        return super().eventFilter(obj, event)

    def _on_host_resized(self):
        """host 缩放节流帧合并响应：同步 backdrop 几何 + blur 模式重抓 snapshot。"""
        self._resize_pending = False
        if self._host is None:
            return
        try:
            self.setGeometry(0, 0, self._host.width(), self._host.height())
        except RuntimeError:
            return
        # blur 模式：旧 pixmap 是按旧尺寸抓的，新尺寸下被拉伸畸变 → 重抓。
        # 走 refresh_blur_fast 而非 prepare_blur_snapshot：用户当前 blur_quality
        # 档位的算法保持一致；high 档下走 QGraphicsBlurEffect QualityHint。
        if self._kind == "blur":
            self.refresh_blur_fast()

    def closeEvent(self, event):
        # host 还活着的话主动 remove，避免 backdrop deleteLater 后 host 仍持悬挂引用。
        host = self._host
        if host is not None:
            try:
                host.removeEventFilter(self)
            except RuntimeError:
                pass
        super().closeEvent(event)

    def play_in(self):
        self._fade.play_in()

    def play_out(self):
        self._fade.play_out()

    def prepare_blur_snapshot(self):
        """在 show() 之前调用：抓取 host 客户区做高斯模糊快照。"""
        if self._host is None:
            return
        from PySide6.QtGui import QPixmap
        from PySide6.QtWidgets import (
            QGraphicsScene,
            QGraphicsPixmapItem,
            QGraphicsBlurEffect,
        )

        # 首次 grab 一般在 backdrop show() 之前，应不会被护到自己；
        # 但为了路径一致也加上护栏，成本为零。
        self._suppress_paint = True
        try:
            pm = self._host.grab()
        finally:
            self._suppress_paint = False
        if pm.isNull():
            return

        scene = QGraphicsScene()
        item = QGraphicsPixmapItem(pm)
        effect = QGraphicsBlurEffect()
        effect.setBlurRadius(16)
        effect.setBlurHints(QGraphicsBlurEffect.BlurHint.QualityHint)
        item.setGraphicsEffect(effect)
        scene.addItem(item)

        blurred = QPixmap(pm.size())
        blurred.fill(Qt.GlobalColor.transparent)
        painter = QPainter(blurred)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        scene.render(painter)
        painter.end()

        self._blur_pixmap = blurred

    def refresh_blur_fast(self):
        """滚动节流帧重抓模糊。按 `blur_quality` 选路径：

        - ``high`` → `_apply_gaussian_blur(pm)`：QGraphicsBlurEffect QualityHint，
          与初始 snapshot 同算法；最柔和但单帧 ~30-60ms，可能掉帧。
        - 其余 3 档 → `_apply_pyramid_box_blur(pm, w, h, levels)`：每级 1/2
          SmoothTransformation downsample 再 upsample，按中心极限定理 N 次盒滤波
          叠加趋近高斯。levels=2/3/4 对应 low/fast/great。

        坑：单次大比例 downsample（如 1/4 一刀切）= 大窗口盒滤波 → 块边/马赛克。
        金字塔的渐进多级 1/2 缩放天然规避（每级窗口都很小）。
        """
        if self._kind != "blur" or self._host is None:
            return

        # 关键：grab 之前抑制 backdrop 自己的 paintEvent。
        # backdrop 是 host 的子 widget，host.grab() 会同步走所有可见子 widget 的
        # paintEvent 画到 pixmap 上。如果不抑制，backdrop 在 snapshot 里会贴一层
        # “模糊背景 + 30% 黑”，下一帧 paintEvent 又会在其上再叠 30% 黑——
        # 逐帧黑色累积，越滚越黑。这里让 paintEvent 直接 return 跟过。
        self._suppress_paint = True
        try:
            try:
                pm = self._host.grab()
            except RuntimeError:
                # host 已销毁
                return
        finally:
            self._suppress_paint = False
        if pm.isNull():
            return

        w, h = pm.width(), pm.height()
        if w <= 0 or h <= 0:
            return

        if self._blur_quality == "high":
            # 高质量路径：与 prepare_blur_snapshot 同源 QGraphicsBlurEffect。
            blurred = self._apply_gaussian_blur(pm)
        else:
            # 金字塔 box blur：levels 由档位映射。
            levels = self._PYRAMID_LEVELS[self._blur_quality]
            blurred = self._apply_pyramid_box_blur(pm, w, h, levels)

        if blurred is None:
            return
        self._blur_pixmap = blurred
        self.update()

    @staticmethod
    def _apply_pyramid_box_blur(pm, w: int, h: int, levels: int):
        """N 级金字塔 box blur —— 每级 1/2 SmoothTransformation 双线性 down
        到 1/2^levels，再对称 up 还原；CLT 上 N 次盒滤波叠加趋近高斯，
        每级缩放窗口很小无块边。

        levels 取值 2..4，分别对应 blur_quality 的 low/fast/great：
          - 2 → 1/2→1/4 →up→up，~5-7ms，最快但边缘略糙。
          - 3 → 多一级 1/8，~8-12ms，**默认 fast 档**。
          - 4 → 多一级 1/16，~12-16ms，great 档；细腻度肉眼可辨。

        坑（已踩）：单次大比例 downsample（如 1/4 一刀切）= 大窗口盒滤波 →
        块边/马赛克。必须渐进多级 1/2 缩放（UE/Unity bloom/DOF 标配做法）。
        坑（已踩）：曾有 5 级（balanced）档，CLT 上 N=10 已超过 16px QGraphicsBlurEffect
        的视觉模糊度——视觉"过度模糊失真"反而比真高斯还糊，已删除。
        """
        smooth = Qt.TransformationMode.SmoothTransformation
        keep = Qt.AspectRatioMode.IgnoreAspectRatio

        # 逐级 down 到 1/2^levels
        downs = [pm]
        cw, ch = w, h
        for _ in range(levels):
            cw, ch = max(1, cw // 2), max(1, ch // 2)
            downs.append(downs[-1].scaled(cw, ch, keep, smooth))

        # 逐级 up 还原回 (w, h)
        cur = downs[-1]
        # 中间级别尺寸：对称用 downs[levels-1..1] 的尺寸
        for i in range(levels - 1, 0, -1):
            tw, th = downs[i].width(), downs[i].height()
            cur = cur.scaled(tw, th, keep, smooth)
        return cur.scaled(w, h, keep, smooth)

    @staticmethod
    def _apply_gaussian_blur(pm):
        """QGraphicsBlurEffect QualityHint 高斯模糊（与 prepare_blur_snapshot 同算法）。
        单帧 ~30-60ms，慢但最柔和；用于 blur_quality='high'。
        与 ``great``（4 级金字塔）的视觉差距很小，仅在大半径 + 静帧细看时能分辨。"""
        from PySide6.QtGui import QPixmap
        from PySide6.QtWidgets import (
            QGraphicsScene,
            QGraphicsPixmapItem,
            QGraphicsBlurEffect,
        )

        scene = QGraphicsScene()
        item = QGraphicsPixmapItem(pm)
        effect = QGraphicsBlurEffect()
        effect.setBlurRadius(16)
        effect.setBlurHints(QGraphicsBlurEffect.BlurHint.QualityHint)
        item.setGraphicsEffect(effect)
        scene.addItem(item)

        blurred = QPixmap(pm.size())
        blurred.fill(Qt.GlobalColor.transparent)
        painter = QPainter(blurred)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        scene.render(painter)
        painter.end()
        return blurred

    def paintEvent(self, event):
        if self._kind == "transparent":
            return
        # grab 期间跳过自己的绘制，避免被抢进下一轮 snapshot 造成黑色累积。
        if self._suppress_paint:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        # 整体透明度随 BackdropFade.progress 渐变
        painter.setOpacity(self._fade.progress_value())

        if self._kind == "blur" and self._blur_pixmap is not None:
            painter.drawPixmap(self.rect(), self._blur_pixmap)
            painter.fillRect(self.rect(), QColor(0, 0, 0, 76))  # 30%
        elif self._kind == "opaque":
            painter.fillRect(self.rect(), QColor(0, 0, 0, 128))  # 50%
        else:
            painter.fillRect(self.rect(), QColor(0, 0, 0, 76))

    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)

    def wheelEvent(self, event):
        """opaque/blur backdrop 默认拦截所有鼠标事件，导致用户在 popover 打开期间
        无法滚动主页面。这里把 wheel 事件抛给 Popover 处理（关闭 + 可选转发到
        祖先 ScrollArea）。

        accept 让 Qt 不再向上冒泡 —— 我们自己已经决定了如何处理。
        """
        # transparent 模式不会进到这里（WA_TransparentForMouseEvents=True，
        # wheelEvent 都不会派发给我们）。
        # 只传 angleDelta（主要轴 + 方向），Popover 重建事件转发。
        self.wheel_scrolled.emit(event.angleDelta())
        event.accept()
