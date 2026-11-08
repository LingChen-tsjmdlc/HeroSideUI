"""管理单次动画的通道所有权、连接和释放。"""

import weakref

from PySide6.QtCore import QAbstractAnimation, QObject
from shiboken6 import isValid


def alive(obj):
    """判断通道持有者或 Qt 对象是否仍可使用。"""
    return obj is not None and (not isinstance(obj, QObject) or isValid(obj))


def revision(owner, attribute):
    """返回通道的请求版本，用于识别回调中的重入。"""
    return getattr(owner, "_hs_animation_revisions", {}).get(attribute, 0)


def settle(owner, attribute, apply=None, on_finished=None):
    """应用终态，仅在期间未被新请求取代时通知完成。"""
    before = revision(owner, attribute)
    if apply is not None:
        apply()
    if alive(owner) and revision(owner, attribute) == before and on_finished is not None:
        on_finished()


def dispose(animation):
    """停止动画、断开内部连接，并安排 Qt 延迟删除。"""
    if alive(animation):
        animation.stop()
        for node in [animation, *animation.findChildren(QAbstractAnimation)]:
            for connection in getattr(node, "_hs_connections", ()):
                QObject.disconnect(connection)
            node._hs_connections = []
        animation.deleteLater()


def connect_owned(animation, signal, callback):
    """记录内部信号连接，供动画结束或取消时统一断开。"""
    connections = getattr(animation, "_hs_connections", None)
    if connections is None:
        connections = []
        animation._hs_connections = connections
    connections.append(signal.connect(callback))


def stop_runner(owner, attribute):
    """先撤销通道所有权，再停止和释放旧动画。"""
    revisions = getattr(owner, "_hs_animation_revisions", None)
    if revisions is None:
        revisions = {}
        owner._hs_animation_revisions = revisions
    revisions[attribute] = revisions.get(attribute, 0) + 1
    animation = getattr(owner, attribute, None)

    setattr(owner, attribute, None)
    if animation is not None:
        dispose(animation)


def current(owner, attribute, animation):
    """判断动画是否仍拥有有效宿主上的对应通道。"""
    return alive(owner) and getattr(owner, attribute, None) is animation


def start_runner(owner, attribute, animation: QAbstractAnimation, on_finished=None):
    """持有并启动动画，统一处理完成和销毁。

    Args:
        owner: 通道持有者，必须支持弱引用和属性赋值。
        attribute: 保存当前动画的字段名。
        animation: 已配置、尚未启动的 Qt 动画。
        on_finished: 仍拥有通道时执行的完成回调。

    Returns:
        运行期间有效的 Qt 动画句柄。
    """
    owner_ref = weakref.ref(owner)
    animation_ref = weakref.ref(animation)

    def destroyed():
        holder, handle = owner_ref(), animation_ref()
        if holder is not None and current(holder, attribute, handle):
            setattr(holder, attribute, None)

    def finish():
        holder = owner_ref()
        owns_channel = holder is not None and current(holder, attribute, animation)
        if owns_channel:
            setattr(holder, attribute, None)
        dispose(animation)
        if owns_channel and on_finished is not None:
            on_finished()

    connect_owned(animation, animation.finished, finish)
    animation.destroyed.connect(destroyed)
    setattr(owner, attribute, animation)
    animation.start()
    return animation
