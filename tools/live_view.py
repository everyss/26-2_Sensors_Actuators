"""실시간 화면 (최종 발표 데모용).

  python live_view.py --port COM5 --rig-port COM6            # 실제 장비 (Windows 예시)
  python live_view.py --port /dev/ttyACM0 --rig-port /dev/ttyUSB0
  python live_view.py --replay ../data/sim/E3_gait_impact.csv  # 장비 없이 리허설

화면
  위   : 정강이 각속도 raw(회색) + Butterworth / 1€ / 칼만 / FIR 고정지연 (최근 5 s), HS·TO 참값 표시
  가운데: 가속도 기반 기울기 raw vs 바늘에 표시 중인 필터
  오른쪽: '흔들림' 막대 (최근 2 s 고역 성분 표준편차)와 각 필터의 지연 추정(ms)

키
  1~5 리그 프리셋(정지 / 정지+진동 / 느린 보행 / 보행+충격 / 보행+충격+진동)
  a  센서 내부 AAF 켬/끔      k  바늘 필터 바꾸기      b  자이로 바이어스 재측정
  y  동기 펄스(LED)           r  기록 시작/종료(../data/live_YYYYmmdd_HHMMSS.csv)
  space 화면 멈춤
"""
import argparse
import collections
import datetime
import os
import re
import sys
import threading
import time

import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui, QtWidgets

COLS = ["t_us", "ax", "ay", "az", "gx", "gy", "gz", "ev", "ev_us", "w", "w_bw", "w_1e", "w_kf", "w_fir", "tilt", "tilt_f"]
FILT = [("w_bw", "Butterworth", "#1f77b4"), ("w_1e", "1€", "#ff7f0e"), ("w_kf", "Kalman", "#2ca02c"), ("w_fir", "FIR 고정지연", "#d62728")]
WIN_S = 5.0


class Source(threading.Thread):
    """직렬 포트 또는 기록 파일에서 줄을 읽어 큐에 넣는다."""

    def __init__(self, port=None, baud=921600, replay=None, speed=1.0):
        super().__init__(daemon=True)
        self.q = collections.deque(maxlen=20000)
        self.meta = {}; self.header = COLS; self.lines_for_log = None
        self.port, self.baud, self.replay, self.speed = port, baud, replay, speed
        self.ser = None; self.alive = True

    def send(self, cmd):
        if self.ser:
            self.ser.write((cmd + "\n").encode())

    def _on_line(self, line):
        line = line.strip()
        if not line:
            return
        if self.lines_for_log is not None:
            self.lines_for_log.append(line)
        if line.startswith("#"):
            for k, v in re.findall(r"(\w+)=([^\s]+)", line):
                self.meta[k] = v
            m = re.search(r"needle=(.+?)(\s+w_axis|$)", line)
            if m:
                self.meta["needle_name"] = m.group(1)
            return
        if line.startswith("t_us"):
            self.header = line.split(","); return
        p = line.split(",")
        if len(p) != len(self.header):
            return
        try:
            self.q.append(dict(zip(self.header, map(float, p))))
        except ValueError:
            pass

    def run(self):
        if self.replay:
            with open(self.replay, encoding="utf-8") as f:
                lines = f.readlines()
            t_prev = None; t_wall = time.perf_counter()
            for line in lines:
                if not self.alive:
                    return
                self._on_line(line)
                if self.q and t_prev is None:
                    t_prev = self.q[-1]["t_us"]
                if self.q and not line.startswith(("#", "t_us")):
                    dt = (self.q[-1]["t_us"] - t_prev) * 1e-6 / self.speed
                    t_wall += dt; t_prev = self.q[-1]["t_us"]
                    lag = t_wall - time.perf_counter()
                    if lag > 0:
                        time.sleep(lag)
            return
        import serial
        self.ser = serial.Serial(self.port, self.baud, timeout=0.05)
        time.sleep(0.2); self.send("?")
        buf = b""
        while self.alive:
            buf += self.ser.read(4096)
            *lines, buf = buf.split(b"\n")
            for ln in lines:
                self._on_line(ln.decode(errors="replace"))


class Viewer(QtWidgets.QMainWindow):
    def __init__(self, src, rig=None):
        super().__init__()
        self.src, self.rig = src, rig
        self.setWindowTitle("IMU 필터 비교 — 실시간")
        self.n = 1000; self.buf = {c: collections.deque(maxlen=self.n) for c in COLS}
        self.events = collections.deque(maxlen=50)
        self.paused = False; self.rec = None; self.needle_k = 0; self.aaf = True

        pg.setConfigOptions(antialias=True, background="w", foreground="k")
        w = pg.GraphicsLayoutWidget(); self.setCentralWidget(w)
        font = QtGui.QFont(); font.setPointSize(11)

        self.p1 = w.addPlot(row=0, col=0, title="정강이 각속도 (deg/s)")
        self.p1.addLegend(offset=(10, 10)); self.p1.showGrid(x=True, y=True, alpha=0.3)
        self.c_raw = self.p1.plot(pen=pg.mkPen("#999999", width=1.5), name="raw")
        self.c_f = {k: self.p1.plot(pen=pg.mkPen(col, width=2), name=nm) for k, nm, col in FILT}
        self.ev_items = []

        self.p2 = w.addPlot(row=1, col=0, title="기울기 (deg): 가속도 raw vs 바늘 필터")
        self.p2.addLegend(offset=(10, 10)); self.p2.showGrid(x=True, y=True, alpha=0.3)
        self.c_tilt = self.p2.plot(pen=pg.mkPen("#999999", width=1.5), name="raw")
        self.c_tiltf = self.p2.plot(pen=pg.mkPen("#d9572b", width=2.5), name="filtered")
        self.p2.setXLink(self.p1)

        self.p3 = w.addPlot(row=0, col=1, title="흔들림 (최근 2 s, 고역 성분 SD, deg/s)")
        self.bar = pg.BarGraphItem(x=np.arange(5), height=np.zeros(5), width=0.6,
                                   brushes=["#999999"] + [c for _, _, c in FILT])
        self.p3.addItem(self.bar)
        self.p3.getAxis("bottom").setTicks([list(enumerate(["raw", "BW", "1€", "KF", "FIR"]))])
        self.info = pg.TextItem(anchor=(0, 0), color="k"); self.info.setFont(font)
        p4 = w.addViewBox(row=1, col=1); p4.addItem(self.info); p4.setRange(xRange=(0, 1), yRange=(0, 1))
        self.info.setPos(0, 1)
        w.ci.layout.setColumnStretchFactor(0, 3); w.ci.layout.setColumnStretchFactor(1, 1)

        self.timer = QtCore.QTimer(); self.timer.timeout.connect(self.update); self.timer.start(33)
        self.last_info = 0; self.rate = 0; self.cnt = 0; self.t_rate = time.time()

    # ------------------------------------------------------------------ 키
    def keyPressEvent(self, e):
        k = e.text()
        if k in "12345" and k:
            self._rig(f"P{int(k) - 1}")
        elif k == "a":
            self.aaf = not self.aaf; self.src.send(f"a{int(self.aaf)}")
        elif k == "k":
            self.needle_k = (self.needle_k + 1) % 5; self.src.send(f"k{self.needle_k}")
        elif k == "b":
            self.src.send("b")
        elif k == "y":
            self._rig("y")
        elif k == "r":
            self.toggle_rec()
        elif k == " ":
            self.paused = not self.paused

    def _rig(self, cmd):
        if self.rig:
            self.rig.write((cmd + "\n").encode())

    def toggle_rec(self):
        if self.rec is None:
            os.makedirs(os.path.join(os.path.dirname(__file__), "..", "data"), exist_ok=True)
            self.rec = os.path.join(os.path.dirname(__file__), "..", "data",
                                    datetime.datetime.now().strftime("live_%Y%m%d_%H%M%S.csv"))
            self.src.lines_for_log = ["# " + " ".join(f"{k}={v}" for k, v in self.src.meta.items()), ",".join(self.src.header)]
        else:
            with open(self.rec, "w") as f:
                f.write("\n".join(self.src.lines_for_log) + "\n")
            print("saved", self.rec); self.rec = None; self.src.lines_for_log = None

    # ------------------------------------------------------------------ 갱신
    def update(self):
        new = 0
        while self.src.q:
            r = self.src.q.popleft(); new += 1
            for c in COLS:
                self.buf[c].append(r.get(c, np.nan))
            if r.get("ev", 0) > 0:
                self.events.append((r["ev_us"], int(r["ev"])))
        self.cnt += new
        if time.time() - self.t_rate > 1:
            self.rate = self.cnt / (time.time() - self.t_rate); self.cnt = 0; self.t_rate = time.time()
        if self.paused or len(self.buf["t_us"]) < 10:
            return
        t_us = np.array(self.buf["t_us"]); t = (t_us - t_us[-1]) * 1e-6
        m = t > -WIN_S
        g = lambda c: np.array(self.buf[c])
        self.c_raw.setData(t[m], g("w")[m])
        for k, _, _ in FILT:
            self.c_f[k].setData(t[m], g(k)[m])
        self.c_tilt.setData(t[m], g("tilt")[m]); self.c_tiltf.setData(t[m], g("tilt_f")[m])
        for it in self.ev_items:
            self.p1.removeItem(it)
        self.ev_items = []
        for eus, code in self.events:
            x = (eus - t_us[-1]) * 1e-6
            if x > -WIN_S and code in (1, 2):
                it = pg.InfiniteLine(pos=x, angle=90, pen=pg.mkPen("#c00000" if code == 1 else "#0050c0", width=1.5,
                                                                   style=QtCore.Qt.DashLine),
                                     label="HS" if code == 1 else "TO", labelOpts=dict(position=0.95, color="k"))
                self.p1.addItem(it); self.ev_items.append(it)
        self.p1.setXRange(-WIN_S, 0, padding=0)

        # 흔들림: 최근 2 s에서 (신호 − 중심 5점 이동평균)의 표준편차
        fs = float(self.src.meta.get("fs", 100))
        n2 = int(2 * fs)
        hf = []
        for c in ["w", "w_bw", "w_1e", "w_kf", "w_fir"]:
            x = g(c)[-n2:]
            if len(x) < 10:
                hf.append(0); continue
            ma = np.convolve(x, np.ones(5) / 5, mode="valid")
            hf.append(float(np.std(x[2:-2] - ma)))
        self.bar.setOpts(height=hf)

        if time.time() - self.last_info > 0.5:
            self.last_info = time.time()
            x = g("w")[-int(4 * fs):]
            lines = []
            for k, nm, _ in FILT:
                y = g(k)[-int(4 * fs):]
                lag = _lag_ms(x, y, fs) if len(x) > 50 and np.std(x) > 5 else float("nan")
                lines.append(f"{nm:<12s} 지연 ≈ {lag:5.0f} ms   흔들림 {hf[[k for k, _, _ in FILT].index(k) + 1]:.2f}")
            meta = self.src.meta
            txt = (f"수신 {self.rate:5.1f} Hz   AAF {'ON' if meta.get('aaf', '1') == '1' else 'OFF'}\n"
                   f"바늘: {meta.get('needle_name', '-')}\n"
                   f"raw 흔들림 {hf[0]:.2f}\n\n" + "\n".join(lines) +
                   ("\n\n● REC" if self.rec else "") +
                   "\n\n[1-5] 프리셋  [a] AAF  [k] 바늘필터\n[y] 동기  [r] 기록  [space] 멈춤")
            self.info.setText(txt)


def _lag_ms(x, y, fs, max_lag=25):
    """y(t) ≈ x(t−L)인 L(ms). raw 대비 필터 출력이 늦은 정도."""
    best, bl = 1e18, 0
    for L in range(0, max_lag):
        e = np.mean((y[L:] - x[:len(x) - L]) ** 2)
        if e < best:
            best, bl = e, L
    return 1000.0 * bl / fs


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--port"); p.add_argument("--baud", type=int, default=921600)
    p.add_argument("--rig-port"); p.add_argument("--rig-baud", type=int, default=115200)
    p.add_argument("--replay"); p.add_argument("--speed", type=float, default=1.0)
    p.add_argument("--screenshot", help="(시험용) N초 뒤 화면 저장 후 종료"); p.add_argument("--after", type=float, default=6)
    a = p.parse_args()
    if not (a.port or a.replay):
        p.error("--port 또는 --replay 필요")
    src = Source(a.port, a.baud, a.replay, a.speed); src.start()
    rig = None
    if a.rig_port:
        import serial
        rig = serial.Serial(a.rig_port, a.rig_baud, timeout=0.05)
    app = QtWidgets.QApplication(sys.argv)
    v = Viewer(src, rig); v.resize(1500, 850); v.show()
    if a.screenshot:
        def shot():
            v.grab().save(a.screenshot); print("saved", a.screenshot); app.quit()
        QtCore.QTimer.singleShot(int(a.after * 1000), shot)
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
