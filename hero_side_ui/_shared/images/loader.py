"""Image 统一图源加载器：URL 异步（全局节流）/本地路径/QPixmap 三种 src。
对外 status 四态与 loaded/failed 信号，对齐 HeroUI use-image。
"""

from __future__ import annotations

import logging
import random
from collections import deque
from collections.abc import Callable

from PySide6.QtCore import QObject, QTimer, QUrl, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest

ImageSrc = str | QPixmap | QImage | None

_logger = logging.getLogger("hero_side_ui.image")

# 远程 URL 节流间隔（毫秒）—— uapis.cn 等公共 API 限频
_URL_THROTTLE_MIN_MS = 1000
_URL_THROTTLE_MAX_MS = 1500


class _UrlRequestQueue(QObject):
    """全局远程请求节流队列：http(s) 串行发起，相邻间隔随机 1000–1500ms。"""

    _instance: _UrlRequestQueue | None = None

    @classmethod
    def instance(cls) -> _UrlRequestQueue:
        """取全局单例节流队列。

        Returns:
            唯一的 _UrlRequestQueue 实例。
        """
        if cls._instance is None:
            cls._instance = _UrlRequestQueue()
        return cls._instance

    def __init__(self):
        """初始化空队列、单次计时器与冷却标记。"""
        super().__init__()
        # 队列条目: (token, callable) —— callable 真正发起 NAM.get
        self._queue: deque[tuple[object, Callable[[], None]]] = deque()
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._on_tick)
        # 是否还在节流冷却中
        self._cooling = False

    # 提交一个请求；token 可用于后续 cancel
    def enqueue(self, token: object, fire: Callable[[], None]):
        """提交一个远程请求，未在冷却中则立即派发。

        Args:
            token: 用于后续 cancel 的唯一标识。
            fire: 真正发起 NAM.get 的可调用对象。
        """
        self._queue.append((token, fire))
        if not self._cooling:
            # 队列空闲：立即处理
            self._dispatch_next()

    # 取消尚未发出的请求（已 dispatch 过的不影响）
    def cancel(self, token: object):
        """取消仍未发出的请求。

        Args:
            token: 入队时提供的标识。

        Note:
            已 dispatch 过的请求不受影响，需由 ImageLoader._cancel 走 abort。
        """
        self._queue = deque((t, f) for (t, f) in self._queue if t is not token)

    def _dispatch_next(self):
        """派发队首请求并进入随机 1000–1500ms 冷却。

        Note:
            单条请求异常被吞掉，不能阻塞整条队列。
        """
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
        """冷却结束：继续派发或清除冷却标记。"""
        if self._queue:
            self._dispatch_next()
        else:
            self._cooling = False


class ImageLoader(QObject):
    """统一异步图源加载器。"""

    loaded = Signal(QPixmap)
    failed = Signal()

    # 共享一个 QNetworkAccessManager（避免每次新建）
    _shared_nam: QNetworkAccessManager | None = None

    def __init__(self, parent: QObject | None = None):
        """创建加载器，初始状态为 pending。

        Args:
            parent: Qt 父对象。
        """
        super().__init__(parent)
        self._status: str = "pending"
        self._reply: QNetworkReply | None = None
        self._current_src: ImageSrc = None
        # 在 URL 排队期间、reply 还没建立时的占位 token
        self._pending_token: object | None = None

    @classmethod
    def _nam(cls) -> QNetworkAccessManager:
        """取共享的 QNetworkAccessManager。

        Returns:
            全局唯一实例，避免每次请求新建。
        """
        if cls._shared_nam is None:
            cls._shared_nam = QNetworkAccessManager()
        return cls._shared_nam

    @property
    def status(self) -> str:
        """返回当前加载状态。

        Returns:
            pending / loading / loaded / failed。
        """
        return self._status

    def load(self, src: ImageSrc):
        """启动加载，先取消上一次请求。

        Args:
            src: 图源，可为 QPixmap / QImage / URL / 本地路径 / None。

        Note:
            已是图像对象时异步一帧发 loaded；http(s) 走全局节流队列；
            未知类型发 failed。
        """
        self._cancel()
        self._current_src = src

        if src is None or (isinstance(src, str) and not src):
            self._status = "pending"
            return

        # 1) 已是图像对象
        if isinstance(src, QPixmap):
            self._status = "loaded"
            # 绑 self 作 context：loader 若在回调前被销毁则自动跳过，避免 "Signal source deleted"
            QTimer.singleShot(0, self, lambda pm=src: self.loaded.emit(pm))
            return
        if isinstance(src, QImage):
            self._status = "loaded"
            pm = QPixmap.fromImage(src)
            QTimer.singleShot(0, self, lambda pm=pm: self.loaded.emit(pm))
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
        QTimer.singleShot(0, self, self.failed.emit)

    # ============================================================
    # 本地 / Qt 资源
    # ============================================================
    def _load_local(self, path: str):
        """同步读本地路径或 Qt 资源，异步一帧发结果。

        Args:
            path: 本地文件路径或 Qt 资源路径。
        """
        self._status = "loading"
        pm = QPixmap(path)
        if pm.isNull():
            self._status = "failed"
            _logger.warning("Image load failed: %s (本地路径不存在或不是有效图像)", path)
            QTimer.singleShot(0, self, self.failed.emit)
            return
        self._status = "loaded"
        QTimer.singleShot(0, self, lambda pm=pm: self.loaded.emit(pm))

    # ============================================================
    # 远程 URL（走全局节流队列）
    # ============================================================
    def _enqueue_url(self, url: str):
        """把远程请求放进全局节流队列。

        Args:
            url: http(s) 图片地址。

        Note:
            用唯一 token 标识，出队回调会校验 token，
            loader 已被 _cancel 时直接丢弃。
        """
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
        """真正发起 NAM.get。

        Args:
            url: 图片地址。

        Note:
            允许 NoLessSafe 重定向（如 uapis.cn 会 302 到目标图），
            并加简单 UA 避免部分服务端拒绝。
        """
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
        """网络回复完成：解析图片或发 failed，并清理 reply。

        Note:
            HTTP 错误、响应体不是有效图像都记 warning 后发 failed；
            无论成功与否都在 finally 里 deleteLater 并清空 _reply。
        """
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
        """取消当前加载：已发请求 abort、排队请求出队，状态回 pending。"""
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
