"""浮层家族共用的全屏遮罩，供 Popover 与 Drawer 使用。"""

from typing import ClassVar

from PySide6.QtCore import QEvent, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QPainter, QPixmap
from PySide6.QtWidgets import (
    QGraphicsBlurEffect,
    QGraphicsPixmapItem,
    QGraphicsScene,
    QWidget,
)

from ...animation import BackdropFade


class Backdrop(QWidget):
    """覆盖宿主客户区的遮罩，作为宿主的子控件存在。

    Attributes:
        clicked: 点击遮罩时发出，是否关闭由使用者决定。
        wheel_scrolled: 遮罩上滚轮滚动时发出，携带 angleDelta(QPoint)。
    """

    # blur_quality 到金字塔级数的映射；high 使用 QGraphicsBlurEffect。
    _PYRAMID_LEVELS: ClassVar[dict[str, int]] = {"low": 2, "fast": 3, "great": 4}
    _VALID_QUALITY = ("low", "fast", "great", "high")

    clicked = Signal()
    wheel_scrolled = Signal(object)

    def __init__(
        self,
        kind: str = "transparent",
        host: QWidget | None = None,
        blur_quality: str = "fast",
    ):
        """构造遮罩。

        Args:
            kind: transparent 透明且鼠标穿透 / opaque 黑色 50% / blur 模糊快照叠加黑色 30%。
            host: 宿主窗口，同时作为父控件限定遮罩范围。
            blur_quality: low、fast、great 使用金字塔模糊，high 使用高斯模糊。

        Raises:
            ValueError: blur_quality 不在支持的档位内。
        """
        super().__init__(host)
        if blur_quality not in self._VALID_QUALITY:
            raise ValueError(
                f"blur_quality must be one of {self._VALID_QUALITY}, got {blur_quality!r}"
            )
        self._kind = kind
        self._host = host
        self._blur_quality = blur_quality
        self._blur_pixmap: QPixmap | None = None
        # 抓取宿主快照期间跳过自身绘制，避免遮罩叠入快照后逐帧变黑。
        self._suppress_paint = False

        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, kind == "transparent")

        self._fade = BackdropFade(owner=self, duration_in=260, duration_out=200)

        # 宿主缩放期间每 50ms 重抓一次模糊，停止缩放 120ms 后补一次最终刷新。
        self._blur_throttle_timer = QTimer(self)
        self._blur_throttle_timer.setInterval(50)
        self._blur_throttle_timer.timeout.connect(self._on_blur_throttle_tick)

        self._blur_settle_timer = QTimer(self)
        self._blur_settle_timer.setSingleShot(True)
        self._blur_settle_timer.setInterval(120)
        self._blur_settle_timer.timeout.connect(self._on_resize_settled)
        if host is not None:
            host.installEventFilter(self)

    def eventFilter(self, obj, event):
        """跟随宿主尺寸变化同步几何，并在 blur 模式下节流重抓快照。"""
        if obj is self._host and event.type() == QEvent.Type.Resize:
            try:
                self.setGeometry(0, 0, self._host.width(), self._host.height())
            except RuntimeError:
                return super().eventFilter(obj, event)
            if self._kind == "blur":
                if not self._blur_throttle_timer.isActive():
                    self._blur_throttle_timer.start()
                self._blur_settle_timer.start()
        return super().eventFilter(obj, event)

    def _on_blur_throttle_tick(self):
        """缩放期间的节流帧：重抓模糊快照。"""
        if self._host is not None and self._kind == "blur":
            self.refresh_blur_fast()

    def _on_resize_settled(self):
        """缩放停止后：结束节流并补一次最终刷新。"""
        self._blur_throttle_timer.stop()
        if self._host is not None and self._kind == "blur":
            self.refresh_blur_fast()

    def closeEvent(self, event):
        """关闭时移除宿主上的事件过滤器，避免遗留悬空引用。"""
        if self._host is not None:
            try:
                self._host.removeEventFilter(self)
            except RuntimeError:
                pass
        super().closeEvent(event)

    def play_in(self):
        """播放淡入。"""
        self._fade.play_in()

    def play_out(self):
        """播放淡出；淡出完成后由使用者负责删除遮罩。"""
        self._fade.play_out()

    def settle(self, value: float):
        """停止过渡并直接定位到终态。

        Args:
            value: 目标进度，0 为全透明，1 为完全显示。
        """
        self._fade.settle(value)

    def prepare_blur_snapshot(self):
        """在遮罩显示前抓取宿主并生成模糊快照。"""
        pm = self._grab_host()
        if pm is not None:
            self._blur_pixmap = self._apply_gaussian_blur(pm)

    def refresh_blur_fast(self):
        """重抓宿主并刷新模糊快照；high 使用高斯，其余使用金字塔滤波。"""
        if self._kind != "blur":
            return
        pm = self._grab_host()
        if pm is None:
            return
        if self._blur_quality == "high":
            blurred = self._apply_gaussian_blur(pm)
        else:
            levels = self._PYRAMID_LEVELS[self._blur_quality]
            blurred = self._apply_pyramid_box_blur(pm, pm.width(), pm.height(), levels)
        self._blur_pixmap = blurred
        self.update()

    def _grab_host(self) -> QPixmap | None:
        """抓取宿主画面，期间不绘制遮罩自身。

        Returns:
            宿主截图；宿主缺失、已销毁或截图为空时为 None。
        """
        if self._host is None:
            return None
        self._suppress_paint = True
        try:
            pm = self._host.grab()
        except RuntimeError:
            return None
        finally:
            self._suppress_paint = False
        if pm.isNull() or pm.width() <= 0 or pm.height() <= 0:
            return None
        return pm

    @staticmethod
    def _apply_pyramid_box_blur(pm: QPixmap, w: int, h: int, levels: int) -> QPixmap:
        """逐级缩小再还原的金字塔盒滤波。

        Args:
            pm: 待模糊的截图。
            w: 目标宽度。
            h: 目标高度。
            levels: 缩放级数，2 到 4。

        Returns:
            与原尺寸一致的模糊图。
        """
        smooth = Qt.TransformationMode.SmoothTransformation
        keep = Qt.AspectRatioMode.IgnoreAspectRatio

        downs = [pm]
        cw, ch = w, h
        for _ in range(levels):
            cw, ch = max(1, cw // 2), max(1, ch // 2)
            downs.append(downs[-1].scaled(cw, ch, keep, smooth))

        cur = downs[-1]
        for i in range(levels - 1, 0, -1):
            cur = cur.scaled(downs[i].width(), downs[i].height(), keep, smooth)
        return cur.scaled(w, h, keep, smooth)

    @staticmethod
    def _apply_gaussian_blur(pm: QPixmap) -> QPixmap:
        """使用 QGraphicsBlurEffect 生成高斯模糊图。

        Args:
            pm: 待模糊的截图。

        Returns:
            与原尺寸一致的模糊图。
        """
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
        """按 kind 绘制模糊快照或半透明黑色覆盖，透明度跟随淡入淡出进度。"""
        if self._kind == "transparent" or self._suppress_paint:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setOpacity(self._fade.progress_value())

        if self._kind == "blur" and self._blur_pixmap is not None:
            painter.drawPixmap(self.rect(), self._blur_pixmap)
            painter.fillRect(self.rect(), QColor(0, 0, 0, 76))
        elif self._kind == "opaque":
            painter.fillRect(self.rect(), QColor(0, 0, 0, 128))
        else:
            painter.fillRect(self.rect(), QColor(0, 0, 0, 76))

    def mousePressEvent(self, event):
        """点击遮罩时发出 clicked。"""
        self.clicked.emit()
        super().mousePressEvent(event)

    def wheelEvent(self, event):
        """转发滚轮增量并拦截事件，不向祖先冒泡。"""
        self.wheel_scrolled.emit(event.angleDelta())
        event.accept()
