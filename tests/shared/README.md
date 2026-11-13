# shared 测试

覆盖 `hero_side_ui/_shared/` 中组件家族共享的基础设施，以及跨组件的依赖边界。

| 文件 | 内容 |
| --- | --- |
| `test_import_boundaries.py` | 组件之间不得依赖对方的私有模块或私有属性，共享层不得在运行时依赖组件 |
| `test_fields_contract.py` | 输入类 Mixin 要求宿主提供的属性，逐个宿主校验 |
| `test_family_capabilities.py` | 遮罩、列表、浮层、日期模型等共享能力的公开接口与真实消费者 |

新增跨组件共享能力时，同步补充消费者的断言，而不只测试共享模块本身。
