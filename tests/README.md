# HeroSideUI 测试套件

按"被测对象的所在层"分目录，每层职责单一，互不掺杂。

## 目录结构

```
tests/
├── conftest.py        # 全局 fixture：每个测试前后抽干 Qt 事件 / 停所有动画 / GC
├── core/              # 核心基础设施（hero_side_ui/core/）
│   ├── test_theme_provider.py
│   ├── test_state_palette.py
│   ├── test_scroll_style.py
│   └── test_smooth_scroll.py
├── utils/             # 纯函数工具（hero_side_ui/utils/）
│   └── （color_utils / icon_utils 等纯函数测试）
├── animation/         # 动画基元（hero_side_ui/animation/）
│   └── （tween / ripple / collapse 等动画测试）
└── components/        # 组件层（hero_side_ui/components/）
    └── test_*.py      # 与组件一一对应
```

每个子目录都有自己的 `README.md`，先看那里再写测试。

## 跑测试

```bash
uv run python -m pytest tests/ -v                             # 全量
uv run python -m pytest tests/core/ -v                        # 只跑核心
uv run python -m pytest tests/components/test_button.py -v    # 单文件
uv run python -m pytest tests/ -k "tooltip"                   # 关键字过滤
```

## 写测试的总原则

1. **每个被测模块一个测试文件**，文件名 = `test_<module_name>.py`。
2. **每个类一个 `Test<功能>` class**，把相关 case 归拢。
3. **不复制 conftest.py 到子目录** —— 全局 fixture 在根 `conftest.py`，pytest 会沿目录树向上收集。
4. **测视觉/动画时只测"状态转移"**，不测像素值；像素验证靠 examples 人工跑。
5. **依赖 Qt 事件循环的测试都用 `qtbot` 注入**（即便不直接用 qtbot，autouse 的 `_cleanup_qt_state` 也需要它）。
6. **测试结束不要留下 active QTimer / 动画**，否则会跨测试访问已释放对象 → access violation（Windows 上必现）。conftest 已尽力兜底，但写组件测试时还是要主动 `widget.close()` / `qtbot.wait(50)` 让动画收尾。

## 新增组件时

- `hero_side_ui/components/xxx/` → `tests/components/test_xxx.py`
- `hero_side_ui/core/xxx.py` → `tests/core/test_xxx.py`
- `hero_side_ui/utils/xxx.py` → `tests/utils/test_xxx.py`
- `hero_side_ui/animation/xxx.py` → `tests/animation/test_xxx.py`

被测对象在哪一层，测试就放哪一层。**不要跨层混测**（比如不要在 `test_button.py` 里测 `tween_value` 的边界）。
