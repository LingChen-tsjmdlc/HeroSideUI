# Spacer 间距填充器

零尺寸占位件，靠 margin 撑出空白。对照官方 `Spacer`（Tailwind spacing scale）复刻。

## 构造参数

| 参数 | 类型                  | 默认 | 说明                              |
| ---- | --------------------- | ---- | --------------------------------- |
| `x`  | `int \| float \| str` | `1`  | 横向 margin（spacing scale 档位） |
| `y`  | `int \| float \| str` | `1`  | 纵向 margin（spacing scale 档位） |

## spacing scale（对照官方 utils.ts，×4px）

| 档位 | 像素 | 档位 | 像素 | 档位 | 像素 |
| ---- | ---- | ---- | ---- | ---- | ---- |
| `px` | 1    | 3    | 12   | 8    | 32   |
| 0    | 0    | 3.5  | 14   | 10   | 40   |
| 0.5  | 2    | 4    | 16   | 12   | 48   |
| 1    | 4    | 5    | 20   | 16   | 64   |
| 1.5  | 6    | 6    | 24   | 20   | 80   |
| 2    | 8    | 7    | 28   | 24   | 96   |

（完整表见 `hero_side_ui/components/spacer/spacer.py::SPACING_SCALE`，最大 96=384px）

## 公共方法

| 方法                      | 说明              |
| ------------------------- | ----------------- |
| `set_x(x)` / `set_y(y)`   | 更新横向/纵向档位 |
| `x_space()` / `y_space()` | 读当前档位        |

## 与 HeroUI 差异

1. 官方本体是 0×0 span + margin-left/margin-top（CSS margin 参与布局）；Qt 布局的 contentsMargins 不参与父布局几何，桌面端等价实现为**本体 fixedSize(x_px, y_px)**——透明无绘制，尺寸即空白。
2. 官方 `as`/`classNames`/`style` React 机制不采纳。
3. 官方 x/y 档位超出 scale 表时按任意值直传 CSS；桌面端数字档位缺失时按数字像素处理。
