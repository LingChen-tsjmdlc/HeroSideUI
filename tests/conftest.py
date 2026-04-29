"""
pytest 全局配置

确保:
1. QApplication 单例在整个测试会话中只创建一次
2. 每个测试结束后清理残留 widget，避免跨测试 segfault
"""

import gc
import sys

import pytest
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="session", autouse=True)
def qapp():
    """确保整个测试会话共用一个 QApplication 实例"""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv[:1])
    yield app


@pytest.fixture(autouse=True)
def cleanup_widgets(qtbot):
    """每个测试结束后强制处理事件并回收 widget"""
    yield
    # 处理所有挂起的事件（包括动画、延迟删除等）
    QApplication.processEvents()
    # 强制垃圾回收，确保 C++ 对象析构
    gc.collect()
    QApplication.processEvents()
