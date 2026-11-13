"""过滤 libpng 写 fd=2 的无害 iCCP 警告：OS 级 dup 管道 + daemon 线程按行过滤，
Python sys.stderr 不动。可经 setup(filter_libpng_warnings=False) 关闭，
也可用 uninstall() 还原。
"""

from __future__ import annotations

import os
import sys
import threading

# 命中即丢弃的前缀（保守起见只过这一条）
_DISCARD_PREFIXES: tuple[bytes, ...] = (b"libpng warning: iCCP",)

_installed: bool = False
# 安装时保存的原始 fd，uninstall 据此还原：(原 stderr fd, 其备份 fd, 管道读端)
_saved: tuple[int, int, int] | None = None


def install() -> None:
    """安装 fd=2 过滤器；幂等。Windows / *nix 通用。"""
    global _installed, _saved
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
        """从 pipe 逐行读取，丢弃命中前缀的警告后写回原始 stderr fd。"""
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
    _saved = (original_fd, saved_fd, r_fd)


def uninstall() -> None:
    """还原 fd=2 并结束过滤线程；未安装时忽略，幂等。

    Note:
        先把 fd=2 指回原目标，管道写端随之关闭，过滤线程读到 EOF 后退出。
    """
    global _installed, _saved
    if not _installed or _saved is None:
        return
    original_fd, saved_fd, r_fd = _saved
    try:
        os.dup2(saved_fd, original_fd)
    except OSError:
        pass
    # 读端关闭后过滤线程的下一次 read 出错并退出；saved_fd 仍可能被线程使用，不关闭。
    try:
        os.close(r_fd)
    except OSError:
        pass
    _installed = False
    _saved = None


__all__ = ["install", "uninstall"]
