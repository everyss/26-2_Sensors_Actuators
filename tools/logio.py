"""STM32 로그(CSV) 읽기. '#' 줄은 메타데이터(key=value), 첫 비주석 줄은 열 이름."""
import re
import numpy as np


def load(path):
    meta, header, rows = {}, None, []
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line.startswith("#"):
                for k, v in re.findall(r"(\w+)=([^\s]+)", line):
                    meta.setdefault(k, v)            # 처음 값 유지 (기록 시작 시점 설정)
                continue
            if header is None:
                header = line.split(",")
                continue
            parts = line.split(",")
            if len(parts) != len(header):
                continue                             # 깨진 줄(직렬 끊김) 무시
            try:
                rows.append([float(x) for x in parts])
            except ValueError:
                continue
    a = np.array(rows)
    d = {h: a[:, i] for i, h in enumerate(header)}
    d["t"] = (d["t_us"] - d["t_us"][0]) * 1e-6
    fs = float(meta.get("fs", 0)) or 1.0 / np.median(np.diff(d["t"]))
    d["_t0_us"] = d["t_us"][0]
    return d, meta, fs


def events(d, code):
    """ev 열에서 코드(1=HS, 2=TO, 3=SYNC) 이벤트 시각(s, 로그 시간축). ev_us(인터럽트 시각) 사용."""
    m = d["ev"] == code
    return (d["ev_us"][m] - d["_t0_us"]) * 1e-6
