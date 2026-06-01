"""Image 组件单元测试

不触网：远程 URL 分支由 `_loader.py` 负责，本文件只覆盖
QPixmap / 本地路径（含失败）两条同步分支与组件的公共契约。
"""

from __future__ import annotations

import pytest
from PySide6.QtGui import QColor, QPixmap

from hero_side_ui import Image

RADII = ("none", "sm", "md", "lg", "full")
SHADOWS = ("none", "sm", "md", "lg")
OBJECT_FITS = ("cover", "contain", "fill", "none", "scale-down")


def _make_pixmap(w: int = 80, h: int = 60, color: str = "#3366cc") -> QPixmap:
    """构造一张纯色 QPixmap，用作可控 src，无需文件 IO。"""
    pm = QPixmap(w, h)
    pm.fill(QColor(color))
    return pm


# ============================================================
# 构造
# ============================================================
class TestImageInit:
    """构造、默认值、不同参数组合。"""

    def test_default_no_args(self, qtbot):
        img = Image()
        qtbot.addWidget(img)
        assert img._radius == "lg"
        assert img._shadow == "none"
        assert img._object_fit == "cover"
        assert img._is_blurred is False
        assert img._is_zoomed is False
        assert img._zoom_factor == pytest.approx(1.25)
        assert img._blur_amount == pytest.approx(1.0)
        assert img._disable_animation is False
        assert img._remove_wrapper is False
        assert img._image_status == "pending"

    def test_custom_params(self, qtbot):
        img = Image(
            radius="sm",
            shadow="lg",
            object_fit="contain",
            is_blurred=True,
            blur_amount=2.0,
            is_zoomed=True,
            zoom_factor=1.5,
            disable_animation=True,
        )
        qtbot.addWidget(img)
        assert img._radius == "sm"
        assert img._shadow == "lg"
        assert img._object_fit == "contain"
        assert img._is_blurred is True
        assert img._blur_amount == pytest.approx(2.0)
        assert img._is_zoomed is True
        assert img._zoom_factor == pytest.approx(1.5)
        assert img._disable_animation is True

    def test_zoom_factor_clamped_to_min_1(self, qtbot):
        # zoom_factor < 1.0 时被夹到 1.0（避免反向缩小）
        img = Image(zoom_factor=0.5)
        qtbot.addWidget(img)
        assert img._zoom_factor == pytest.approx(1.0)

    def test_blur_amount_clamped_to_non_negative(self, qtbot):
        img = Image(blur_amount=-2.0)
        qtbot.addWidget(img)
        assert img._blur_amount == pytest.approx(0.0)

    def test_fallback_forces_disable_skeleton(self, qtbot):
        # 传 fallback_src 时组件强制关闭 skeleton（与 HeroUI 行为对齐）
        img = Image(fallback_src=_make_pixmap())
        qtbot.addWidget(img)
        assert img._disable_skeleton is True
        assert img._skeleton is None
        # fallback loader 内部 QTimer.singleShot 已投递，让它跑完再清理 fixture
        qtbot.wait(20)

    def test_remove_wrapper_no_skeleton_no_blurred(self, qtbot):
        img = Image(remove_wrapper=True, is_blurred=True)
        qtbot.addWidget(img)
        assert img._skeleton is None
        assert img._blurred is None
        # remove_wrapper 同时禁用阴影 effect
        assert img.graphicsEffect() is None

    def test_blurred_layer_created(self, qtbot):
        img = Image(is_blurred=True)
        qtbot.addWidget(img)
        assert img._blurred is not None

    def test_skeleton_default_present(self, qtbot):
        img = Image()
        qtbot.addWidget(img)
        assert img._skeleton is not None


# ============================================================
# 圆角
# ============================================================
class TestImageRadius:
    @pytest.mark.parametrize("radius", RADII)
    def test_all_radii(self, qtbot, radius):
        img = Image(radius=radius)
        qtbot.addWidget(img)
        assert img._radius == radius
        # 主图层与 skeleton 应同步使用相同 radius
        assert img._img._radius == radius


# ============================================================
# 阴影
# ============================================================
class TestImageShadow:
    @pytest.mark.parametrize("shadow", SHADOWS)
    def test_all_shadows(self, qtbot, shadow):
        img = Image(shadow=shadow)
        qtbot.addWidget(img)
        assert img._shadow == shadow

    def test_shadow_none_no_effect(self, qtbot):
        img = Image(shadow="none")
        qtbot.addWidget(img)
        assert img.graphicsEffect() is None

    def test_shadow_lg_attaches_effect(self, qtbot):
        img = Image(shadow="lg")
        qtbot.addWidget(img)
        assert img.graphicsEffect() is not None


# ============================================================
# object-fit
# ============================================================
class TestImageObjectFit:
    @pytest.mark.parametrize("fit", OBJECT_FITS)
    def test_all_fits(self, qtbot, fit):
        img = Image(object_fit=fit)
        qtbot.addWidget(img)
        assert img._object_fit == fit
        assert img._img._object_fit == fit


# ============================================================
# 同步加载（QPixmap / 本地路径失败）
# ============================================================
class TestImageLoading:
    """覆盖 ImageLoader 的同步分支：QPixmap 直传 与 本地路径失败。"""

    def test_load_pixmap_emits_loaded(self, qtbot):
        pm = _make_pixmap(120, 80)
        img = Image(src=pm)
        qtbot.addWidget(img)

        with qtbot.waitSignal(img.loaded, timeout=1000):
            pass

        assert img.status() == "loaded"
        assert img.pixmap() is not None
        assert not img.pixmap().isNull()
        assert img.is_loading() is False

    def test_load_invalid_local_path_emits_failed(self, qtbot):
        img = Image(src="this_path_does_not_exist_xyz.png")
        qtbot.addWidget(img)

        with qtbot.waitSignal(img.failed, timeout=1000):
            pass

        assert img.status() == "failed"
        assert img.pixmap() is None

    def test_natural_size_applied_after_load(self, qtbot):
        # 未传 width/height 时，加载完成后 wrapper 应按原图比例 + margin 展开
        pm = _make_pixmap(160, 90)
        img = Image(src=pm, shadow="none")  # shadow=none 时四向 margin = 0
        qtbot.addWidget(img)

        with qtbot.waitSignal(img.loaded, timeout=1000):
            pass

        # shadow=none 时 margin=0，wrapper 尺寸 = 原图尺寸
        assert img.width() == 160
        assert img.height() == 90

    def test_fallback_takes_over_when_main_fails(self, qtbot):
        # 主图加载失败 → fallback_src（QPixmap）顶替上屏
        fallback = _make_pixmap(50, 50, "#ff0000")
        img = Image(src="missing.png", fallback_src=fallback)
        qtbot.addWidget(img)

        # 主图先 failed
        with qtbot.waitSignal(img.failed, timeout=1000):
            pass
        # fallback 是异步发出的，等一帧让它上屏
        qtbot.wait(50)
        # 主图 status 仍是 failed，但 _img 已挂载 fallback pixmap
        assert img.status() == "failed"
        assert img._img._pixmap is not None
        assert not img._img._pixmap.isNull()


# ============================================================
# 受控 loading
# ============================================================
class TestImageControlledLoading:
    def test_is_loading_prop_forces_skeleton(self, qtbot):
        pm = _make_pixmap()
        img = Image(src=pm, is_loading=True)
        qtbot.addWidget(img)
        with qtbot.waitSignal(img.loaded, timeout=1000):
            pass
        # 受控 loading=True 时，即便实际已 loaded 也仍视为 loading
        assert img.is_loading() is True

    def test_set_is_loading_releases(self, qtbot):
        pm = _make_pixmap()
        img = Image(src=pm, is_loading=True)
        qtbot.addWidget(img)
        with qtbot.waitSignal(img.loaded, timeout=1000):
            pass

        img.set_is_loading(False)
        assert img.is_loading() is False


# ============================================================
# 动态 setter
# ============================================================
class TestImageSetters:
    def test_set_radius(self, qtbot):
        img = Image(radius="sm")
        qtbot.addWidget(img)
        img.set_radius("full")
        assert img._radius == "full"
        assert img._img._radius == "full"

    def test_set_shadow_attaches_then_clears(self, qtbot):
        img = Image(shadow="none")
        qtbot.addWidget(img)
        img.set_shadow("lg")
        assert img._shadow == "lg"
        assert img.graphicsEffect() is not None

        img.set_shadow("none")
        assert img._shadow == "none"
        assert img.graphicsEffect() is None

    def test_set_object_fit(self, qtbot):
        img = Image(object_fit="cover")
        qtbot.addWidget(img)
        img.set_object_fit("contain")
        assert img._object_fit == "contain"
        assert img._img._object_fit == "contain"

    def test_set_is_zoomed(self, qtbot):
        img = Image()
        qtbot.addWidget(img)
        img.set_is_zoomed(True)
        assert img._is_zoomed is True
        # 关闭 zoom 时 zoomFactor 立刻回 1.0
        img.set_is_zoomed(False)
        assert img._img.zoomFactor == pytest.approx(1.0)

    def test_set_zoom_factor_clamped(self, qtbot):
        img = Image()
        qtbot.addWidget(img)
        img.set_zoom_factor(2.0)
        assert img._zoom_factor == pytest.approx(2.0)
        img.set_zoom_factor(0.3)  # < 1.0 被夹到 1.0
        assert img._zoom_factor == pytest.approx(1.0)

    def test_set_is_blurred_toggle(self, qtbot):
        img = Image()
        qtbot.addWidget(img)
        assert img._blurred is None

        img.set_is_blurred(True)
        assert img._is_blurred is True
        assert img._blurred is not None

        img.set_is_blurred(False)
        assert img._is_blurred is False
        assert img._blurred is None

    def test_set_is_blurred_idempotent(self, qtbot):
        # 同状态再次设置不应炸
        img = Image(is_blurred=True)
        qtbot.addWidget(img)
        img.set_is_blurred(True)
        assert img._is_blurred is True

    def test_set_blur_amount(self, qtbot):
        img = Image(is_blurred=True)
        qtbot.addWidget(img)
        img.set_blur_amount(0.5)
        assert img._blur_amount == pytest.approx(0.5)

    def test_set_disable_skeleton(self, qtbot):
        img = Image()
        qtbot.addWidget(img)
        img.set_disable_skeleton(True)
        assert img._disable_skeleton is True

    def test_set_src_resets_state(self, qtbot):
        pm1 = _make_pixmap(10, 10, "#ff0000")
        pm2 = _make_pixmap(20, 20, "#00ff00")
        img = Image(src=pm1)
        qtbot.addWidget(img)
        with qtbot.waitSignal(img.loaded, timeout=1000):
            pass
        assert img.status() == "loaded"

        # 切换 src 后应触发新一轮 loaded
        with qtbot.waitSignal(img.loaded, timeout=1000):
            img.set_src(pm2)
        assert img.status() == "loaded"
        assert img.pixmap() is not None
        assert img.pixmap().width() == 20


# ============================================================
# 组合
# ============================================================
class TestImageCombinations:
    @pytest.mark.parametrize("radius", ("none", "lg", "full"))
    @pytest.mark.parametrize("shadow", SHADOWS)
    def test_radius_x_shadow_smoke(self, qtbot, radius, shadow):
        img = Image(radius=radius, shadow=shadow, src=_make_pixmap())
        qtbot.addWidget(img)
        with qtbot.waitSignal(img.loaded, timeout=1000):
            pass
        assert img._radius == radius
        assert img._shadow == shadow

    def test_blurred_plus_shadow(self, qtbot):
        img = Image(is_blurred=True, shadow="md", src=_make_pixmap())
        qtbot.addWidget(img)
        with qtbot.waitSignal(img.loaded, timeout=1000):
            pass
        assert img._blurred is not None
        assert img.graphicsEffect() is not None

    def test_remove_wrapper_with_pixmap(self, qtbot):
        pm = _make_pixmap()
        img = Image(src=pm, remove_wrapper=True)
        qtbot.addWidget(img)
        with qtbot.waitSignal(img.loaded, timeout=1000):
            pass
        assert img._skeleton is None
        assert img._blurred is None
        assert img.graphicsEffect() is None
        assert img.status() == "loaded"
