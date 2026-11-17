"""CI 诊断报告：汇总追踪日志与 macOS 崩溃报告，直接打印到 job 日志。

用法：
    python hs_ci_report.py trace <追踪文件>
    python hs_ci_report.py crash <.ips/.crash 文件或目录>

trace：找出崩溃时正在执行的阶段、其前后的记录、Qt 警告统计。
crash：解析崩溃报告，打印异常类型、崩溃线程的 C++ 调用栈与加载的库。
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

_LINE = re.compile(r"^\s*(?P<t>[\d.]+) T(?P<th>\d+)\s+(?P<body>.*)$")
_BEGIN = re.compile(r"^BEGIN (?P<phase>\w+)\s+(?P<node>\S+)")
_END = re.compile(r"^END\s+(?P<phase>\w+)\s+(?P<node>\S+)")


def _title(text: str) -> None:
    print(f"\n{'=' * 8} {text} {'=' * 8}")


def report_trace(path: Path) -> None:
    """汇总追踪文件。"""
    _title(f"追踪日志 {path}")
    if not path.exists():
        print("没有追踪文件：测试进程没有启动，或没有设置 HS_TRACE_FILE")
        return
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    print(f"共 {len(lines)} 行")

    open_at, open_desc = None, ""
    started = finished = 0
    qt_msgs: Counter[str] = Counter()
    outcomes: Counter[str] = Counter()
    for i, raw in enumerate(lines):
        m = _LINE.match(raw)
        body = m.group("body") if m else raw.strip()
        b, e = _BEGIN.match(body), _END.match(body)
        if body.startswith("==== TEST"):
            started += 1
        elif b:
            open_at, open_desc = i, f"{b.group('phase')} {b.group('node')}"
        elif e and open_desc == f"{e.group('phase')} {e.group('node')}":
            open_at = None
        elif body.startswith("SESSION FINISH"):
            finished += 1
        elif body.startswith("QT "):
            qt_msgs[re.sub(r"0x[0-9a-fA-F]+|\d+", "N", body)[:160]] += 1
        elif body.startswith("report "):
            parts = body.split()
            outcomes[f"{parts[1]}:{parts[2]}"] += 1
    print(f"开始的用例 {started}；各阶段结果 {dict(outcomes)}")
    print("会话正常结束" if finished else "会话没有正常结束标记：进程崩溃或被杀")

    if open_at is not None:
        _title("崩溃/卡住时正在执行的阶段（有 BEGIN 没有 END）")
        print(lines[open_at])
        print("\n--- 此前 30 行 ---")
        print("\n".join(lines[max(0, open_at - 30) : open_at]))
        print("\n--- 此后的记录（崩溃前最后写出的内容） ---")
        print("\n".join(lines[open_at + 1 :][-40:]) or "（无）")
    else:
        _title("最后 25 行")
        print("\n".join(lines[-25:]))

    if qt_msgs:
        _title("Qt 消息统计（数字已归一，前 15）")
        for msg, n in qt_msgs.most_common(15):
            print(f"{n:>5} × {msg}")


def _image_name(image: dict) -> str:
    return Path(image.get("path") or image.get("name") or "?").name


def _frame_line(i: int, frame: dict, images: list[dict]) -> str:
    idx = frame.get("imageIndex")
    image = _image_name(images[idx]) if isinstance(idx, int) and idx < len(images) else "?"
    if frame.get("symbol"):
        where = f"{frame['symbol']} + {frame.get('symbolLocation', 0)}"
    else:
        where = f"(无符号) offset=0x{frame.get('imageOffset', 0):x}"
    src = (
        f"  [{frame['sourceFile']}:{frame.get('sourceLine', '?')}]"
        if frame.get("sourceFile")
        else ""
    )
    return f"{i:>3}  {image:<36} {where}{src}"


def _report_ips(text: str) -> bool:
    head, _, body = text.partition("\n")
    try:
        header, data = json.loads(head), json.loads(body)
    except ValueError:
        try:
            header, data = {}, json.loads(text)
        except ValueError:
            return False
    images = data.get("usedImages") or []
    print(
        f"进程: {header.get('app_name') or data.get('procName')}  时间: {header.get('timestamp')}"
    )
    print(
        f"系统: {header.get('os_version') or data.get('osVersion')}  机型: {data.get('modelCode')}"
    )
    exc = data.get("exception") or {}
    print(f"异常: type={exc.get('type')} signal={exc.get('signal')} subtype={exc.get('subtype')}")
    print(f"codes: {exc.get('codes')}")
    print(f"终止: {data.get('termination')}")
    region = data.get("vmRegionInfo")
    if region:
        print(f"出错地址的内存区域: {region}")

    threads = data.get("threads") or []
    crashed = next((t for t in threads if t.get("triggered")), None)
    if crashed is None and threads:
        crashed = threads[min(data.get("faultingThread", 0), len(threads) - 1)]
    if crashed:
        _title(
            f"崩溃线程 id={crashed.get('id')} name={crashed.get('name')} queue={crashed.get('queue')}"
        )
        for i, fr in enumerate(crashed.get("frames") or []):
            print(_frame_line(i, fr, images))
    last = data.get("lastExceptionBacktrace")
    if last:
        _title("lastExceptionBacktrace")
        for i, fr in enumerate(last):
            print(_frame_line(i, fr, images))

    _title(f"其它线程（共 {len(threads)} 个，每个前 4 帧）")
    for t in threads:
        if t is crashed:
            continue
        print(f"-- 线程 {t.get('id')} name={t.get('name')} queue={t.get('queue')}")
        for i, fr in enumerate((t.get("frames") or [])[:4]):
            print(_frame_line(i, fr, images))

    _title("加载的主要库")
    names = sorted({_image_name(im) for im in images})
    keep = [
        n for n in names if re.search(r"Qt|PySide|shiboken|python|libpng|Cocoa|AppKit", n, re.I)
    ]
    print("\n".join(keep) or "\n".join(names[:40]))
    return True


def _report_crash_text(text: str) -> None:
    lines = text.splitlines()
    for key in ("Exception Type", "Exception Codes", "Termination Reason", "Triggered by Thread"):
        for ln in lines:
            if ln.startswith(key):
                print(ln)
    for i, ln in enumerate(lines):
        if re.match(r"Thread \d+ Crashed", ln):
            print()
            print("\n".join(lines[i : i + 45]))
            return
    print("\n".join(lines[:80]))


def report_crash(target: Path) -> None:
    """解析崩溃报告文件或目录。"""
    files = (
        [target] if target.is_file() else sorted(target.glob("*"), key=lambda p: p.stat().st_mtime)
    )
    files = [f for f in files if f.suffix in (".ips", ".crash")]
    _title(f"崩溃报告 {target}")
    if not files:
        print("没有找到 .ips / .crash 文件（系统可能没写出报告，或进程不是被信号杀掉的）")
        return
    for f in files:
        _title(f"报告 {f.name}（{f.stat().st_size} 字节）")
        text = f.read_text(encoding="utf-8", errors="replace")
        if f.suffix == ".ips" and _report_ips(text):
            continue
        _report_crash_text(text)


def main(argv: list[str]) -> int:
    if len(argv) < 3 or argv[1] not in ("trace", "crash"):
        print(__doc__)
        return 2
    for arg in argv[2:]:
        (report_trace if argv[1] == "trace" else report_crash)(Path(arg))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
