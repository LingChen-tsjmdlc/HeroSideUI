"""Image 组件：wrapper 内 blurred 副本 + Skeleton 占位 + 圆角图像三层。
shadow 走 QGraphicsDropShadowEffect 挂 wrapper。
"""

from __future__ import annotations

from PySide6.QtCore import (
    Signal,
)
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QWidget

from ...animation import tween_property
from ..skeleton import Skeleton
from ._blurred import BlurredImage
from ._loader import ImageLoader, ImageSrc
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
        width: int | None = None,
        height: int | None = None,
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
        parent: QWidget | None = None,
    ):
        """创建图像组件：模糊副本 + Skeleton 占位 + 圆角主图层。

        Args:
            src: 图源，支持本地路径 / Qt 资源 / http(s) URL / QPixmap / QImage。
            width: 图像可视宽度（像素）；None 按原图自适应。
            height: 图像可视高度（像素）；None 按原图自适应。
            radius: none / sm / md / lg / full。
            shadow: none / sm / md / lg。
            object_fit: cover / contain / fill / none / scale-down。
            is_blurred: 是否叠加模糊副本背景。
            blur_amount: 模糊强度倍率（1.0 对应 10px 半径）。
            is_zoomed: hover 时是否放大。
            zoom_factor: hover 放大倍数（下限 1.0）。
            is_loading: 受控 loading；True 时强制显示 Skeleton。
            disable_skeleton: 关闭 Skeleton 占位。
            disable_animation: 关闭 zoom / fade / shimmer 动画。
            remove_wrapper: 去掉外层 wrapper，退化为单 QLabel 行为。
            fallback_src: 加载失败时显示的备用图。
            parent: Qt 父对象。

        Note:
            传了 fallback_src 时按 HeroUI 语义默认禁用 Skeleton；
            _apply_size 必须在 _apply_shadow 之后调用，宽高需算上阴影 margin。
        """
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
        self._loaded_pixmap: QPixmap | None = None
        self._fallback_pixmap: QPixmap | None = None

        self._setup_ui()
        self._apply_shadow()
        self._apply_size()  # 必须在 _apply_shadow 之后：宽高需要算上阴影 margin
        self._kick_load()

    # ============================================================
    # UI 构建
    # ============================================================
    def _setup_ui(self):
        """搭建主图层、模糊副本与 Skeleton 三层并定好 z 序。

        Note:
            remove_wrapper 时彻底简化为单 QLabel 行为；
            主图层始终 raise_() 置于最上。
        """
        # 主图层
        self._img = _RoundedImage(self)
        self._img.set_radius(self._radius)
        self._img.set_object_fit(self._object_fit)
        self._img.move(0, 0)

        # 模糊副本（按需）
        self._blurred: BlurredImage | None = None
        if self._is_blurred and not self._remove_wrapper:
            self._blurred = BlurredImage(self, blur_amount=self._blur_amount)
            self._blurred.lower()  # 放最底
            self._blurred.move(0, 0)

        # Skeleton 占位（按需）
        self._skeleton: Skeleton | None = None
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
        self._zoom_anim = None

        # fade-in 动画（loaded 后 opacity 0→1，对齐 transition-opacity 300ms）
        self._fade_anim = None

        # rememove_wrapper：彻底简化为单 QLabel 行为
        if self._remove_wrapper:
            self._img.move(0, 0)

    # ============================================================
    # 加载
    # ============================================================
    def _kick_load(self):
        """创建主 / fallback 加载器并启动加载。

        Note:
            fallback 用独立 loader 预加载，不影响主流程；
            src 为 None 时停在 pending 并刷新占位 UI。
        """
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
        """主图加载成功：上屏、自适应尺寸、fade-in 并发 loaded。

        Args:
            pm: 加载完成的 QPixmap。
        """
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
        """主图加载失败：转 failed 态、刷新占位并发 failed。"""
        self._image_status = "failed"
        # 失败时 wrapper 显示 fallback（QPixmap 形式 _fallback_pixmap）
        self._refresh_loading_ui()
        self.failed.emit()

    def _on_fallback_loaded(self, pm: QPixmap):
        """备用图预加载完成。

        Args:
            pm: 备用图 QPixmap。

        Note:
            仅当主图尚未加载成功时才让 fallback 上屏，并同步重算尺寸。
        """
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
        """当前是否处于加载态。

        Returns:
            内部 status 为 loading 或外部受控 is_loading 为 True 时返回 True。
        """
        return self._image_status == "loading" or self._is_loading_prop

    def _show_skeleton(self) -> bool:
        """是否应显示 Skeleton 占位。

        Returns:
            加载中且未禁用 Skeleton 时为 True。
        """
        return self._is_loading_now() and not self._disable_skeleton

    def _refresh_loading_ui(self):
        """按加载态切换 Skeleton 显隐并调整 z 序。

        Note:
            加载完成后让出 mouse 与 z 顺序，把主图层 raise_() 置顶。
        """
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
        """播放主图层 opacity 0→1 淡入（对齐 CSS 300ms）。"""
        tween_property(
            self._img,
            "_fade_anim",
            b"fadeOpacity",
            1.0,
            owner=self,
            duration=300,
            animated=not self._disable_animation,
        )

    # ============================================================
    # 阴影
    # ============================================================
    def _apply_shadow(self):
        """应用 QGraphicsDropShadowEffect，无阴影时清空。"""
        eff = make_shadow_effect(self, self._shadow, self._remove_wrapper)
        self.setGraphicsEffect(eff)

    def _content_margins(self) -> tuple:
        """返回 (top, right, bottom, left) 四向独立 margin。

        Returns:
            阴影与模糊副本需求逐向取最大值后的四元组。
        """
        return content_margins(self._shadow, self._is_blurred, self._remove_wrapper)

    # ============================================================
    # 尺寸
    # ============================================================
    def _apply_size(self):
        """用户传的 width/height 是图像可视尺寸，wrapper 多包一圈 margin。

        Note:
            两边都未传时先给 300×200 占位尺寸，避免初期 0×0。
        """
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
        """加载完成后按原图尺寸 / 比例自适应 wrapper。

        Args:
            pm: 已加载的 QPixmap。

        Note:
            仅影响未显式传尺寸的那一侧；空图或零尺寸直接返回。
        """
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
        """尺寸变化后按四向 margin 重新分配三层几何。

        Args:
            event: Qt 尺寸变化事件；set_shadow / set_is_blurred 会以 None
                主动调用本方法触发重排。

        Note:
            模糊副本按 1.18 倍放大并下移 6px，打出明显的下方光晕。
        """
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
        """鼠标进入：isZoomed 且已加载时播放放大补间。

        Args:
            event: Qt 进入事件。
        """
        if self._is_zoomed and self._image_status == "loaded":
            tween_property(
                self._img,
                "_zoom_anim",
                b"zoomFactor",
                self._zoom_factor,
                owner=self,
                duration=300,
                animated=not self._disable_animation,
            )
        super().enterEvent(event)

    def leaveEvent(self, event):
        """鼠标离开：isZoomed 时回落到 1.0 倍。

        Args:
            event: Qt 离开事件。
        """
        if self._is_zoomed:
            tween_property(
                self._img,
                "_zoom_anim",
                b"zoomFactor",
                1.0,
                owner=self,
                duration=300,
                animated=not self._disable_animation,
            )
        super().leaveEvent(event)

    # ============================================================
    # 公共 API
    # ============================================================
    def set_src(self, src: ImageSrc):
        """替换图源并重新加载。

        Args:
            src: 新图源；None 回到 pending 并清空当前图像。
        """
        self._src = src
        self._image_status = "loading" if src is not None else "pending"
        self._loaded_pixmap = None
        self._img.set_source_pixmap(None)
        self._img.fadeOpacity = 0.0
        self._refresh_loading_ui()
        if src is not None:
            self._loader.load(src)

    def set_is_loading(self, loading: bool):
        """切换受控 loading 态。

        Args:
            loading: True 时强制显示 Skeleton。
        """
        self._is_loading_prop = loading
        self._refresh_loading_ui()

    def set_radius(self, r: str):
        """切换圆角档位并联动主图层与 Skeleton。

        Args:
            r: 圆角档位名。
        """
        self._radius = r
        self._img.set_radius(r)
        if self._skeleton is not None:
            self._skeleton.set_radius(r)
        self.update()

    def set_shadow(self, s: str):
        """切换阴影档位并重算尺寸与图层几何。

        Args:
            s: 阴影档位名。

        Note:
            阴影档位变化会改变 margin，wrapper 整体尺寸需重算，
            并主动触发一次 resizeEvent 让所有图层重新分配几何。
        """
        self._shadow = s
        self._apply_shadow()
        # shadow 档位变化会改变 _shadow_margin，wrapper 整体尺寸需要重算
        self._apply_size()
        # 触发一次 resizeEvent 让所有图层重新分配几何
        self.resizeEvent(None)

    def set_is_zoomed(self, v: bool):
        """切换 hover 放大开关。

        Args:
            v: False 时立即把缩放复位到 1.0。
        """
        self._is_zoomed = v
        if not v:
            self._img.zoomFactor = 1.0

    def set_zoom_factor(self, v: float):
        """调整 isZoomed=True 时 hover 的放大倍数。

        Args:
            v: 目标倍数，下限钳制为 1.0。
        """
        self._zoom_factor = max(1.0, float(v))

    def set_object_fit(self, fit: str):
        """设置裁剪模式。

        Args:
            fit: cover / contain / fill / none / scale-down。
        """
        self._object_fit = fit
        self._img.set_object_fit(fit)

    def set_is_blurred(self, v: bool):
        """切换模糊副本图层并按需创建 / 销毁。

        Args:
            v: True 时补建 BlurredImage 并把已加载的图喂给它。

        Note:
            动态切换后需重算 wrapper 尺寸与子控件布局。
        """
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
        """调整模糊强度倍率。

        Args:
            amount: 1.0 为默认，>1 加强、<1 减弱；负值按 0 处理。
        """
        self._blur_amount = max(0.0, float(amount))
        if self._blurred is not None:
            self._blurred.set_blur_amount(self._blur_amount)

    def set_disable_skeleton(self, v: bool):
        """切换是否禁用 Skeleton 占位。

        Args:
            v: True 时加载中不再显示 Skeleton。
        """
        self._disable_skeleton = v
        self._refresh_loading_ui()

    def is_loading(self) -> bool:
        """返回当前是否处于加载态。

        Returns:
            True 表示加载中或受控 loading 为 True。
        """
        return self._is_loading_now()

    def status(self) -> str:
        """返回当前加载状态。

        Returns:
            pending / loading / loaded / failed。
        """
        return self._image_status

    def pixmap(self) -> QPixmap | None:
        """返回已加载的主图。

        Returns:
            当前 QPixmap；未加载成功时为 None。
        """
        return self._loaded_pixmap


__all__ = ["Image"]
