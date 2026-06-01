"""HeroSideUI Image — HeroUI v2 Image 组件 PySide6 复刻。

样式来源:  https://github.com/heroui-inc/heroui/blob/main/packages/core/theme/src/components/image.ts
组件来源:  https://github.com/heroui-inc/heroui/tree/main/packages/components/image

结构:
    Image (QWidget, wrapper)
    ├── _blurred  (BlurredImage, z=0, isBlurred=True 时存在)
    ├── _skeleton (Skeleton, z=1, 加载/loading 时显示动画)
    └── _img      (QLabel, z=2, 实际图像，hover 时 scale 1.25 ≈ isZoomed)

Skeleton 完全复用项目已有 Skeleton 组件，加载完成 set_loaded(True)。
shadow 用 QGraphicsDropShadowEffect 挂在 wrapper 上。
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import (
    Signal,
    QPropertyAnimation,
    QEasingCurve,
)
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QWidget

from ..skeleton import Skeleton
from ._loader import ImageLoader, ImageSrc
from ._blurred import BlurredImage
from ._rounded_image import _RoundedImage
from ._shadow import content_margins, make_shadow_effect

# 未传 width/height 且还未加载完成时的占位尺寸
_FALLBACK_W, _FALLBACK_H = 300, 200


class Image(QWidget):
    """HeroUI v2 风格 Image 组件。

    Args:
        src:               图源，支持本地路径 / Qt 资源路径 / http(s) URL / QPixmap / QImage
        width / height:    图像可视尺寸（int 像素），未传时按 src 原始尺寸
        radius:            none / sm / md / lg / full（默认 lg）
        shadow:            none / sm / md / lg（默认 none）
        object_fit:        cover / contain / fill / none / scale-down（默认 cover）
        is_blurred:        模糊副本背景（同图放大 1.05 + blur + saturate + opacity 0.3）
        blur_amount:       模糊强度倍率，默认 1.0（对应 10px 半径），>1 加强、<1 减弱
        is_zoomed:         hover 缩放至 zoom_factor
        zoom_factor:       isZoomed=True 时 hover 放大倍数，默认 1.25
        is_loading:        受控 loading；为 True 时强制显示 Skeleton
        disable_skeleton:  关闭 Skeleton 占位
        disable_animation: 关闭所有动画（zoom hover / fade in / shimmer）
        remove_wrapper:    去掉外层 wrapper（无 skeleton/zoom/blur/shadow 任何效果）
        fallback_src:      加载失败时显示的备用图（同 src 类型）
    """

    loaded = Signal()
    failed = Signal()

    def __init__(
        self,
        src: ImageSrc = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        radius: str = "lg",
        shadow: str = "none",
        object_fit: str = "cover",
        is_blurred: bool = False,
        blur_amount: float = 1.0,
        is_zoomed: bool = False,
        zoom_factor: float = 1.25,
        is_loading: bool = False,
        disable_skeleton: bool = False,
        disable_animation: bool = False,
        remove_wrapper: bool = False,
        fallback_src: ImageSrc = None,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.setObjectName("HeroImage")

        # 配置
        self._src = src
        self._fallback_src = fallback_src
        self._width = width
        self._height = height
        self._radius = radius
        self._shadow = shadow
        self._object_fit = object_fit
        self._is_blurred = is_blurred
        self._blur_amount = max(0.0, float(blur_amount))
        self._is_zoomed = is_zoomed
        self._zoom_factor = max(1.0, float(zoom_factor))
        self._is_loading_prop = is_loading
        # 当传入 fallback_src 时，HeroUI 默认 disableSkeleton = true
        self._disable_skeleton = disable_skeleton or fallback_src is not None
        self._disable_animation = disable_animation
        self._remove_wrapper = remove_wrapper

        # 内部状态
        self._image_status: str = "pending"  # loading / loaded / failed / pending
        self._loaded_pixmap: Optional[QPixmap] = None
        self._fallback_pixmap: Optional[QPixmap] = None

        self._setup_ui()
        self._apply_shadow()
        self._apply_size()  # 必须在 _apply_shadow 之后：宽高需要算上阴影 margin
        self._kick_load()

    # ============================================================
    # UI 构建
    # ============================================================
    def _setup_ui(self):
        # 主图层
        self._img = _RoundedImage(self)
        self._img.set_radius(self._radius)
        self._img.set_object_fit(self._object_fit)
        self._img.move(0, 0)

        # 模糊副本（按需）
        self._blurred: Optional[BlurredImage] = None
        if self._is_blurred and not self._remove_wrapper:
            self._blurred = BlurredImage(self, blur_amount=self._blur_amount)
            self._blurred.lower()  # 放最底
            self._blurred.move(0, 0)

        # Skeleton 占位（按需）
        self._skeleton: Optional[Skeleton] = None
        if not self._disable_skeleton and not self._remove_wrapper:
            self._skeleton = Skeleton(
                radius=self._radius,
                disable_animation=self._disable_animation,
                parent=self,
            )
            self._skeleton.move(0, 0)
            self._skeleton.raise_()

        # 主图层放最上
        self._img.raise_()

        # zoom 动画
        self._zoom_anim = QPropertyAnimation(self._img, b"zoomFactor")
        self._zoom_anim.setDuration(300)
        self._zoom_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        # fade-in 动画（loaded 后 opacity 0→1，对齐 transition-opacity 300ms）
        self._fade_anim = QPropertyAnimation(self._img, b"fadeOpacity")
        self._fade_anim.setDuration(300)
        self._fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        # rememove_wrapper：彻底简化为单 QLabel 行为
        if self._remove_wrapper:
            self._img.move(0, 0)

    # ============================================================
    # 加载
    # ============================================================
    def _kick_load(self):
        # 主图源
        self._loader = ImageLoader(self)
        self._loader.loaded.connect(self._on_loaded)
        self._loader.failed.connect(self._on_failed)

        # fallback 预加载（独立 loader，不影响主流程）
        if self._fallback_src is not None:
            self._fb_loader = ImageLoader(self)
            self._fb_loader.loaded.connect(self._on_fallback_loaded)
            self._fb_loader.load(self._fallback_src)

        if self._src is None:
            self._image_status = "pending"
            self._refresh_loading_ui()
            return

        self._image_status = "loading"
        self._refresh_loading_ui()
        self._loader.load(self._src)

    def _on_loaded(self, pm: QPixmap):
        self._image_status = "loaded"
        self._loaded_pixmap = pm
        self._img.set_source_pixmap(pm)
        if self._blurred is not None:
            self._blurred.set_source(pm)
        # 依原图尺寸自适应 wrapper（仅当用户未显式传 width/height）
        self._apply_natural_size_from(pm)
        self._refresh_loading_ui()
        self._fade_in()
        self.loaded.emit()

    def _on_failed(self):
        self._image_status = "failed"
        # 失败时 wrapper 显示 fallback（QPixmap 形式 _fallback_pixmap）
        self._refresh_loading_ui()
        self.failed.emit()

    def _on_fallback_loaded(self, pm: QPixmap):
        self._fallback_pixmap = pm
        # 仅当主图未加载成功时才让 fallback 上屏
        if self._image_status != "loaded":
            self._img.set_source_pixmap(pm)
            self._img.fadeOpacity = 1.0
            # fallback 上屏同样需要重算原图尺寸
            self._apply_natural_size_from(pm)
            self.update()

    # ============================================================
    # 状态 → UI
    # ============================================================
    def _is_loading_now(self) -> bool:
        return self._image_status == "loading" or self._is_loading_prop

    def _show_skeleton(self) -> bool:
        return self._is_loading_now() and not self._disable_skeleton

    def _refresh_loading_ui(self):
        if self._skeleton is None:
            return
        loading = self._show_skeleton()
        self._skeleton.set_loaded(not loading)
        if loading:
            self._skeleton.raise_()
        # 加载完成后让出 mouse 与 z 顺序
        if not loading:
            self._img.raise_()

    def _fade_in(self):
        if self._disable_animation:
            self._img.fadeOpacity = 1.0
            return
        self._fade_anim.stop()
        self._fade_anim.setStartValue(self._img.fadeOpacity)
        self._fade_anim.setEndValue(1.0)
        self._fade_anim.start()

    # ============================================================
    # 阴影
    # ============================================================
    def _apply_shadow(self):
        """应用 QGraphicsDropShadowEffect，无阴影时清空。"""
        eff = make_shadow_effect(self, self._shadow, self._remove_wrapper)
        self.setGraphicsEffect(eff)

    def _content_margins(self) -> tuple:
        """返回 (top, right, bottom, left) 四向独立 margin。"""
        return content_margins(self._shadow, self._is_blurred, self._remove_wrapper)

    # ============================================================
    # 尺寸
    # ============================================================
    def _apply_size(self):
        """用户传的 width/height 是图像可视尺寸，wrapper 多包一圈 margin。"""
        mt, mr, mb, ml = self._content_margins()
        mh, mv = ml + mr, mt + mb
        if self._width is not None:
            self.setFixedWidth(self._width + mh)
        if self._height is not None:
            self.setFixedHeight(self._height + mv)
        # 两边都未传：先给占位尺寸，避免初期 0×0
        if self._width is None and self._height is None:
            self.setFixedSize(_FALLBACK_W + mh, _FALLBACK_H + mv)

    def _apply_natural_size_from(self, pm: QPixmap):
        """加载完成后按原图尺寸/比例自适应 wrapper。仅影响未显式传尺寸的侧。"""
        if pm is None or pm.isNull():
            return
        mt, mr, mb, ml = self._content_margins()
        mh, mv = ml + mr, mt + mb
        nw, nh = pm.width(), pm.height()
        if nw <= 0 or nh <= 0:
            return
        if self._width is None and self._height is None:
            self.setFixedSize(nw + mh, nh + mv)
        elif self._width is None:
            self.setFixedWidth(int(self._height * nw / nh) + mh)
        elif self._height is None:
            self.setFixedHeight(int(self._width * nh / nw) + mv)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        w, h = self.width(), self.height()
        mt, mr, mb, ml = self._content_margins()
        # 可视图像区域按四向 margin 独立分配
        cw = max(0, w - ml - mr)
        ch = max(0, h - mt - mb)

        self._img.setGeometry(ml, mt, cw, ch)

        if self._skeleton is not None:
            self._skeleton.setGeometry(ml, mt, cw, ch)

        if self._blurred is not None:
            # scale 1.18 + translate-y 6，打出明显的下方光晕
            scale = 1.18
            ext_w = int(cw * scale)
            ext_h = int(ch * scale)
            offset_x = ml + (cw - ext_w) // 2
            offset_y = mt + (ch - ext_h) // 2 + 6
            self._blurred.setGeometry(offset_x, offset_y, ext_w, ext_h)

    # ============================================================
    # hover (isZoomed)
    # ============================================================
    def enterEvent(self, event):
        if self._is_zoomed and self._image_status == "loaded":
            self._zoom_anim.stop()
            self._zoom_anim.setStartValue(self._img.zoomFactor)
            self._zoom_anim.setEndValue(self._zoom_factor)
            if self._disable_animation:
                self._img.zoomFactor = self._zoom_factor
            else:
                self._zoom_anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        if self._is_zoomed:
            self._zoom_anim.stop()
            self._zoom_anim.setStartValue(self._img.zoomFactor)
            self._zoom_anim.setEndValue(1.0)
            if self._disable_animation:
                self._img.zoomFactor = 1.0
            else:
                self._zoom_anim.start()
        super().leaveEvent(event)

    # ============================================================
    # 公共 API
    # ============================================================
    def set_src(self, src: ImageSrc):
        self._src = src
        self._image_status = "loading" if src is not None else "pending"
        self._loaded_pixmap = None
        self._img.set_source_pixmap(None)
        self._img.fadeOpacity = 0.0
        self._refresh_loading_ui()
        if src is not None:
            self._loader.load(src)

    def set_is_loading(self, loading: bool):
        self._is_loading_prop = loading
        self._refresh_loading_ui()

    def set_radius(self, r: str):
        self._radius = r
        self._img.set_radius(r)
        if self._skeleton is not None:
            self._skeleton.set_radius(r)
        self.update()

    def set_shadow(self, s: str):
        self._shadow = s
        self._apply_shadow()
        # shadow 档位变化会改变 _shadow_margin，wrapper 整体尺寸需要重算
        self._apply_size()
        # 触发一次 resizeEvent 让所有图层重新分配几何
        self.resizeEvent(None)

    def set_is_zoomed(self, v: bool):
        self._is_zoomed = v
        if not v:
            self._img.zoomFactor = 1.0

    def set_zoom_factor(self, v: float):
        """调整 isZoomed=True 时 hover 的放大倍数（>= 1.0）。"""
        self._zoom_factor = max(1.0, float(v))

    def set_object_fit(self, fit: str):
        """设置裁剪模式：cover / contain / fill / none / scale-down。"""
        self._object_fit = fit
        self._img.set_object_fit(fit)

    def set_is_blurred(self, v: bool):
        if v == self._is_blurred:
            return
        self._is_blurred = v
        if v and self._blurred is None:
            self._blurred = BlurredImage(self, blur_amount=self._blur_amount)
            self._blurred.lower()
            if self._loaded_pixmap is not None:
                self._blurred.set_source(self._loaded_pixmap)
            self._blurred.show()
        elif not v and self._blurred is not None:
            self._blurred.deleteLater()
            self._blurred = None
        # 动态切换后重算 wrapper 尺寸与子控件布局
        self._apply_size()
        self.resizeEvent(None)

    def set_blur_amount(self, amount: float):
        """调整模糊强度倍率（1.0 = 默认，>1 加强，<1 减弱）。"""
        self._blur_amount = max(0.0, float(amount))
        if self._blurred is not None:
            self._blurred.set_blur_amount(self._blur_amount)

    def set_disable_skeleton(self, v: bool):
        self._disable_skeleton = v
        self._refresh_loading_ui()

    def is_loading(self) -> bool:
        return self._is_loading_now()

    def status(self) -> str:
        return self._image_status

    def pixmap(self) -> Optional[QPixmap]:
        return self._loaded_pixmap


__all__ = ["Image"]
