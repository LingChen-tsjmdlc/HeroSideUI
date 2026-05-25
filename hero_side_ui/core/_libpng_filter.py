"""过滤 libpng 写到 fd=2 (stderr) 的无害噪声警告（私有）。

背景：
    Qt 6 / Windows 加载某些内置 PNG 资源时，libpng 通过 C 的 fwrite 直接
    向 fd=2 写出 ``libpng warning: iCCP: known incorrect sRGB profile``。
    这条警告完全无害，但每个组件实例化都会触发一次，刷屏严重。
    libpng 直接写 fd=2，Python 的 ``sys.stderr`` 替换拦不住它，必须做 OS 级
    fd 重定向才能截断。

实现：
    把原 fd=2 dup 到 pipe 的 write 端，启一条 daemon 线程不断读 pipe，按行
    过滤后再写回**真正的**原 stderr。Python 层 ``sys.stderr`` 不动，避免影响
    其他正常的 Python warning / traceback。

可关闭：``HeroSideUIProvider.setup(filter_libpng_warnings=False)``。
"""

from __future__ import annotations

import os
import sys
import threading

# 命中即丢弃的前缀（保守起见只过这一条）
_DISCARD_PREFIXES: tuple[bytes, ...] = (b"libpng warning: iCCP",)

_installed: bool = False


def install() -> None:
    """安装 fd=2 过滤器；幂等。Windows / *nix 通用。"""
    global _installed
    if _installed:
        return
    # 没有真实 stderr fd（部分 IDE / 嵌入解释器场景）→ 直接 bail
    try:
        original_fd = sys.stderr.fileno()
    except (AttributeError, OSError, ValueError):
        return

    try:
        # 备份原 fd 用于真正写出
        saved_fd = os.dup(original_fd)
        # 建 pipe；让 fd=2 指向 pipe 的写端
        r_fd, w_fd = os.pipe()
        os.dup2(w_fd, original_fd)
        os.close(w_fd)
    except OSError:
        return

    def _pump():
        # 从 pipe 读取，按行过滤后写回原始 stderr fd
        buf = b""
        while True:
            try:
                chunk = os.read(r_fd, 4096)
            except OSError:
                return
            if not chunk:
                return
            buf += chunk
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                if any(line.startswith(p) for p in _DISCARD_PREFIXES):
                    continue
                try:
                    os.write(saved_fd, line + b"\n")
                except OSError:
                    return

    t = threading.Thread(target=_pump, name="hero_side_ui-libpng-filter", daemon=True)
    t.start()
    _installed = True


__all__ = ["install"]
