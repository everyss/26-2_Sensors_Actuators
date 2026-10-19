"""
예비 시뮬레이션: 하지(정강이) IMU 자이로 신호의 사전 vs 사후 필터링 비교

- 합성(가상) 보행 신호이므로 '실측 결과'가 아니라 '방법론 타당성 검증용'이다.
- 사전(Pre)  = 실시간 인과(causal) 필터: MCU에서 샘플이 들어올 때마다 계산
- 사후(Post) = 오프라인 비인과(non-causal) 필터: 저장된 raw 전체를 사용 (영위상 / 스무더)
- 센서 내부 사전 필터(AAF, MPU-6050 DLPF 근사)의 유무에 따른 앨리어싱도 함께 본다.

실행: python3 prelim_sim.py  ->  figures/*.png, results_table.md 생성
"""

import os

import matplotlib.pyplot as plt
import numpy as np
from scipy import signal

rng = np.random.default_rng(7)
HERE = os.path.dirname(os.path.abspath(__file__))
FIG_DIR = os.path.join(HERE, "figures")
os.makedirs(FIG_DIR, exist_ok=True)

FS_HI = 1000          # '연속 신호' 대용 (Hz)
FS = 100              # 웨어러블에서 흔한 출력 샘플링 (Hz)
DEC = FS_HI // FS
DURATION = 60.0       # s
FC = 10.0             # 목표 차단 주파수 (Hz). 각속도는 각도보다 고주파 성분이 많아 6 Hz(Winter)보다 높게.
                      # 실제 실험에서는 residual analysis로 결정한다.
AAF_HZ = 42           # MPU-6050 DLPF_CFG=3 (gyro 42 Hz) 근사
EDGE = 2.0            # 지표 계산 시 양 끝 제외 구간 (s)

# 색상 (dataviz 기본 팔레트 slot 1~3, 참값/raw는 중립 회색)
C_TRUTH, C_RAW = "#3a3a38", "#b8b7b2"
C_PRE, C_POST, C_DUP = "#2a78d6", "#eb6834", "#1baf7a"
C_GRID, C_TEXT2 = "#e4e3df", "#52514e"


# ---------------------------------------------------------------------------
# 1. 합성 보행 신호 (정강이 시상면 각속도, deg/s)
# ---------------------------------------------------------------------------
def gait_template(phase):
    """phase: 0=heel strike(HS), ~0.6=toe off(TO), ~0.8=mid-swing(MS)."""
    def g(c, a, s):
        d = (phase - c + 0.5) % 1.0 - 0.5            # 주기 경계 wrap
        return a * np.exp(-0.5 * (d / s) ** 2)
    return (g(0.00, -100, 0.015) + g(0.30, 60, 0.12)
            + g(0.60, -170, 0.025) + g(0.80, 380, 0.055))


def make_signals():
    t = np.arange(0, DURATION, 1 / FS_HI)
    n_str = int(DURATION / 1.0) + 5
    T_str = 1.1 * (1 + 0.03 * rng.standard_normal(n_str))      # 보폭 시간 변동
    amp = 1 + 0.05 * rng.standard_normal(n_str)                 # 보폭별 진폭 변동
    starts = np.concatenate([[0.0], np.cumsum(T_str)]) - 0.5
    idx = np.searchsorted(starts, t, side="right") - 1
    phase = (t - starts[idx]) / T_str[idx]
    truth = amp[idx] * gait_template(phase)

    # 아티팩트: (1) HS 충격 과도응답 35 Hz, (2) 104 Hz 진동(가정), (3) 광대역 잡음
    art = np.zeros_like(t)
    for s in starts[(starts > 0) & (starts < DURATION)]:
        m = t >= s
        dt = t[m] - s
        art[m] += 60 * np.exp(-dt / 0.015) * np.sin(2 * np.pi * 35 * dt + rng.uniform(0, 2 * np.pi))
    art += 12 * np.sin(2 * np.pi * 104 * t + 0.3)
    art += 2.0 * rng.standard_normal(t.size)
    # (4) 연부조직/스트랩 흔들림(STA) 대역 잡음 12-30 Hz, rms 6 deg/s (가정)
    b, a = signal.butter(4, [12, 30], btype="band", fs=FS_HI)
    sta = signal.filtfilt(b, a, rng.standard_normal(t.size))
    art += 6.0 * sta / sta.std()
    return t, truth, truth + art


# ---------------------------------------------------------------------------
# 2. 필터 (사전 = 인과 / 사후 = 비인과)
# ---------------------------------------------------------------------------
def maf_pre(x, n):
    return signal.lfilter(np.ones(n) / n, 1.0, x)


def maf_post(x, n):                                   # 중심 이동평균 (영위상)
    return np.convolve(x, np.ones(n) / n, mode="same")


def lpf_pre(x, a):                                    # y_k = a*y_{k-1} + (1-a)*x_k
    return signal.lfilter([1 - a], [1, -a], x, zi=[a * x[0]])[0]


def lpf_post(x, a):                                   # forward-backward (filtfilt)
    return signal.filtfilt([1 - a], [1, -a], x)


def _kf(z, q, r, smooth):
    """1D 칼만 필터, 상태 [w, dw/dt] 등속(white-noise accel) 모델. smooth=True면 RTS 스무더."""
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
    if not smooth:
        return xf[:, 0]
    xs = xf.copy(); Ps = Pf.copy()
    for k in range(n - 2, -1, -1):
        C = Pf[k] @ F.T @ np.linalg.inv(Pp[k + 1])
        xs[k] = xf[k] + C @ (xs[k + 1] - xp[k + 1])
        Ps[k] = Pf[k] + C @ (Ps[k + 1] - Pp[k + 1]) @ C.T
    return xs[:, 0]


def kf_pre(x, q, r=1.0):
    return _kf(x, q, r, smooth=False)


def kf_post(x, q, r=1.0):
    return _kf(x, q, r, smooth=True)


def gain_at_fc(fn, n=2000):
    """임펄스 응답으로 |H(FC)| 계산 (정상상태 기준)."""
    imp = np.zeros(n); imp[n // 2] = 1.0
    h = fn(imp)
    H = np.abs(np.fft.rfft(h))
    f = np.fft.rfftfreq(n, 1 / FS)
    return np.interp(FC, f, H)


def tune(make_fn, lo, hi, increasing):
    """|H(FC)| = 1/sqrt(2) 이 되도록 파라미터를 이분 탐색 (공정 비교: 동일 -3 dB 차단 주파수)."""
    target = 1 / np.sqrt(2)
    for _ in range(60):
        mid = np.sqrt(lo * hi) if lo > 0 else (lo + hi) / 2
        gtest = gain_at_fc(make_fn(mid))
        if (gtest < target) == increasing:
            lo = mid
        else:
            hi = mid
    return mid


# ---------------------------------------------------------------------------
# 3. 지표
# ---------------------------------------------------------------------------
UP = 10   # 지연/피크/이벤트를 1 ms 해상도로 보기 위한 업샘플 배율


def metrics(est, truth_lo, truth_hi):
    m = slice(int(EDGE * FS), -int(EDGE * FS))
    rmse = np.sqrt(np.mean((est[m] - truth_lo[m]) ** 2))

    e_up = signal.resample_poly(est, UP, 1)
    tr_up = truth_hi[: e_up.size]
    mh = slice(int(EDGE * FS_HI), -int(EDGE * FS_HI))
    a, b = e_up[mh] - e_up[mh].mean(), tr_up[mh] - tr_up[mh].mean()
    max_lag = 100  # ms
    lags = np.arange(-max_lag, max_lag + 1)
    xc = [np.dot(a[max_lag + L: a.size - max_lag + L], b[max_lag: b.size - max_lag]) for L in lags]
    lag_ms = lags[int(np.argmax(xc))]
    # 지연을 보정한 뒤의 '형상' 오차 (노이즈 잔여 + 파형 왜곡만 남김)
    e_al = e_up[mh.start + lag_ms: mh.stop + lag_ms]
    rmse_al = np.sqrt(np.mean((e_al - tr_up[mh]) ** 2))

    # mid-swing 피크 감쇠, HS 시점 오차 (참값 1 kHz 신호 기준)
    pk, _ = signal.find_peaks(tr_up, height=250, distance=700)
    pk = pk[(pk > EDGE * FS_HI) & (pk < tr_up.size - EDGE * FS_HI)]
    att, hs_err = [], []
    for p in pk:
        w = slice(p - 50, p + 120)
        att.append(e_up[w].max() / tr_up[p] - 1)
        w2 = slice(p + 50, p + 400)
        hs_true = p + 50 + np.argmin(tr_up[w2])
        hs_est = p + 50 + np.argmin(e_up[w2])
        hs_err.append(hs_est - hs_true)
    return dict(rmse=rmse, rmse_al=rmse_al, lag=lag_ms, peak=100 * np.mean(att),
                hs=np.mean(hs_err), hs_sd=np.std(hs_err))


# ---------------------------------------------------------------------------
# 4. 실행
# ---------------------------------------------------------------------------
def main():
    t_hi, truth_hi, meas_hi = make_signals()

    # 샘플링 단계: AAF 없음(DLPF off) vs AAF 있음(DLPF ~20 Hz, 2차 버터워스 근사, 인과)
    b_aaf, a_aaf = signal.butter(2, AAF_HZ, fs=FS_HI)
    raw_noaaf = meas_hi[::DEC]
    raw_aaf = signal.lfilter(b_aaf, a_aaf, meas_hi)[::DEC]
    truth_lo = truth_hi[::DEC]
    t_lo = t_hi[::DEC]

    # 동일 -3 dB(6 Hz)로 파라미터 맞추기
    def maf_f3(n):
        imp = np.zeros(2000); imp[1000] = 1
        H = np.abs(np.fft.rfft(maf_pre(imp, n)))
        f = np.fft.rfftfreq(2000, 1 / FS)
        return f[np.argmax(H < 1 / np.sqrt(2))]
    # 중심 이동평균이 대칭이 되도록 홀수 N 중 -3 dB가 FC에 가장 가까운 값
    N_MAF = min(range(3, 31, 2), key=lambda n: abs(maf_f3(n) - FC))
    f3_maf = maf_f3(N_MAF)
    a_pre = tune(lambda a: (lambda x: lpf_pre(x, a)), 0.01, 0.99, increasing=False)
    a_post = tune(lambda a: (lambda x: lpf_post(x, a)), 0.01, 0.99, increasing=False)
    q_pre = tune(lambda q: (lambda x: kf_pre(x, q)), 1e-2, 1e9, increasing=True)
    q_post = tune(lambda q: (lambda x: kf_post(x, q)), 1e-2, 1e9, increasing=True)

    filters = {
        "MAF": (lambda x: maf_pre(x, N_MAF), lambda x: maf_post(x, N_MAF)),
        "LPF": (lambda x: lpf_pre(x, a_pre), lambda x: lpf_post(x, a_post)),
        "KF":  (lambda x: kf_pre(x, q_pre), lambda x: kf_post(x, q_post)),
    }

    # H1 검증: MCU식 샘플 단위 루프(float32) == 오프라인 인과 필터(float64)?
    x32 = raw_aaf.astype(np.float32)
    y = np.float32(x32[0]); a32 = np.float32(a_pre); online = np.empty_like(x32)
    for k, v in enumerate(x32):
        y = a32 * y + (np.float32(1) - a32) * v
        online[k] = y
    h1_diff = np.max(np.abs(online - lpf_pre(raw_aaf, a_pre)))

    rows, results = [], {}
    for acq_name, raw in [("AAF off", raw_noaaf), ("AAF on", raw_aaf)]:
        results[(acq_name, "Raw", "-")] = metrics(raw, truth_lo, truth_hi)
        for fname, (pre, post) in filters.items():
            y_pre = pre(raw)
            y_post = post(raw)
            y_dup = post(pre(raw))       # 사전+사후 '단순 중복'
            results[(acq_name, "Pre", fname)] = metrics(y_pre, truth_lo, truth_hi)
            results[(acq_name, "Post", fname)] = metrics(y_post, truth_lo, truth_hi)
            results[(acq_name, "Pre+Post(dup)", fname)] = metrics(y_dup, truth_lo, truth_hi)
            if acq_name == "AAF on":
                rows.append((fname, y_pre, y_post, y_dup))

    # ---- 결과 표 ----
    lines = [
        "# 예비 시뮬레이션 결과 (합성 신호, 방법론 검증용)",
        "",
        f"- 출력 샘플링 {FS} Hz, 모든 필터는 -3 dB 차단 주파수 ≈ {FC:.0f} Hz로 맞춤 "
        f"(MAF N={N_MAF} → {f3_maf:.2f} Hz, LPF 사전 α={a_pre:.3f}, LPF 사후(왕복) α={a_post:.3f}, "
        f"KF 사전 q/r={q_pre:.3g}, KF 사후(RTS) q/r={q_post:.3g})",
        f"- H1 검증: MCU식 float32 샘플 루프 vs 오프라인 인과 LPF 최대 차이 = {h1_diff:.2e} deg/s",
        f"- AAF on = 센서 내부 DLPF ~{AAF_HZ} Hz(2차 버터워스 근사), AAF off = DLPF 끔\n"
        "- 지연(lag): 참값 대비 상호상관 최대 지점 (+ = 늦음), 지연 보정 RMSE: 지연만큼 당긴 뒤의 오차, "
        "피크: mid-swing 피크 크기 오차, "
        "HS: heel strike 시점 오차 평균±SD",
        "",
        "| 샘플링 | 처리 위치 | 필터 | RMSE (deg/s) | 지연 보정 RMSE (deg/s) | 지연 (ms) | 피크 오차 (%) | HS 시점 오차 (ms) |",
        "|---|---|---|---:|---:|---:|---:|---:|",
    ]
    for (acq, loc, fn), r in results.items():
        lines.append(f"| {acq} | {loc} | {fn} | {r['rmse']:.1f} | {r['rmse_al']:.1f} | {r['lag']:+d} | "
                     f"{r['peak']:+.1f} | {r['hs']:+.1f} ± {r['hs_sd']:.1f} |")
    table = "\n".join(lines) + "\n"
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

    # Fig 1: 한 보폭 확대 - 사전(인과) vs 사후(영위상)
    pk, _ = signal.find_peaks(truth_lo, height=250, distance=70)
    p0 = pk[len(pk) // 2]
    w = slice(p0 - 25, p0 + 45)
    fig, axes = plt.subplots(3, 1, figsize=(7.5, 8), sharex=True)
    for ax, (fname, y_pre, y_post, _) in zip(axes, rows):
        tt = (t_lo[w] - t_lo[p0]) * 1000
        ax.plot(tt, raw_aaf[w], color=C_RAW, lw=1, label="Raw")
        ax.plot(tt, truth_lo[w], color=C_TRUTH, lw=2, label="Truth")
        ax.plot(tt, y_pre[w], color=C_PRE, lw=2, label="Pre (causal, real-time)")
        ax.plot(tt, y_post[w], color=C_POST, lw=2, label="Post (zero-phase, offline)")
        r1, r2 = results[("AAF on", "Pre", fname)], results[("AAF on", "Post", fname)]
        ax.set_title(f"{fname}   lag: pre {r1['lag']:+d} ms / post {r2['lag']:+d} ms   "
                     f"peak: pre {r1['peak']:+.1f}% / post {r2['peak']:+.1f}%",
                     loc="left", fontsize=10, color="#0b0b0b")
        ax.set_ylabel("Shank ang. vel. (deg/s)")
    axes[0].legend(loc="upper right", ncol=2, fontsize=9)
    axes[-1].set_xlabel("Time from mid-swing peak (ms)")
    fig.suptitle(f"Same {FC:.0f} Hz cutoff, different timing: pre (causal) vs post (zero-phase)",
                 x=0.02, ha="left", fontsize=12)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, "fig1_pre_vs_post_lag.png"), dpi=160)
    plt.close(fig)

    # Fig 2: 앨리어싱 - 100 Hz 데이터에 남는 '잡음 성분'(측정 - 참값)의 PSD
    noise_hi = meas_hi - truth_hi
    fig, ax = plt.subplots(figsize=(7.5, 4))
    ax.axvspan(0, FC, color=C_GRID, alpha=0.6, lw=0)
    psd = {}
    for name, x, col in [("off", noise_hi[::DEC], C_POST),
                         ("on", signal.lfilter(b_aaf, a_aaf, noise_hi)[::DEC], C_PRE)]:
        f, P = signal.welch(x, fs=FS, nperseg=1024)
        psd[name] = (f, P)
        lab = ("No anti-aliasing (DLPF off)" if name == "off"
               else f"On-chip anti-aliasing (DLPF ~{AAF_HZ} Hz)")
        ax.semilogy(f, P, color=col, lw=2, label=lab)
    f, P = psd["off"]
    i4 = np.argmax(np.where((f > 3) & (f < 5), P, 0))
    ax.annotate("104 Hz vibration folded to 4 Hz\n= inside the gait band,\n   no post-filter can remove it",
                xy=(f[i4], P[i4]), xytext=(13, P[i4] * 0.6), fontsize=9, color="#0b0b0b",
                arrowprops=dict(arrowstyle="-", color=C_TEXT2, lw=0.8), va="center")
    i4b = np.argmax(np.where((f > 3) & (f < 5), psd["on"][1], 0))
    ax.annotate(f"{10 * np.log10(P[i4] / psd['on'][1][i4b]):.0f} dB lower with pre-filter",
                xy=(f[i4b], psd["on"][1][i4b]), xytext=(13, 0.02),
                fontsize=9, color="#0b0b0b", va="center",
                arrowprops=dict(arrowstyle="-", color=C_TEXT2, lw=0.8))
    ax.text(30, 8, "impact + soft-tissue noise\n(in-band, removable later)", fontsize=8,
            color=C_TEXT2, ha="center")
    ax.text(0.4, 2e-4, f"post-filter\npassband\n(< {FC:.0f} Hz)", fontsize=8, color=C_TEXT2)
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

    # Fig 3: 정확도-지연 트레이드오프
    fig, ax = plt.subplots(figsize=(7.5, 4.6))
    marker = {"MAF": "o", "LPF": "s", "KF": "^"}
    color = {"Pre": C_PRE, "Post": C_POST, "Pre+Post(dup)": C_DUP}
    for loc in ["Pre", "Post", "Pre+Post(dup)"]:
        for fname in ["MAF", "LPF", "KF"]:
            r = results[("AAF on", loc, fname)]
            ax.scatter(r["lag"], r["rmse_al"], s=70, marker=marker[fname], color=color[loc],
                       edgecolors="#fcfcfb", linewidths=2, zorder=3)
            off = {("Post", "MAF"): (8, 3), ("Post", "LPF"): (8, -6), ("Post", "KF"): (8, -3),
                   ("Pre", "KF"): (8, -9), ("Pre+Post(dup)", "KF"): (8, 3)}.get((loc, fname), (8, 3))
            ax.annotate(f"{fname} ({loc})", (r["lag"], r["rmse_al"]), xytext=off,
                        textcoords="offset points", fontsize=8, color=C_TEXT2)
    r = results[("AAF on", "Raw", "-")]
    ax.scatter(r["lag"], r["rmse_al"], s=70, marker="D", color=C_RAW, edgecolors="#fcfcfb",
               linewidths=2, zorder=2)
    ax.annotate("Raw", (r["lag"], r["rmse_al"]), xytext=(-28, 3), textcoords="offset points",
                fontsize=8, color=C_TEXT2)
    handles = [plt.Line2D([], [], color=color[k], marker="o", lw=0, markersize=8, label=k)
               for k in color]
    handles += [plt.Line2D([], [], color=C_TEXT2, marker=marker[k], lw=0, markersize=7,
                           markerfacecolor="none", label=k) for k in marker]
    handles.insert(3, plt.Line2D([], [], color=C_RAW, marker="D", lw=0, markersize=7, label="Raw"))
    ax.legend(handles=handles, loc="upper left", fontsize=9, ncol=2)
    ax.set_xlim(0, 32)
    ax.set_xlabel("Lag vs truth (ms)   [real-time usability: smaller is better]")
    ax.set_ylabel("Lag-compensated RMSE (deg/s)\n[noise + shape distortion]")
    ax.set_title(f"Accuracy-latency trade-off (AAF on, all filters at {FC:.0f} Hz)", loc="left", fontsize=12)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, "fig3_tradeoff.png"), dpi=160)
    plt.close(fig)


if __name__ == "__main__":
    main()
