# 发布新版本指南

本文档说明如何把 HeroSideUI 发布到 PyPI。
**发包已接入 GitHub Actions + PyPI Trusted Publisher (OIDC)，不需要任何 Token**。

## 目录

- [首次配置（一次性）](#首次配置一次性)
- [日常发版流程](#日常发版流程)
- [试水发版（TestPyPI）](#试水发版testpypi)
- [故障排查](#故障排查)

---

## 首次配置（一次性）

### 1. 在 PyPI 上注册 Trusted Publisher

**正式 PyPI** (`https://pypi.org/`)：

1. 登录 https://pypi.org/ → Account settings → **Publishing**
2. 滚到最下面 "Add a new pending publisher"
3. 填写：
   | 字段 | 值 |
   | --- | --- |
   | PyPI Project Name | `herosideui` |
   | Owner | `LingChen-tsjmdlc` |
   | Repository name | `HeroSideUI` |
   | Workflow name | `publish.yml` |
   | Environment name | `pypi-release` |
4. 点 **Add**

> 💡 "pending publisher" 是给**还没发过包**的项目用的——首次发布成功后会自动转正。

**TestPyPI** (`https://test.pypi.org/`)：

重复同样的步骤，但：

- Environment name 改为 `testpypi-release`
- 注意 TestPyPI 账号和正式 PyPI 账号**不互通**，要单独注册

### 2. 在 GitHub 仓库上建 Environment

为了让 OIDC 生效，需要在 GitHub 仓库创建 2 个 environment：

1. 打开 https://github.com/LingChen-tsjmdlc/HeroSideUI/settings/environments
2. 点 **New environment**，分别建：
   - `pypi-release`（发正式 PyPI）
   - `testpypi-release`（发 TestPyPI）
3. （可选加保护）给 `pypi-release` 加 **Required reviewers**，这样每次发正式包都需要一个人批准，防止误操作

### 3. 完成

以上步骤做完后，整个仓库**永久不再需要管理 PyPI Token**。任何电脑、任何人（有仓库权限的）都能触发发包。

---

## 日常发版流程

### 方式 A：通过 GitHub Release（推荐 ⭐）

1. **本地 bump 版本号**：修改 `pyproject.toml` 里的 `version` 和 `hero_side_ui/__init__.py` 里的 `__version__`
   ```bash
   # 比如从 0.0.21 → 0.0.22
   ```
2. **commit + push + tag**：
   ```bash
   git add pyproject.toml hero_side_ui/__init__.py
   git commit -m "chore: release v0.0.22"
   git tag v0.0.22
   git push origin main --tags
   ```
3. **在 GitHub 网页上发 Release**：
   - 打开 https://github.com/LingChen-tsjmdlc/HeroSideUI/releases/new
   - Choose a tag: 选刚推上去的 `v0.0.22`
   - Release title: `v0.0.22`
   - 点 **Generate release notes**（自动生成变更摘要）
   - 点 **Publish release**
4. **等 CI 完成**：
   - 打开 https://github.com/LingChen-tsjmdlc/HeroSideUI/actions
   - 看到 `Publish to PyPI` workflow 正在跑
   - 几分钟后绿勾 → 发包成功
5. **验证**：`pip install herosideui==0.0.22` 能装到

### 方式 B：手动触发（灵活）

1. 打开 https://github.com/LingChen-tsjmdlc/HeroSideUI/actions/workflows/publish.yml
2. 点右上 **Run workflow**
3. 选 `target` = `pypi`
4. 点绿色 **Run workflow** 按钮

> ⚠️ 手动触发不会自动更新 `pyproject.toml` 的版本号，需要**事先把版本号改好再 push**。否则会因版本号已存在而被 PyPI 拒绝。

---

## 试水发版（TestPyPI）

第一次发包前，**强烈建议先试 TestPyPI**，确保打包无误、资源文件齐全、同事装起来没问题。

1. 打开 https://github.com/LingChen-tsjmdlc/HeroSideUI/actions/workflows/publish.yml
2. 点 **Run workflow**
3. `target` 选 `testpypi`
4. Run

完成后用干净环境验证：

```bash
# 开一个干净 venv
python -m venv /tmp/herosideui-test
# Windows 是 /tmp/herosideui-test/Scripts/python

# 从 TestPyPI 装
/tmp/herosideui-test/bin/pip install \
  --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ \
  herosideui==0.0.22

# 冒烟测试
/tmp/herosideui-test/bin/python -c "
from hero_side_ui import Button, ThemeSwitcher
from hero_side_ui.utils import load_svg_icon
pixmap = load_svg_icon('heroicons--check-solid', size=24)
print('✅ icon 加载 OK, pixmap =', pixmap)
"
```

> 💡 `--extra-index-url https://pypi.org/simple/` 是必须的，因为 PySide6 只在正式 PyPI 有，TestPyPI 装不到依赖。

TestPyPI 验证通过了，再发正式 PyPI。

---

## 故障排查

### ❌ `Trusted publisher not found`

PyPI 项目侧的 pending publisher 没配好，或配错了。检查：

- Owner / Repository name 大小写是否完全一致
- Workflow name 必须填 `publish.yml`（不是 `Publish.yml`）
- Environment name 必须完全匹配（`pypi-release` / `testpypi-release`）

### ❌ `File already exists`

版本号冲突。PyPI 不允许重复发相同版本号。
解决：bump 版本号，重新 push tag 并发 Release。

> ⚠️ **已发的版本号永久占用**，即使从 PyPI 删掉了，**同一个版本号也不能再发**。

### ❌ `wheel 中未找到 svg 资源`

打包时 pipeline 的 sanity check 失败。检查：

- `hero_side_ui/resources/icons/` 下确实有 `.svg` 文件
- `pyproject.toml` 的 `[tool.hatch.build.targets.wheel.force-include]` 还在

### ❌ CI 显示 `pending approval`

某个 environment 启用了 Required reviewers，需要有人批准。
去 Actions 页面点那个等待的 job，点 "Review deployments" → Approve。

---

## 版本号约定

遵循 [PEP 440](https://peps.python.org/pep-0440/)，开发阶段用 `0.0.x`，接近 beta 用 `0.1.0b1`，接近稳定用 `0.1.0rc1`，稳定用 `0.1.0`。

```
0.0.21  → alpha（当前）
0.0.22
  ...
0.1.0   → 第一个相对稳定的 minor
1.0.0   → 正式稳定版（API 锁定）
```

**注意**：HeroSideUI 目前是 **Alpha 阶段**，API 可能破坏性变更。依赖方请**锁死版本号**（`herosideui==0.0.21`），而不是 `>=`。
