"""Dialog 的结果层：结果码、结果数据、阻塞 / 非阻塞打开。"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QEventLoop

from ._footer import ACCEPTED, REJECTED, check_code


class _ResultMixin:
    """done / accept / reject / exec / open 与结果数据。

    宿主类需提供 finished / accepted / rejected 信号、show()、_active、
    _result、_result_data、_data_provider 与 _on_done()。
    """

    def result(self) -> int:
        """结果码。打开期间恒为 0，关闭那一刻才确定，之后保持到下次打开。"""
        return self._result

    def result_data(self):
        """结果数据（任意对象），默认 None；每次打开时重置。"""
        return self._result_data

    def set_result_data(self, data):
        """写入结果数据；关闭时若 done 或按钮带了数据，会覆盖它。"""
        self._result_data = data

    def set_result_data_provider(self, provider: Callable[[], object] | None):
        """设置关闭时才取数据的函数。

        Args:
            provider: 无参函数，返回值作为结果数据；仅在数据仍为 None 且结果码不是 0 时调用。
                None 取消。
        """
        self._data_provider = provider

    def accept(self):
        """以结果码 1 关闭。"""
        self.done(ACCEPTED)

    def reject(self):
        """以结果码 0 关闭。"""
        self.done(REJECTED)

    def done(self, code: int, data=None):
        """以任意整数结果码关闭。

        Args:
            code: 结果码；bool 不算整数。
            data: 结果数据；None 表示不改动已有数据。

        Raises:
            ValueError: code 不是整数。

        Note:
            没打开或已关闭时忽略，不发信号。信号顺序：finished，再 accepted / rejected；
            结果数据在信号发出之前就位。
        """
        code = check_code(code)
        if not self._active:
            return
        if data is None and self._result_data is None and code != REJECTED:
            if self._data_provider is not None:
                data = self._data_provider()
        self._active = False
        self._result = code
        if data is not None:
            self._result_data = data
        self._on_done()
        self.finished.emit(code)
        if code == ACCEPTED:
            self.accepted.emit()
        elif code == REJECTED:
            self.rejected.emit()

    def open(self):
        """打开，不阻塞；结果靠信号拿。"""
        self.show()

    def exec(self) -> int:
        """打开并阻塞到关闭。

        Returns:
            结果码。父窗口被销毁时事件循环也会退出，不会卡死。
        """
        loop = QEventLoop()
        conns = [
            self.finished.connect(lambda *_: loop.quit()),
            self.destroyed.connect(lambda *_: loop.quit()),
        ]
        try:
            if not self._active:
                self.open()
            if self._active:
                loop.exec()
        finally:
            for c in conns:
                try:
                    self.disconnect(c)
                except RuntimeError:
                    pass  # 对话框已随父窗口销毁
        return self._result


__all__ = ["_ResultMixin"]
