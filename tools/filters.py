"""필터·이벤트 검출·지표 (PC 분석과 STM32 펌웨어가 같은 식을 쓰도록 맞춘 기준 구현).

세 가지 '적용 시점'
  causal    : 지금까지의 샘플만 사용 (실시간, 지연 = 필터 고유 지연)
  fixed-lag : d 샘플을 기다린 뒤 출력 (실시간, 지연 = d + 필터 고유 지연이 상쇄된 값)
  offline   : 전체 기록 사용 (영위상, 실시간 불가)
"""
import numpy as np
from scipy import signal


# ----------------------------------------------------------------------------
# 1. Butterworth
# ----------------------------------------------------------------------------
def butter_causal(x, fc, fs, order=2):
    b, a = signal.butter(order, fc, fs=fs)
    return signal.lfilter(b, a, x, zi=signal.lfilter_zi(b, a) * x[0])[0]


def butter_offline(x, fc, fs, order=2):
    """filtfilt. 왕복 후 -3 dB가 fc가 되도록 0.802 보정 (2차 기준, Winter 2009)."""
    b, a = signal.butter(order, fc / 0.802, fs=fs)
    return signal.filtfilt(b, a, x)


def fir_fixed_lag(x, fc, fs, d):
    """선형위상 FIR(Hamming 창), 길이 2d+1 → 모든 주파수에서 지연이 정확히 d 샘플.
    출력 y[k]는 x[k-d] 시점의 추정. 정렬된(지연 제거) 신호를 원하면 shift_back(y, d)."""
    h = signal.firwin(2 * d + 1, fc, fs=fs)
    return signal.lfilter(h, 1.0, np.concatenate([np.full(2 * d, x[0]), x]))[2 * d:]


# ----------------------------------------------------------------------------
# 2. 1€ filter (Casiez et al., CHI 2012)
# ----------------------------------------------------------------------------
def one_euro(x, fs, min_cut=8.0, beta=0.01, d_cut=10.0):
    te = 1.0 / fs
    alpha = lambda fc: 1.0 / (1.0 + 1.0 / (2 * np.pi * fc * te))
    y = np.empty_like(x, dtype=float)
    x_prev, xh, dxh = x[0], x[0], 0.0
    a_d = alpha(d_cut)
    for k, v in enumerate(x):
        dxh += a_d * ((v - x_prev) * fs - dxh)
        xh += alpha(min_cut + beta * abs(dxh)) * (v - xh)
        y[k] = xh
        x_prev = v
    return y


# ----------------------------------------------------------------------------
# 3. 칼만 계열 (등속 모델, 상태 [w, dw/dt])
# ----------------------------------------------------------------------------
def kalman_family(z, fs, q, r=1.0, lags=(0,)):
    """lags 원소: 0 → 칼만 필터, d>0 → 고정지연 스무더(시각 k에 x_{k-d} 추정을 출력),
    'rts' → RTS 스무더(오프라인). 반환: {lag: 출력 배열}. 고정지연 출력은 '시각 k에 나온 값'
    배열이므로 원 신호 대비 d 샘플 늦다."""
    T = 1.0 / fs
    F = np.array([[1, T], [0, 1]])
    Q = q * np.array([[T**3 / 3, T**2 / 2], [T**2 / 2, T]])
    n = len(z)
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
        else:
            y = np.empty(n)
            for k in range(n):
                xs = xf[k]
                for j in range(k - 1, max(0, k - d) - 1, -1):
                    xs = xf[j] + C[j] @ (xs - xp[j + 1])
                y[k] = xs[0]
            out[d] = y
    return out


def gain_at(fn, f0, fs, n=4000):
    imp = np.zeros(n); imp[n // 2] = 1.0
    H = np.abs(np.fft.rfft(fn(imp)))
    return float(np.interp(f0, np.fft.rfftfreq(n, 1 / fs), H))


def kalman_q_for_cutoff(fc, fs, r=1.0, mode=0):
    """칼만(mode=0) 또는 RTS(mode='rts')의 -3 dB 주파수가 fc가 되는 q (r 고정). 이분 탐색."""
    lo, hi = 1e-2, 1e12
    for _ in range(60):
        mid = np.sqrt(lo * hi)
        g = gain_at(lambda x: kalman_family(x, fs, mid, r, (mode,))[mode], fc, fs, 1000)
        lo, hi = (mid, hi) if g < 1 / np.sqrt(2) else (lo, mid)
    return float(mid)


# ----------------------------------------------------------------------------
# 4. 실행 묶음: 필터 × 시점
# ----------------------------------------------------------------------------
def shift_back(y, d):
    """고정지연 출력(시각 k에 x_{k-d} 추정)을 원래 시간축으로 정렬. 끝 d개는 NaN."""
    if d == 0:
        return y.copy()
    out = np.full_like(y, np.nan, dtype=float)
    out[:-d] = y[d:]
    return out


def run_all(x, fs, fc=10.0, d_list=(1, 2, 3, 5, 8, 10), euro=(8.0, 0.01, 10.0), kf_q=None, kf_r=1.0):
    """반환: list of dict(name, family, timing, d, y) — y는 '출력이 나온 시각' 기준(실시간 관점).
    fixed-lag의 d는 '기다린 샘플 수'."""
    res = []
    add = lambda fam, tim, d, y, name: res.append(dict(family=fam, timing=tim, d=d, y=y, name=name))
    add("Butterworth", "causal", 0, butter_causal(x, fc, fs), f"BW causal fc={fc:g}")
    for d in d_list:
        add("Butterworth", "fixed-lag", d, fir_fixed_lag(x, fc, fs, d), f"FIR fixed-lag d={d}")
    add("Butterworth", "offline", None, butter_offline(x, fc, fs), "BW zero-phase")
    add("1euro", "causal", 0, one_euro(x, fs, *euro), "1€ causal")
    for d in d_list:   # 1€는 비선형 인과 필터 → 고정지연 버전 = 1€ 뒤 대칭 이동평균 대신, 앞뒤 1€ 평균(전후방)
        add("1euro", "fixed-lag", d, _euro_fixed_lag(x, fs, euro, d), f"1€ fwd-bwd lag d={d}")
    add("1euro", "offline", None, 0.5 * (one_euro(x, fs, *euro) + one_euro(x[::-1], fs, *euro)[::-1]), "1€ fwd-bwd")
    q = kf_q if kf_q is not None else kalman_q_for_cutoff(fc, fs, kf_r)
    kf = kalman_family(x, fs, q, kf_r, (0, *d_list, "rts"))
    add("Kalman", "causal", 0, kf[0], "KF")
    for d in d_list:
        add("Kalman", "fixed-lag", d, kf[d], f"KF fixed-lag d={d}")
    add("Kalman", "offline", None, kf["rts"], "RTS")
    return res


def _euro_fixed_lag(x, fs, euro, d):
    """1€의 고정지연 변형: 시각 k에서 길이 W(=4d) 창의 역방향 1€를 x_{k-d}까지 돌려 전방 출력과 평균.
    (계산량이 크므로 분석용. MCU 데모에는 넣지 않는다.)"""
    fwd = one_euro(x, fs, *euro)
    n = len(x); y = np.empty(n); W = max(4 * d, d + 1)
    for k in range(n):
        s = max(0, k - W)
        seg = x[s:k + 1][::-1]
        b = one_euro(seg, fs, *euro)[::-1]
        j = max(0, k - d)
        y[k] = 0.5 * (fwd[j] + b[j - s])
    return y


# ----------------------------------------------------------------------------
# 5. 보행 이벤트 검출 (정강이 시상면 각속도)
# ----------------------------------------------------------------------------
def detect_events(w, fs, ms_height=None, min_stride_s=0.6, hs_win=(0.03, 0.35), to_win=(0.05, 0.45)):
    """mid-swing(MS) = 큰 양의 피크. HS = MS 뒤 첫 극소, TO = MS 앞 극소 (Aminian 2002 계열).
    반환: dict(ms, hs, to) 샘플 인덱스(실수, 포물선 보간)."""
    w = np.asarray(w, float)
    ok = np.isfinite(w)
    ww = np.where(ok, w, np.nanmedian(w))
    if ms_height is None:
        ms_height = 0.5 * np.nanpercentile(ww, 99)
    ms, _ = signal.find_peaks(ww, height=ms_height, distance=int(min_stride_s * fs))
    hs, to = [], []
    for p in ms:
        a, b = p + int(hs_win[0] * fs), p + int(hs_win[1] * fs)
        if b < len(ww) and ok[a:b].all():
            hs.append(_parabolic(ww, a + int(np.argmin(ww[a:b]))))
        a, b = p - int(to_win[1] * fs), p - int(to_win[0] * fs)
        if a >= 0 and ok[a:b].all():
            to.append(_parabolic(ww, a + int(np.argmin(ww[a:b]))))
    return dict(ms=ms.astype(float), hs=np.array(hs), to=np.array(to))


def _parabolic(y, i):
    if 0 < i < len(y) - 1:
        den = y[i - 1] - 2 * y[i] + y[i + 1]
        if den != 0:
            return i + 0.5 * (y[i - 1] - y[i + 1]) / den
    return float(i)


def match_events(est_t, true_t, max_err=0.15):
    """각 참값 이벤트에 가장 가까운 추정 이벤트의 오차(est - true, s). 범위 밖은 제외."""
    est_t = np.asarray(est_t); errs = []
    for t in true_t:
        if est_t.size == 0:
            break
        j = int(np.argmin(np.abs(est_t - t)))
        if abs(est_t[j] - t) <= max_err:
            errs.append(est_t[j] - t)
    return np.array(errs)


# ----------------------------------------------------------------------------
# 6. 지표
# ----------------------------------------------------------------------------
def delay_and_rmse(y, ref, fs, max_lag_s=0.25, edge_s=1.0):
    """y(t)가 ref(t-D)와 가장 잘 맞는 D(ms, 샘플 해상도→포물선 보간)와 그때의 RMSE."""
    n = len(y); e = int(edge_s * fs); L = int(max_lag_s * fs)
    errs = []
    for D in range(L):
        k = np.arange(e + D, n - e)
        a, b = y[k], ref[k - D]
        m = np.isfinite(a) & np.isfinite(b)
        errs.append(np.sqrt(np.mean((a[m] - b[m]) ** 2)))
    errs = np.array(errs); i = int(np.argmin(errs))
    return 1000 * _parabolic(errs, i) / fs, float(errs[i]), float(errs[0])


def noise_metrics(x, fs):
    """정지 구간 흔들림 지표: 표준편차, 피크-피크, 0.1 s 창 RMS의 평균."""
    x = np.asarray(x, float) - np.mean(x)
    w = max(1, int(0.1 * fs))
    rms = np.sqrt(np.convolve(x ** 2, np.ones(w) / w, mode="valid"))
    return dict(std=float(np.std(x)), p2p=float(np.ptp(x)), rms100ms=float(np.mean(rms)))
