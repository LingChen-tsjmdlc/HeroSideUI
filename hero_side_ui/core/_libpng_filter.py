"""过滤 libpng 写 fd=2 的无害 iCCP 警告：OS 级 dup 管道 + daemon 线程按行过滤，
Python sys.stderr 不动。可经 setup(filter_libpng_warnings=False) 关闭，
也可用 uninstall() 还原。

资源所有权：备份 stderr 的 fd 与管道读端归过滤线程，线程读到 EOF 并写完
剩余内容后关闭；管道写端仅以 fd=2 的形式存在，uninstall 还原 fd=2 即关闭它。
"""

from __future__ import annotations

import os
import sys
import threading

# 命中即丢弃的前缀（保守起见只过这一条）
_DISCARD_PREFIXES: tuple[bytes, ...] = (b"libpng warning: iCCP",)
# uninstall 等待过滤线程退出的上限（秒）；有子进程持有管道写端时线程要等其退出
_JOIN_TIMEOUT = 2.0


class _Filter:
    """一次安装的状态：被接管的 fd、备份 fd 与过滤线程。"""

    def __init__(self, target_fd: int, backup_fd: int, read_fd: int) -> None:
        """记录三个描述符并创建线程，线程拥有 backup_fd 与 read_fd。

        Args:
            target_fd: 被接管的 stderr 描述符。
            backup_fd: target_fd 原指向目标的备份，用于写出与还原。
            read_fd: 管道读端。
        """
        self.target_fd = target_fd
        self.backup_fd = backup_fd
        self.read_fd = read_fd
        self.thread = threading.Thread(
            target=self._pump, name="hero_side_ui-libpng-filter", daemon=True
        )

    def _pump(self) -> None:
        """逐行读管道，丢弃命中前缀的警告，其余写回备份 fd；读到 EOF 后释放 fd。"""
        buf = b""
        try:
            while True:
                try:
                    chunk = os.read(self.read_fd, 4096)
                except OSError:
                    break
                if not chunk:
                    break
                buf += chunk
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    self._emit(line + b"\n")
            if buf:
                self._emit(buf)
        finally:
            for fd in (self.read_fd, self.backup_fd):
                try:
                    os.close(fd)
                except OSError:
                    pass

    def _emit(self, line: bytes) -> None:
        """把不在丢弃名单里的内容写回备份 fd。"""
        if line.startswith(_DISCARD_PREFIXES):
            return
        try:
            os.write(self.backup_fd, line)
        except OSError:
            pass


_active: _Filter | None = None


def install() -> None:
    """安装 fd=2 过滤器；幂等。Windows / *nix 通用。"""
    global _active
    if _active is not None:
        return
    # 没有真实 stderr fd（部分 IDE / 嵌入解释器场景）→ 直接 bail
    try:
        target_fd = sys.stderr.fileno()
    except (AttributeError, OSError, ValueError):
        return

    opened: list[int] = []
    try:
        backup_fd = os.dup(target_fd)
        opened.append(backup_fd)
        read_fd, write_fd = os.pipe()
        opened += [read_fd, write_fd]
        os.dup2(write_fd, target_fd)
    except OSError:
        for fd in opened:
            try:
                os.close(fd)
            except OSError:
                pass
        return
    os.close(write_fd)  # fd=2 已持有写端，这一份不再需要
    _active = _Filter(target_fd, backup_fd, read_fd)
    _active.thread.start()


def uninstall() -> None:
    """还原 fd=2 并等待过滤线程释放资源；未安装时忽略，幂等。

    Note:
        先还原 fd=2 使管道写端关闭，线程读到 EOF 后写完剩余内容并关闭
        自己持有的 fd。等待超时（子进程仍持有写端）时线程继续持有，
        EOF 到达后自行释放，不会被提前关闭。
    """
    global _active
    current, _active = _active, None
    if current is None:
        return
    try:
        os.dup2(current.backup_fd, current.target_fd)
    except OSError:
        pass
    current.thread.join(_JOIN_TIMEOUT)


__all__ = ["install", "uninstall"]
