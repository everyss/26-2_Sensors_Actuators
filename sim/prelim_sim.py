"""
예비 시뮬레이션 (최종): 하지(정강이) IMU 자이로 신호의 사전 / 고정지연(결합) / 사후 필터링

핵심 관점: 사전(실시간, d = 0)과 사후(오프라인, d = 무한대)는 '허용 지연 d'라는 하나의 축의 양 끝이고,
그 사이에 '고정지연 필터'(실시간으로 돌되 d만큼 늦게 출력해 약간의 미래 샘플을 쓰는 필터)가 있다.
필터 계열마다 지연(ms)과 정확도(지연 보정 RMSE)를 스윕해 '지연 예산별 최선의 필터'를 찾는다.

- 합성(가상) 보행 신호이므로 실측 결과가 아니라 방법론 타당성 검증용이다.
- 피험자 A = 학습형 필터 학습용, 피험자 B = 평가용 (파형, 보폭, 잡음이 다름)

필터 계열
- 고전 선형  : 2차 Butterworth (인과)  / 선형위상 FIR (고정지연)          / 영위상 Butterworth (사후)
- 적응형     : 1 Euro filter (인과, Casiez 2012)
- 모델 기반  : 칼만 필터 (인과)        / 고정지연 칼만 스무더 (고정지연)  / RTS 스무더 (사후)
- 데이터 기반: 학습 FIR (사후 출력을 정답으로 최소제곱 학습, 인과 또는 고정지연)  [확장]
             + 같은 정답으로 학습한 소형 신경망과 비교

실행: python3 prelim_sim.py  ->  figures/*.png, results_table.md 생성
"""

import os

import matplotlib.pyplot as plt
import numpy as np
from scipy import signal
from sklearn.neural_network import MLPRegressor

HERE = os.path.dirname(os.path.abspath(__file__))
FIG_DIR = os.path.join(HERE, "figures")
os.makedirs(FIG_DIR, exist_ok=True)

FS_HI = 1000          # '연속 신호' 대용 (Hz)
FS = 100              # 웨어러블에서 흔한 출력 샘플링 (Hz)
DEC = FS_HI // FS
FC_POST = 10.0        # 사후 필터 차단 주파수 (Hz). 실제 실험에서는 residual analysis로 결정
AAF_HZ = 42           # 센서 내부 AAF (2차 버터워스 근사)
EDGE = 2.0            # 지표 계산 시 양 끝 제외 (s)
WIN = 20              # 학습 FIR 입력 창 길이 (샘플, 200 ms)
MAX_D = 150           # 지연 탐색 범위 (ms)

# 두 '가상 피험자': 보폭 시간, 진폭, 파형 위치, 연부조직 잡음 크기가 다르다
SUBJ_A = dict(stride=1.10, amp=1.00, hs=(-100, 0.00, 0.015), st=(60, 0.30, 0.12),
              to=(-170, 0.60, 0.025), ms=(380, 0.80, 0.055), sta=6.0, seed=1, dur=120)
SUBJ_B = dict(stride=1.00, amp=0.90, hs=(-120, 0.00, 0.018), st=(50, 0.28, 0.11),
              to=(-150, 0.62, 0.028), ms=(400, 0.78, 0.050), sta=7.0, seed=2, dur=60)

# 색상 (dataviz 기본 팔레트 고정 순서, 참값/raw/오프라인 기준선은 중립 회색)
C_TRUTH, C_RAW, C_REF = "#3a3a38", "#b8b7b2", "#8c8b85"
C_CLASSIC, C_EURO, C_KF, C_LEARN = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"
C_GRID, C_TEXT2 = "#e4e3df", "#52514e"


# ---------------------------------------------------------------------------
# 1. 합성 보행 신호 (정강이 시상면 각속도, deg/s)
# ---------------------------------------------------------------------------
def gait_template(phase, p):
    """phase: 0=heel strike(HS), ~0.6=toe off(TO), ~0.8=mid-swing(MS)."""
    out = np.zeros_like(phase)
    for a, c, s in (p["hs"], p["st"], p["to"], p["ms"]):
        d = (phase - c + 0.5) % 1.0 - 0.5            # 주기 경계 wrap
        out += a * np.exp(-0.5 * (d / s) ** 2)
    return out


def make_subject(p):
    rng = np.random.default_rng(p["seed"])
    t = np.arange(0, p["dur"], 1 / FS_HI)
    n_str = int(p["dur"] / p["stride"]) + 5
    T_str = p["stride"] * (1 + 0.03 * rng.standard_normal(n_str))   # 보폭 시간 변동
    amp = p["amp"] * (1 + 0.05 * rng.standard_normal(n_str))        # 보폭별 진폭 변동
    starts = np.concatenate([[0.0], np.cumsum(T_str)]) - 0.5
    idx = np.searchsorted(starts, t, side="right") - 1
    phase = (t - starts[idx]) / T_str[idx]
    truth = amp[idx] * gait_template(phase, p)

    # 아티팩트: HS 충격 과도응답(35 Hz) + 104 Hz 진동(가정) + 백색 잡음 + 연부조직 잡음(12-30 Hz)
    art = np.zeros_like(t)
    for s in starts[(starts > 0) & (starts < p["dur"])]:
        m = t >= s
        dt = t[m] - s
        art[m] += 60 * np.exp(-dt / 0.015) * np.sin(2 * np.pi * 35 * dt + rng.uniform(0, 2 * np.pi))
    art += 12 * np.sin(2 * np.pi * 104 * t + rng.uniform(0, 2 * np.pi))
    art += 2.0 * rng.standard_normal(t.size)
    b, a = signal.butter(4, [12, 30], btype="band", fs=FS_HI)
    sta = signal.filtfilt(b, a, rng.standard_normal(t.size))
    art += p["sta"] * sta / sta.std()
    return dict(t_hi=t, truth_hi=truth, meas_hi=truth + art)


B_AAF, A_AAF = signal.butter(2, AAF_HZ, fs=FS_HI)


def acquire(meas_hi, aaf):
    x = signal.lfilter(B_AAF, A_AAF, meas_hi) if aaf else meas_hi
    return x[::DEC]


# ---------------------------------------------------------------------------
# 2. 필터
# ---------------------------------------------------------------------------
def butter_pre(x, fc):                         # 2차 버터워스, 인과 (MCU에서 biquad 1개)
    b, a = signal.butter(2, fc, fs=FS)
    return signal.lfilter(b, a, x, zi=signal.lfilter_zi(b, a) * x[0])[0]


def butter_post(x, fc):                        # 영위상 filtfilt. 왕복 후 -3 dB가 fc가 되도록 보정(0.802, Winter)
    b, a = signal.butter(2, fc / 0.802, fs=FS)
    return signal.filtfilt(b, a, x)


def fir_fixed_lag(x, fc, d):                   # 선형위상 FIR: 길이 2d+1, 모든 주파수에서 지연이 정확히 d 샘플
    h = signal.firwin(2 * d + 1, fc, fs=FS)
    return signal.lfilter(h, 1.0, np.concatenate([np.full(d, x[0]), x]))[d:]


def one_euro(x, min_cut, beta, d_cut):
    """1 Euro filter (Casiez et al., CHI 2012): 변화 속도에 따라 차단 주파수를 바꾸는 적응형 1차 LPF."""
    te = 1.0 / FS

    def alpha(fc):
        return 1.0 / (1.0 + 1.0 / (2 * np.pi * fc * te))

    y = np.empty_like(x)
    x_prev, xh, dxh = x[0], x[0], 0.0
    a_d = alpha(d_cut)
    for k, v in enumerate(x):
        dxh += a_d * ((v - x_prev) * FS - dxh)
        xh += alpha(min_cut + beta * abs(dxh)) * (v - xh)
        y[k] = xh
        x_prev = v
    return y


def kalman_family(z, q, lags, r=1.0):
    """1D 칼만 필터, 상태 [w, dw/dt] 등속 모델.
    lags의 각 d에 대해: d=0 -> 칼만 필터, d>0 -> 고정지연 스무더(시각 k에 x_{k-d} 출력), 'rts' -> RTS 스무더."""
    T = 1 / FS
    F = np.array([[1, T], [0, 1]])
    Q = q * np.array([[T**3 / 3, T**2 / 2], [T**2 / 2, T]])
    n = z.size
    xp = np.zeros((n, 2)); Pp = np.zeros((n, 2, 2))
    xf = np.zeros((n, 2)); Pf = np.zeros((n, 2, 2))
    x = np.array([z[0], 0.0]); P = np.diag([r, 1e4])
    for k in range(n):
        if k > 0:
            x = F @ x
            P = F @ P @ F.T + Q
        xp[k], Pp[k] = x, P
        K = P[:, 0] / (P[0, 0] + r)
        x = x + K * (z[k] - x[0])
        P = P - np.outer(K, P[0, :])
        xf[k], Pf[k] = x, P
    C = [Pf[k] @ F.T @ np.linalg.inv(Pp[k + 1]) for k in range(n - 1)]
    out = {}
    for d in lags:
        if d == 0:
            out[d] = xf[:, 0].copy()
        elif d == "rts":
            xs = xf.copy()
            for k in range(n - 2, -1, -1):
                xs[k] = xf[k] + C[k] @ (xs[k + 1] - xp[k + 1])
            out[d] = xs[:, 0]
        else:                                     # 시각 k까지의 데이터로 x_{k-d} 추정 (실시간 가능, 지연 d)
            y = np.empty(n)
            for k in range(n):
                xs = xf[k]
                for j in range(k - 1, max(0, k - d) - 1, -1):
                    xs = xf[j] + C[j] @ (xs - xp[j + 1])
                y[k] = xs[0]
            out[d] = y
    return out


def lagged(x, win=WIN):
    """[x_k, x_{k-1}, ..., x_{k-win+1}] 행렬 (과거 샘플만 사용 = 인과)."""
    xp = np.concatenate([np.full(win - 1, x[0]), x])
    return np.lib.stride_tricks.sliding_window_view(xp, win)[:, ::-1]


class LearnedFIR:
    """사후 출력을 d 샘플 늦춘 신호를 정답으로 최소제곱 학습한 FIR (= 데이터로 구한 고정지연 위너 필터)."""
    def fit(self, x, teacher, d, lam=1e-3):
        tgt = np.concatenate([np.full(d, teacher[0]), teacher[: teacher.size - d]])
        X = np.hstack([lagged(x), np.ones((x.size, 1))])
        self.w = np.linalg.solve(X.T @ X + lam * np.eye(X.shape[1]), X.T @ tgt)
        return self

    def __call__(self, x):
        return np.hstack([lagged(x), np.ones((x.size, 1))]) @ self.w


class TinyMLP:
    """같은 정답으로 학습한 소형 신경망 (입력 20 -> 32 -> 32 -> 1). 선형 학습 FIR 대비 이득이 있는지 확인용."""
    S = 300.0

    def fit(self, x, teacher, d):
        tgt = np.concatenate([np.full(d, teacher[0]), teacher[: teacher.size - d]])
        self.m = MLPRegressor(hidden_layer_sizes=(32, 32), activation="tanh", alpha=1e-2,
                              max_iter=600, early_stopping=True, random_state=0)
        self.m.fit(lagged(x) / self.S, tgt / self.S)
        return self

    def __call__(self, x):
        return self.m.predict(lagged(x) / self.S) * self.S


def gain_at(fn, f0, n=2000):
    imp = np.zeros(n); imp[n // 2] = 1.0
    H = np.abs(np.fft.rfft(fn(imp)))
    return np.interp(f0, np.fft.rfftfreq(n, 1 / FS), H)


# ---------------------------------------------------------------------------
# 3. 지표
# ---------------------------------------------------------------------------
def evaluate(y, truth_hi):
    """지연 D(ms)와 지연 보정 RMSE: 출력 y_k를 참값 x(t_k - D)와 비교해 오차가 최소가 되는 D.
    실시간 시스템에서 지연 D가 일정하면 '지금 보고 있는 값은 D ms 전의 값'이므로 이 쌍이 곧 성능이다."""
    k = np.arange(int(EDGE * FS), y.size - int(EDGE * FS))
    errs = np.array([np.sqrt(np.mean((y[k] - truth_hi[k * DEC - D]) ** 2)) for D in range(MAX_D)])
    D = int(np.argmin(errs))

    # heel strike 시점 오차 (1 ms 해상도), mid-swing 피크 오차
    e_up = signal.resample_poly(y, DEC, 1)
    tr = truth_hi[: e_up.size]
    pk, _ = signal.find_peaks(tr, height=250, distance=700)
    pk = pk[(pk > EDGE * FS_HI) & (pk < tr.size - EDGE * FS_HI - 400)]
    hs, peak = [], []
    for p in pk:
        w = slice(p + 50, p + 400)
        hs.append(np.argmin(e_up[w]) - np.argmin(tr[w]))
        peak.append(e_up[p - 50: p + 200].max() / tr[p] - 1)
    return dict(D=D, err=float(errs[D]), err0=float(errs[0]), hs=float(np.mean(hs)),
                hs_sd=float(np.std(hs)), peak=100 * float(np.mean(peak)))


def pareto(points):
    """(D, err, ...) 목록에서 지연이 늘수록 오차가 줄어드는 점만 남긴다 (파레토 전선)."""
    front, best = [], np.inf
    for pnt in sorted(points, key=lambda p: (p["D"], p["err"])):
        if pnt["err"] < best:
            front.append(pnt)
            best = pnt["err"]
    return front


def best_within(front, budget):
    ok = [p for p in front if p["D"] <= budget]
    return min(ok, key=lambda p: p["err"]) if ok else None


# 1샘플당 곱셈-누적(MAC) 수 근사: 아두이노/STM32 부담 비교용
def mac_count(cfg):
    fam = cfg["family"]
    if fam == "Classical":
        return 5 if cfg["mode"] == "causal" else 2 * cfg["d"] + 1
    if fam == "1-Euro":
        return 12
    if fam == "Kalman":
        return 30 + 12 * cfg.get("d", 0)
    if fam == "Learned FIR":
        return WIN + 1
    return 0


# ---------------------------------------------------------------------------
# 4. 실행
# ---------------------------------------------------------------------------
def main():
    A, B = make_subject(SUBJ_A), make_subject(SUBJ_B)
    xa, xb = acquire(A["meas_hi"], True), acquire(B["meas_hi"], True)
    tb = B["truth_hi"]

    def run(family, mode, y, **cfg):
        r = evaluate(y, tb)
        r.update(family=family, mode=mode, y=y, **cfg)
        r["mac"] = mac_count(r)
        return r

    pts = {"Classical": [], "1-Euro": [], "Kalman": [], "Learned FIR": []}
    for fc in (4, 5, 6, 7, 8, 10, 12, 15, 20, 25, 30, 40):
        pts["Classical"].append(run("Classical", "causal", butter_pre(xb, fc), fc=fc, d=0))
    for fc in (10, 12, 15):
        for d in (1, 2, 3, 4, 5, 6, 8):
            pts["Classical"].append(run("Classical", "fixed-lag", fir_fixed_lag(xb, fc, d), fc=fc, d=d))
    for dc in (3, 10, 30):
        for mc in (2, 4, 8, 12, 16):
            for be in (1e-3, 3e-3, 1e-2, 3e-2):
                pts["1-Euro"].append(run("1-Euro", "causal", one_euro(xb, mc, be, dc),
                                         min_cut=mc, beta=be, d_cut=dc, d=0))
    # 칼만: -3 dB = FC_POST가 되는 q를 기준으로 몇 배씩 스윕
    lo, hi = 1e1, 1e9
    for _ in range(50):
        mid = np.sqrt(lo * hi)
        if gain_at(lambda x: kalman_family(x, mid, ["rts"])["rts"], FC_POST) < 1 / np.sqrt(2):
            lo = mid
        else:
            hi = mid
    q_ref = mid
    for qm in (0.1, 0.3, 1, 3, 10, 30):
        outs = kalman_family(xb, q_ref * qm, [0, 1, 2, 3, 5, 8])
        for d, y in outs.items():
            pts["Kalman"].append(run("Kalman", "causal" if d == 0 else "fixed-lag", y, q=q_ref * qm, d=d))
    teacher_a = butter_post(xa, FC_POST)            # 학습 FIR의 정답: 피험자 A의 사후 필터 출력
    for d in (0, 1, 2, 3, 5, 8):
        f = LearnedFIR().fit(xa, teacher_a, d)
        pts["Learned FIR"].append(run("Learned FIR", "causal" if d == 0 else "fixed-lag", f(xb), d=d))

    mlp_check = []
    for d in (0, 1, 2):
        lin = next(p for p in pts["Learned FIR"] if p["d"] == d)
        nn = evaluate(TinyMLP().fit(xa, teacher_a, d)(xb), tb)
        mlp_check.append((d, lin, nn))

    raw = run("Raw", "-", xb)
    post_bw = run("Offline", "zero-phase Butterworth", butter_post(xb, FC_POST))
    post_rts = run("Offline", "RTS smoother", kalman_family(xb, q_ref, ["rts"])["rts"])
    double = run("Double", "causal BW -> zero-phase BW", butter_post(butter_pre(xb, FC_POST), FC_POST))
    floor = post_bw["err"]
    fronts = {k: pareto(v) for k, v in pts.items()}

    # 앨리어싱: 센서 내부 AAF 유무 (사후 필터 후)
    xb_off = acquire(B["meas_hi"], False)
    alias_on = evaluate(butter_post(xb, FC_POST), tb)
    alias_off = evaluate(butter_post(xb_off, FC_POST), tb)

    # H1: MCU식 float32 biquad 루프 == PC 인과 필터?
    b, a = signal.butter(2, FC_POST, fs=FS)
    b32, a32 = b.astype(np.float32), a.astype(np.float32)
    z = (signal.lfilter_zi(b, a) * xb[0]).astype(np.float32)
    online = np.empty(xb.size, dtype=np.float32)
    for k, v in enumerate(xb.astype(np.float32)):       # Direct Form II transposed
        y = b32[0] * v + z[0]
        z[0] = b32[1] * v - a32[1] * y + z[1]
        z[1] = b32[2] * v - a32[2] * y
        online[k] = y
    h1_diff = float(np.max(np.abs(online - butter_pre(xb, FC_POST))))

    # ---- 결과 표 ----
    def cfg_str(p):
        if p["family"] == "Classical":
            return (f"causal Butterworth fc={p['fc']} Hz" if p["mode"] == "causal"
                    else f"linear-phase FIR fc={p['fc']} Hz, d={p['d'] * 10} ms")
        if p["family"] == "1-Euro":
            return f"min_cut={p['min_cut']} Hz, beta={p['beta']:g}, d_cut={p['d_cut']} Hz"
        if p["family"] == "Kalman":
            return "Kalman filter" if p["d"] == 0 else f"fixed-lag smoother d={p['d'] * 10} ms"
        return f"d={p['d'] * 10} ms"

    L = [
        "# 예비 시뮬레이션 결과 (합성 신호, 방법론 검증용)",
        "",
        "- 평가: 가상 피험자 B (60 s, 보폭 1.0 s). 학습 FIR만 피험자 A(120 s, 보폭 1.1 s, 파형·잡음 다름)로 학습",
        f"- 출력 100 Hz, 센서 내부 AAF ~{AAF_HZ} Hz 포함. 사후 필터 -3 dB = {FC_POST:.0f} Hz",
        "- 지연 D: 출력이 참값 x(t - D)와 가장 잘 맞는 D. 오차: 그때의 RMSE (deg/s)",
        f"- H1 검증: MCU식 float32 biquad 루프 vs PC 인과 필터 최대 차이 = {h1_diff:.1e} deg/s",
        "",
        "## 1. 지연 예산별 최선의 정확도 (각 계열 파라미터 스윕의 파레토 전선)",
        "",
        f"오프라인(사후) 기준선: 영위상 Butterworth {floor:.2f} / RTS 스무더 {post_rts['err']:.2f} deg/s "
        f"(지연 {post_bw['D']} ms는 센서 AAF 몫, 실시간 사용 불가). Raw: {raw['err']:.2f} deg/s @ {raw['D']} ms",
        "",
        "| 필터 계열 | 지연 ≤ 10 ms | 지연 ≤ 20 ms | 지연 ≤ 30 ms | 오프라인 수준(기준선 +5%) 도달 지연 |",
        "|---|---|---|---|---|",
    ]
    for fam, fr in fronts.items():
        cells = []
        for bud in (10, 20, 30):
            p = best_within(fr, bud)
            cells.append(f"{p['err']:.2f} ({p['D']} ms)" if p else "-")
        reach = next((p for p in fr if p["err"] <= 1.05 * floor), None)
        cells.append(f"{reach['D']} ms ({cfg_str(reach)})" if reach else "도달 못 함")
        L.append(f"| {fam} | " + " | ".join(cells) + " |")

    reps = [
        ("사전", "Classical", lambda p: p["mode"] == "causal" and p["fc"] == FC_POST),
        ("사전", "1-Euro", lambda p: p is best_within(fronts["1-Euro"], 10)),
        ("사전", "Kalman", lambda p: p["d"] == 0 and p["q"] == q_ref),
        ("결합(고정지연)", "Kalman", lambda p: p is best_within(fronts["Kalman"], 20)),
        ("결합(고정지연)", "Classical", lambda p: p is best_within(
            pareto([q for q in pts["Classical"] if q["mode"] == "fixed-lag"]), 30)),
        ("결합(고정지연)", "Learned FIR", lambda p: p is best_within(fronts["Learned FIR"], 20)),
    ]
    L += ["", "## 2. 대표 설정의 상세 지표", "",
          "| 처리 | 필터 | 설정 | 지연 (ms) | 지연 보정 RMSE | 현재값 RMSE | HS 시점 오차 평균 ± 지터 (ms) | 피크 오차 (%) | MAC/샘플 |",
          "|---|---|---|---:|---:|---:|---:|---:|---:|"]
    rep_pts = {}
    for loc, fam, sel in reps:
        p = next(q for q in pts[fam] if sel(q))
        rep_pts[(loc, fam)] = p
        L.append(f"| {loc} | {fam} | {cfg_str(p)} | {p['D']} | {p['err']:.2f} | {p['err0']:.2f} | "
                 f"{p['hs']:+.1f} ± {p['hs_sd']:.1f} | {p['peak']:+.1f} | {p['mac']} |")
    for loc, p, name in [("사후", post_bw, "zero-phase Butterworth"), ("사후", post_rts, "RTS smoother"),
                         ("단순 중복", double, "causal BW -> zero-phase BW"), ("Raw", raw, "-")]:
        L.append(f"| {loc} | {name} | - | {p['D']} | {p['err']:.2f} | {p['err0']:.2f} | "
                 f"{p['hs']:+.1f} ± {p['hs_sd']:.1f} | {p['peak']:+.1f} | - |")
    L += ["", "## 3. 센서 내부 안티앨리어싱 필터 (사후 Butterworth 적용 후)", "",
          "| 센서 내부 AAF | 지연 (ms) | 지연 보정 RMSE |", "|---|---:|---:|",
          f"| 켬 (~{AAF_HZ} Hz) | {alias_on['D']} | {alias_on['err']:.2f} |",
          f"| 끔 | {alias_off['D']} | {alias_off['err']:.2f} |"]
    L += ["", "## 4. 확장 검토: 신경망 vs 선형 학습 FIR (같은 정답 = 피험자 A의 사후 출력)", "",
          "| 고정지연 d | 학습 FIR: 지연 / 오차 | 소형 MLP 20-32-32-1: 지연 / 오차 |", "|---|---|---|"]
    for d, lin, nn in mlp_check:
        L.append(f"| {d * 10} ms | {lin['D']} ms / {lin['err']:.2f} | {nn['D']} ms / {nn['err']:.2f} |")
    L.append("")
    L.append("정답이 선형 필터 출력이면 신경망이 선형 학습 FIR보다 나아질 이유가 없다 "
             "→ 신경망은 엔코더 참값을 정답으로 쓸 수 있는 벤치 데이터에서만 시도한다.")
    table = "\n".join(L) + "\n"
    with open(os.path.join(HERE, "results_table.md"), "w") as f:
        f.write(table)
    print(table)

    # ---- 그림 공통 스타일 ----
    plt.rcParams.update({
        "font.size": 10, "axes.edgecolor": C_GRID, "axes.labelcolor": C_TEXT2,
        "xtick.color": C_TEXT2, "ytick.color": C_TEXT2, "axes.grid": True,
        "grid.color": C_GRID, "grid.linewidth": 0.8, "axes.spines.top": False,
        "axes.spines.right": False, "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb",
        "lines.solid_capstyle": "round", "legend.frameon": False,
    })
    t_lo = B["t_hi"][::DEC]
    truth_lo = tb[::DEC]

    # Fig 1: 한 보폭 - 실시간 필터들이 지연을 어떻게 쓰는가
    pk, _ = signal.find_peaks(truth_lo, height=250, distance=70)
    p0 = pk[len(pk) // 2]
    w = slice(p0 - 25, p0 + 45)
    tt = (t_lo[w] - t_lo[p0]) * 1000
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    ax.plot(tt, xb[w], color=C_RAW, lw=1, label="Raw")
    ax.plot(tt, truth_lo[w], color=C_TRUTH, lw=2, label="Truth")
    for (loc, fam), col, lab in [(("사전", "Classical"), C_CLASSIC, "Pre: causal Butterworth 10 Hz"),
                                 (("사전", "1-Euro"), C_EURO, "Pre: 1-Euro (adaptive)"),
                                 (("결합(고정지연)", "Kalman"), C_KF, "Fixed-lag Kalman smoother")]:
        p = rep_pts[(loc, fam)]
        ax.plot(tt, p["y"][w], color=col, lw=2, label=f"{lab}  [{p['D']} ms, {p['err']:.1f} deg/s]")
    ax.set_xlabel("Time from mid-swing peak (ms)")
    ax.set_ylabel("Shank ang. vel. (deg/s)")
    ax.legend(loc="upper right", fontsize=8.5)
    ax.set_title("One stride, unseen subject: each real-time filter spends delay differently",
                 loc="left", fontsize=11)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, "fig1_waveform.png"), dpi=160)
    plt.close(fig)

    # Fig 2: 앨리어싱 - 100 Hz 데이터에 남는 잡음 성분(측정 - 참값)의 PSD
    noise_hi = B["meas_hi"] - tb
    fig, ax = plt.subplots(figsize=(7.5, 4))
    ax.axvspan(0, FC_POST, color=C_GRID, alpha=0.6, lw=0)
    psd = {}
    for name, x, col in [("off", noise_hi[::DEC], C_EURO),
                         ("on", signal.lfilter(B_AAF, A_AAF, noise_hi)[::DEC], C_CLASSIC)]:
        f, P = signal.welch(x, fs=FS, nperseg=1024)
        psd[name] = P
        lab = ("No on-chip anti-aliasing filter" if name == "off"
               else f"On-chip anti-aliasing filter (~{AAF_HZ} Hz)")
        ax.semilogy(f, P, color=col, lw=2, label=lab)
    P, Pon = psd["off"], psd["on"]
    i4 = np.argmax(np.where((f > 3) & (f < 5), P, 0))
    ax.annotate("104 Hz vibration folded to 4 Hz\n= inside the gait band,\n   no post-filter can remove it",
                xy=(f[i4], P[i4]), xytext=(13, P[i4] * 0.6), fontsize=9, color="#0b0b0b",
                arrowprops=dict(arrowstyle="-", color=C_TEXT2, lw=0.8), va="center")
    i4b = np.argmax(np.where((f > 3) & (f < 5), Pon, 0))
    ax.annotate(f"{10 * np.log10(P[i4] / Pon[i4b]):.0f} dB lower with pre-filter",
                xy=(f[i4b], Pon[i4b]), xytext=(13, 0.02), fontsize=9, color="#0b0b0b",
                va="center", arrowprops=dict(arrowstyle="-", color=C_TEXT2, lw=0.8))
    ax.text(30, 8, "impact + soft-tissue noise\n(in-band, removable later)", fontsize=8,
            color=C_TEXT2, ha="center")
    ax.text(0.4, 2e-4, f"post-filter\npassband\n(< {FC_POST:.0f} Hz)", fontsize=8, color=C_TEXT2)
    ax.set_xlabel("Frequency (Hz)")
    ax.set_ylabel("Noise PSD ((deg/s)$^2$/Hz)")
    ax.set_xlim(0, 50)
    ax.set_ylim(1e-4, 1e4)
    ax.legend(loc="upper right", fontsize=9)
    ax.set_title("Noise reaching the 100 Hz data: what only a pre-filter (before sampling) can stop",
                 loc="left", fontsize=11)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, "fig2_aliasing_psd.png"), dpi=160)
    plt.close(fig)

    # Fig 3: 지연 예산 vs 정확도 - 계열별 파레토 전선
    fig, ax = plt.subplots(figsize=(7.5, 4.6))
    ax.axhline(floor, color=C_REF, lw=1.5, zorder=1)
    ax.text(58, floor + 0.08, "offline reference: zero-phase Butterworth 10 Hz (not real-time)",
            fontsize=8, color=C_TEXT2, ha="right", va="bottom")
    labels = {"Classical": "Classical (Butterworth / linear-phase FIR)", "1-Euro": "Adaptive (1-Euro)",
              "Kalman": "Model-based (KF / fixed-lag smoother)", "Learned FIR": "Data-driven (learned FIR)"}
    cols = {"Classical": C_CLASSIC, "1-Euro": C_EURO, "Kalman": C_KF, "Learned FIR": C_LEARN}
    for fam, fr in fronts.items():
        fr = [p for p in fr if p["D"] <= 60]
        ax.plot([p["D"] for p in fr], [p["err"] for p in fr], color=cols[fam], lw=2, marker="o",
                markersize=5, markeredgecolor="#fcfcfb", markeredgewidth=0.8, label=labels[fam], zorder=3)
    ax.scatter(raw["D"], raw["err"], s=60, marker="D", color=C_RAW, edgecolors="#fcfcfb",
               linewidths=2, zorder=4)
    ax.annotate("Raw", (raw["D"], raw["err"]), xytext=(6, 4), textcoords="offset points",
                fontsize=8, color=C_TEXT2)
    ax.set_xlim(0, 60)
    ax.set_ylim(floor - 1.0, raw["err"] + 1.5)
    ax.set_xlabel("Latency budget: allowed delay (ms)")
    ax.set_ylabel("Error vs truth, delay-aligned RMSE (deg/s)")
    ax.legend(loc="upper right", fontsize=8.5)
    ax.set_title("Best achievable accuracy for a given delay (Pareto fronts, unseen subject)",
                 loc="left", fontsize=11)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, "fig3_latency_budget.png"), dpi=160)
    plt.close(fig)


if __name__ == "__main__":
    main()
