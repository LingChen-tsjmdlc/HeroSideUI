"""Image 组件统一图源加载器。

支持三种 src：
- str（http/https URL）→ QNetworkAccessManager 异步下载（全局节流 1.0–1.5s）
- str（本地路径 / Qt 资源路径）→ QPixmap 直接加载
- QPixmap / QImage → 直接发出 loaded 信号

对外提供 status：pending / loading / loaded / failed，以及 loaded(pixmap) /
failed() 两个信号。和 HeroUI use-image 行为对齐。
"""

from __future__ import annotations

import logging
import random
from collections import deque
from typing import Callable, Deque, Optional, Tuple, Union

from PySide6.QtCore import QObject, QTimer, QUrl, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest

ImageSrc = Union[str, QPixmap, QImage, None]

_logger = logging.getLogger("hero_side_ui.image")

# 远程 URL 节流间隔（毫秒）—— uapis.cn 等公共 API 限频
_URL_THROTTLE_MIN_MS = 1000
_URL_THROTTLE_MAX_MS = 1500


class _UrlRequestQueue(QObject):
    """全局远程 URL 请求节流队列。

    所有 ImageLoader 实例的 http(s) 请求都串行通过这里，相邻两次
    实际发起请求的时间间隔随机 1000–1500ms。
    """

    _instance: Optional["_UrlRequestQueue"] = None

    @classmethod
    def instance(cls) -> "_UrlRequestQueue":
        if cls._instance is None:
            cls._instance = _UrlRequestQueue()
        return cls._instance

    def __init__(self):
        super().__init__()
        # 队列条目: (token, callable) —— callable 真正发起 NAM.get
        self._queue: Deque[Tuple[object, Callable[[], None]]] = deque()
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._on_tick)
        # 是否还在节流冷却中
        self._cooling = False

    # 提交一个请求；token 可用于后续 cancel
    def enqueue(self, token: object, fire: Callable[[], None]):
        self._queue.append((token, fire))
        if not self._cooling:
            # 队列空闲：立即处理
            self._dispatch_next()

    # 取消尚未发出的请求（已 dispatch 过的不影响）
    def cancel(self, token: object):
        self._queue = deque((t, f) for (t, f) in self._queue if t is not token)

    def _dispatch_next(self):
        if not self._queue:
            self._cooling = False
            return
        _, fire = self._queue.popleft()
        try:
            fire()
        except Exception:
            # 单条请求异常不能阻塞整条队列
            pass
        # 进入冷却，到点后再处理下一条
        self._cooling = True
        delay = random.randint(_URL_THROTTLE_MIN_MS, _URL_THROTTLE_MAX_MS)
        self._timer.start(delay)

    def _on_tick(self):
        if self._queue:
            self._dispatch_next()
        else:
            self._cooling = False


class ImageLoader(QObject):
    """统一异步图源加载器。"""

    loaded = Signal(QPixmap)
    failed = Signal()

    # 共享一个 QNetworkAccessManager（避免每次新建）
    _shared_nam: Optional[QNetworkAccessManager] = None

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._status: str = "pending"
        self._reply: Optional[QNetworkReply] = None
        self._current_src: ImageSrc = None
        # 在 URL 排队期间、reply 还没建立时的占位 token
        self._pending_token: Optional[object] = None

    @classmethod
    def _nam(cls) -> QNetworkAccessManager:
        if cls._shared_nam is None:
            cls._shared_nam = QNetworkAccessManager()
        return cls._shared_nam

    @property
    def status(self) -> str:
        return self._status

    def load(self, src: ImageSrc):
        """启动加载。"""
        self._cancel()
        self._current_src = src

        if src is None or (isinstance(src, str) and not src):
            self._status = "pending"
            return

        # 1) 已是图像对象
        if isinstance(src, QPixmap):
            self._status = "loaded"
            QTimer.singleShot(0, lambda pm=src: self.loaded.emit(pm))
            return
        if isinstance(src, QImage):
            self._status = "loaded"
            pm = QPixmap.fromImage(src)
            QTimer.singleShot(0, lambda pm=pm: self.loaded.emit(pm))
            return

        # 2) 字符串：URL or 本地路径
        if isinstance(src, str):
            if src.startswith(("http://", "https://")):
                self._enqueue_url(src)
            else:
                self._load_local(src)
            return

        # 未知类型
        self._status = "failed"
        QTimer.singleShot(0, self.failed.emit)

    # ============================================================
    # 本地 / Qt 资源
    # ============================================================
    def _load_local(self, path: str):
        self._status = "loading"
        pm = QPixmap(path)
        if pm.isNull():
            self._status = "failed"
            _logger.warning(
                "Image load failed: %s (本地路径不存在或不是有效图像)", path
            )
            QTimer.singleShot(0, self.failed.emit)
            return
        self._status = "loaded"
        QTimer.singleShot(0, lambda pm=pm: self.loaded.emit(pm))

    # ============================================================
    # 远程 URL（走全局节流队列）
    # ============================================================
    def _enqueue_url(self, url: str):
        self._status = "loading"
        token = object()  # 唯一标识本次请求
        self._pending_token = token

        def _fire():
            # 出队回调：可能 loader 已被 _cancel，需校验 token
            if self._pending_token is not token:
                return
            self._pending_token = None
            self._do_load_url(url)

        _UrlRequestQueue.instance().enqueue(token, _fire)

    def _do_load_url(self, url: str):
        req = QNetworkRequest(QUrl(url))
        # 允许重定向（uapis.cn 实际会 302 到目标图）
        req.setAttribute(
            QNetworkRequest.Attribute.RedirectPolicyAttribute,
            QNetworkRequest.RedirectPolicy.NoLessSafeRedirectPolicy,
        )
        # 简单 UA，避免某些服务端拒绝
        req.setRawHeader(b"User-Agent", b"HeroSideUI/Image")

        reply = self._nam().get(req)
        self._reply = reply
        reply.finished.connect(self._on_reply_finished)

    def _on_reply_finished(self):
        reply = self._reply
        if reply is None:
            return
        try:
            if reply.error() != QNetworkReply.NetworkError.NoError:
                self._status = "failed"
                url = reply.request().url().toString()
                _logger.warning(
                    "Image load failed: %s (HTTP 错误: %s)",
                    url,
                    reply.errorString(),
                )
                self.failed.emit()
                return
            data = bytes(reply.readAll())
            pm = QPixmap()
            if not pm.loadFromData(data) or pm.isNull():
                self._status = "failed"
                url = reply.request().url().toString()
                _logger.warning("Image load failed: %s (响应体不是有效图像)", url)
                self.failed.emit()
                return
            self._status = "loaded"
            self.loaded.emit(pm)
        finally:
            reply.deleteLater()
            self._reply = None

    # ============================================================
    def _cancel(self):
        # 1) 已发出的请求：abort
        if self._reply is not None:
            try:
                self._reply.abort()
            except RuntimeError:
                pass
            self._reply = None
        # 2) 还在节流队列里等待的请求：从队列移除
        if self._pending_token is not None:
            _UrlRequestQueue.instance().cancel(self._pending_token)
            self._pending_token = None
        self._status = "pending"


__all__ = ["ImageLoader", "ImageSrc"]
