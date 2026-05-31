# Squircle — 超椭圆 (Superellipse) 圆角

> **⚠️ 实验性功能 — 已实现但未集成到组件库**
>
> 代码保留在 `hero_side_ui/utils/squircle.py`，供未来讨论和按需启用。
> 当前所有组件使用 Qt 标准 `drawRoundedRect` / QSS `border-radius`。

## 为什么没有集成？

2026-06-01 经完整实现 + PS 叠加验证后的决策：

| 因素                 | 详情                                                                                                      |
| -------------------- | --------------------------------------------------------------------------------------------------------- |
| **视觉差异不够显著** | 小尺寸组件 (Button R=8) 偏差 24px 但人眼难以分辨；大组件 (Card R=14) 差异可见但不惊艳                     |
| **集成成本高**       | 每个 paintEvent 组件需 `drawRoundedRect` → `squircle_path` + `drawPath`；QSS 组件 (Button/Alert) 无法使用 |
| **视觉一致性风险**   | 混用会导致部分"鼓角"+ 部分标准圆角的割裂感                                                                |
| **维护负担**         | 每个新圆角组件都需做集成决策                                                                              |

**值得重新考虑的场景：** 大容器 (Modal/Dialog/Sheet, R≥20)、品牌 icon 容器、用户明确要求 iOS 风格的项目。

## 技术概要（供参考）

**核心方程：**
$$\left|\frac{x}{a}\right|^n + \left|\frac{y}{b}\right|^n = 1$$

| 算法                                | 最大偏差 (R=14) | 结论                           |
| ----------------------------------- | --------------- | ------------------------------ |
| Figma corner smoothing (v1, 已废弃) | <0.5 px         | PS 叠加重合，不可见            |
| **Superellipse (v2, 当前)**         | **~22 px**      | 可见但不够惊艳，也没有那么好看 |

**参数映射：** `smoothness` [0,1] → n [2,10]，默认 0.6 → n=5 (iOS)

## API 参考

```python
from hero_side_ui.utils.squircle import squircle_path

path = squircle_path(
    rect=QRectF(0, 0, 200, 100),
    radius=14.0,
    smoothness=0.6,  # → n=5 (iOS)
)
# painter.drawPath(path)
```

详见 `hero_side_ui/utils/squircle.py` 文件头注释。

## Demo

```bash
python examples/squircle_preview.py
```

包含 5 个对比区域：整体轮廓 / 真实尺寸 / 大图放大 / 描边叠加 / n 梯度。
