"""실험 로그 분석 → 그림(PNG) + 결과표(Markdown).

  python3 analyze.py static ../data/E1_*.csv            --out ../results/E1
  python3 analyze.py vib    ../data/E2_*.csv            --out ../results/E2
  python3 analyze.py gait   ../data/E3_*.csv            --out ../results/E3          (참값 = Arduino 명령 펄스)
  python3 analyze.py gait   ../data/E4_S1_t1.csv --video ../data/E4_S1_t1_video.csv --out ../results/E4  (참값 = 영상)

gait 분석의 기준
  - 실시간 출력의 '실효 지연' = HS 시점 오차 평균 − 사후(영위상) 필터의 HS 시점 오차 평균
    (참값에 서보 지연이나 영상 판정 기준 같은 일정한 치우침이 있어도 빼고 나면 필터 몫만 남는다)
  - 정밀도 = HS 시점 오차의 표준편차(지터)
  - 파형 오차 = 지연 보정 후 사후 기준 신호와의 RMSE
  - '사후 수준' 판정: 지터 ≤ 사후 지터 × (1+tol) + 1 ms 이고 파형 오차 ≤ 원신호의 파형 오차 × wtol
    → 이를 만족하는 가장 작은 지연 = d*
"""
import argparse
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import signal, stats
import warnings
import filters as F
import logio

warnings.filterwarnings("ignore", message="Glyph")
plt.rcParams.update({"font.size": 10, "axes.grid": True, "grid.alpha": 0.3, "figure.dpi": 120})
for fam in ("Malgun Gothic", "AppleGothic", "NanumGothic", "Noto Sans CJK KR"):
    from matplotlib import font_manager
    if any(fam in f.name for f in font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = fam
        break
plt.rcParams["axes.unicode_minus"] = False
COL = {"Butterworth": "#1f5fad", "1euro": "#d9572b", "Kalman": "#2e8b57", "raw": "#555555"}


def w_signal(d, meta):
    if "w" in d:
        return d["w"]
    ax = int(meta.get("w_axis", 2)); sg = float(meta.get("w_sign", 1))
    return sg * d[["gx", "gy", "gz"][ax]]


# ---------------------------------------------------------------- E1/E2: 흔들림
def cmd_noise(files, out, vib=False):
    os.makedirs(out, exist_ok=True)
    rows = []
    fig, axs = plt.subplots(1, 2, figsize=(12, 4.2))
    for path in files:
        d, meta, fs = logio.load(path)
        name = os.path.splitext(os.path.basename(path))[0]
        lab = f"{name} (AAF {'ON' if meta.get('aaf') == '1' else 'OFF'}, {fs:g} Hz)"
        w = w_signal(d, meta)
        r = dict(file=name, aaf=meta.get("aaf"), fs=fs)
        for k, v in F.noise_metrics(w, fs).items():
            r["w_" + k] = v
        if "tilt" in d:
            for k, v in F.noise_metrics(d["tilt"], fs).items():
                r["tilt_" + k] = v
        for c in ("w_bw", "w_1e", "w_kf", "w_fir", "tilt_f"):
            if c in d:
                r[c + "_std"] = F.noise_metrics(d[c], fs)["std"]
        f, P = signal.welch(w - w.mean(), fs=fs, nperseg=min(len(w), int(4 * fs)))
        band = (f > 0.5)
        r["peak_hz"] = float(f[band][np.argmax(P[band])])
        rows.append(r)
        axs[0].plot(f, 10 * np.log10(P + 1e-12), lw=1.2, label=lab)
        k = slice(int(2 * fs), int(7 * fs))
        axs[1].plot(d["t"][k], w[k] - np.mean(w[k]), lw=0.9, label=lab)
    axs[0].set(xlabel="주파수 (Hz)", ylabel="PSD (dB re 1 (deg/s)²/Hz)", title="정강이 축 각속도 스펙트럼")
    axs[1].set(xlabel="시간 (s)", ylabel="각속도 - 평균 (deg/s)", title="정지 상태 흔들림 (5 s)")
    for a in axs:
        a.legend(fontsize=7)
    fig.tight_layout(); fig.savefig(os.path.join(out, "noise_psd.png")); plt.close(fig)

    # 표
    lines = ["| 파일 | AAF | fs | w 표준편차 (deg/s) | w 피크-피크 | 주 피크 (Hz) | tilt 표준편차 (deg) | BW/1€/KF/FIR 표준편차 (deg/s) |",
             "|---|---|---:|---:|---:|---:|---:|---|"]
    for r in rows:
        filt = " / ".join(f"{r[c + '_std']:.3f}" for c in ("w_bw", "w_1e", "w_kf", "w_fir") if c + "_std" in r) or "-"
        lines.append(f"| {r['file']} | {r.get('aaf')} | {r['fs']:g} | {r['w_std']:.3f} | {r['w_p2p']:.2f} | "
                     f"{r['peak_hz']:.1f} | {r.get('tilt_std', float('nan')):.3f} | {filt} |")
    # 칼만 R 추천: 정지 잡음 분산
    if rows and not vib:
        lines += ["", f"- 칼만 측정 잡음 분산 R 추천값(정지 w 분산 평균): **{np.mean([r['w_std'] ** 2 for r in rows]):.4f} (deg/s)²**"
                  "  → STM32 `q<q>,<R>` 명령과 analyze의 --kf-r 에 사용. 대역폭(10 Hz)을 유지하려면 q도 같은 배율로: q = 376000 × R"]
    _write(out, "noise", lines)

    if vib and len(files) >= 1:
        _bar_shake(files, out)


def _bar_shake(files, out):
    """흔들림 막대그래프 (발표 슬라이드용): 각 파일에서 raw와 필터 출력의 표준편차."""
    fig, ax = plt.subplots(figsize=(7, 4))
    width = 0.8 / len(files)
    labels = ["raw", "Butterworth", "1€", "Kalman", "FIR(d)"]
    cols = ["w", "w_bw", "w_1e", "w_kf", "w_fir"]
    for i, path in enumerate(files):
        d, meta, fs = logio.load(path)
        vals = [np.std(d[c]) if c in d else np.nan for c in cols]
        ax.bar(np.arange(5) + i * width, vals, width,
               label=f"AAF {'ON' if meta.get('aaf') == '1' else 'OFF'}")
    ax.set_xticks(np.arange(5) + width * (len(files) - 1) / 2); ax.set_xticklabels(labels)
    ax.set(ylabel="표준편차 (deg/s)", title="정지 + 진동 상태의 흔들림 크기")
    ax.legend(); fig.tight_layout(); fig.savefig(os.path.join(out, "shake_bar.png")); plt.close(fig)


# ---------------------------------------------------------------- E3/E4: 보행 이벤트
def truth_from_video(d, video_csv, fps_default=100.0):
    fps = fps_default; rows = []
    with open(video_csv) as f:
        for line in f:
            line = line.strip()
            if line.startswith("#"):
                if "fps=" in line:
                    fps = float(line.split("fps=")[1].split()[0])
                continue
            if not line or line.startswith("frame"):
                continue
            fr, typ = line.split(",")[:2]
            rows.append((int(fr) / fps, typ.strip().upper()))
    vs = np.array([t for t, y in rows if y == "SYNC"])
    isync = logio.events(d, 3)
    if len(vs) == 0 or len(isync) == 0:
        raise SystemExit("영상과 IMU 모두에 SYNC 이벤트가 필요합니다 (Arduino 'y' 명령 + LED).")
    if len(vs) >= 2 and len(isync) >= 2:
        scale = (isync[-1] - isync[0]) / (vs[-1] - vs[0])
    else:
        scale = 1.0
    conv = lambda tv: isync[0] + (tv - vs[0]) * scale
    hs = np.array([conv(t) for t, y in rows if y == "HS"])
    to = np.array([conv(t) for t, y in rows if y == "TO"])
    return hs, to, dict(fps=fps, clock_scale=scale, n_sync=len(vs))


def cmd_gait(files, out, video=None, fc=10.0, d_list=(1, 2, 3, 5, 8, 10, 15), kf_r=1.0, tol=0.10, wtol=0.30,
             euro=(8.0, 0.01, 10.0)):
    os.makedirs(out, exist_ok=True)
    kf_q = F.kalman_q_for_cutoff(fc, 100.0, kf_r, "rts")   # RTS(사후)의 -3 dB = fc 가 되도록 → 계열 간 공정 비교
    per = {}            # name → list of dicts (파일별)
    stride_err = {}     # name → list of arrays (참값 HS 순서대로, NaN 포함) — 통계용
    example = None
    bias_log = []
    for fi, path in enumerate(files):
        d, meta, fs = logio.load(path)
        x = w_signal(d, meta)
        if video:
            hs_true, to_true, vinfo = truth_from_video(d, video[fi] if isinstance(video, list) else video)
        else:
            hs_true, to_true = logio.events(d, 1), logio.events(d, 2)
        res = F.run_all(x, fs, fc, d_list, euro, kf_q, kf_r)
        res.append(dict(family="raw", timing="raw", d=0, y=x.copy(), name="raw"))
        ref = next(r["y"] for r in res if r["name"] == "BW zero-phase")
        ref_rms = float(np.sqrt(np.mean((ref - ref.mean()) ** 2)))
        T_end = d["t"][-1]
        hs_true = hs_true[(hs_true > 2) & (hs_true < T_end - 2)]
        to_true = to_true[(to_true > 2) & (to_true < T_end - 2)]
        # 참값의 일정한 치우침(서보 지연, 영상 판정 기준) = 사후 기준 이벤트와의 중앙값 차이 → 제거 후 비교
        ev_ref = F.detect_events(ref, fs)
        b_hs = _bias(ev_ref["hs"] / fs, hs_true); b_to = _bias(ev_ref["to"] / fs, to_true)
        bias_log.append((os.path.basename(path), b_hs * 1000, b_to * 1000))
        for r in res:
            ev = F.detect_events(r["y"], fs)
            err = _aligned_err(ev["hs"] / fs, hs_true + b_hs)
            to_err = _aligned_err(ev["to"] / fs, to_true + b_to)
            D, rmse, _ = F.delay_and_rmse(r["y"], ref, fs)
            per.setdefault(r["name"], []).append(dict(
                family=r["family"], timing=r["timing"], d=r["d"], hs_mean=np.nanmean(err) * 1000,
                hs_sd=np.nanstd(err) * 1000, to_mean=np.nanmean(to_err) * 1000, to_sd=np.nanstd(to_err) * 1000,
                D=D, rmse=rmse, ref_rms=ref_rms, n=int(np.isfinite(err).sum()), n_true=len(hs_true)))
            stride_err.setdefault(r["name"], []).append(err * 1000)
        if example is None:
            example = (d["t"], res, hs_true, fs, os.path.basename(path))

    # 파일 평균 → 표
    summ = []
    for name, lst in per.items():
        s = {k: lst[0][k] for k in ("family", "timing", "d")}
        for k in ("hs_mean", "hs_sd", "to_mean", "to_sd", "D", "rmse", "ref_rms"):
            s[k] = float(np.nanmean([v[k] for v in lst]))
        s["n"] = sum(v["n"] for v in lst); s["n_true"] = sum(v["n_true"] for v in lst); s["name"] = name
        summ.append(s)
    off = next(s for s in summ if s["name"] == "BW zero-phase")
    raw_rmse = next(s for s in summ if s["name"] == "raw")["rmse"]
    for s in summ:
        s["lat"] = s["hs_mean"] - off["hs_mean"]
        s["offline_level"] = (s["hs_sd"] <= off["hs_sd"] * (1 + tol) + 1.0) and (s["rmse"] <= wtol * raw_rmse)

    # d*: 실시간(causal/fixed-lag) 중 사후 수준을 만족하는 최소 실효 지연 (계열별)
    dstar = {}
    for fam in ("Butterworth", "1euro", "Kalman"):
        ok = [s for s in summ if s["family"] == fam and s["timing"] in ("causal", "fixed-lag") and s["offline_level"]]
        dstar[fam] = min(ok, key=lambda s: s["lat"]) if ok else None

    order = {"raw": 0, "causal": 1, "fixed-lag": 2, "offline": 3}
    summ.sort(key=lambda s: (["raw", "Butterworth", "1euro", "Kalman"].index(s["family"]), order[s["timing"]], s["d"] or 0))
    lines = [f"- 파일 {len(files)}개, 참값 HS {summ[0]['n_true']}개, fc = {fc} Hz, 칼만 q = {kf_q:.0f} (R = {kf_r})",
             f"- 참값: {'영상 주석(SYNC 정렬)' if video else 'Arduino 명령 펄스(서보 지연 포함 → 실효 지연은 사후 대비 차이로 봄)'}",
             f"- 사후 수준 판정: HS 지터 ≤ 사후 지터 × {1 + tol:.2f} + 1 ms, 그리고 파형 RMSE(사후 기준 대비) ≤ 원신호 RMSE × {wtol:.2f}"
             "  (= 원신호가 사후 결과와 다른 정도를 {:.0f}% 이상 줄임)".format(100 * (1 - wtol)),
             "- 실효 지연은 사후(영위상) 대비 값이라 음수가 될 수 있음 (충격 파형을 덜 평활하면 극소가 더 일찍 잡힘)",
             "- 참값 치우침(사후 기준 대비 중앙값, 제거 후 비교) HS / TO (ms): "
             + "; ".join(f"{n} {a:+.0f} / {b:+.0f}" for n, a, b in bias_log),
             "", "| 계열 | 시점 | 설정 | 실효 지연 (ms) | HS 지터 SD (ms) | TO 오차 평균±SD (ms) | 파형 지연 D (ms) | 파형 RMSE (deg/s) | 사후 수준 |",
             "|---|---|---|---:|---:|---:|---:|---:|:---:|"]
    for s in summ:
        lines.append(f"| {s['family']} | {s['timing']} | {s['name']} | {s['lat']:+.1f} | {s['hs_sd']:.1f} | "
                     f"{s['to_mean']:+.1f} ± {s['to_sd']:.1f} | {s['D']:.1f} | {s['rmse']:.2f} | {'O' if s['offline_level'] else ''} |")
    lines += ["", "## 최소 지연 d* (계열별, 실시간 중 '사후 수준'을 처음 만족하는 설정)", ""]
    for fam, s in dstar.items():
        lines.append(f"- {fam}: " + (f"**{s['lat']:.1f} ms** ({s['name']})" if s else "조건 만족 설정 없음"))

    # 통계: 대표 설정들의 보폭별 |HS 오차 − 사후 평균| → Friedman + Wilcoxon(Holm)
    reps = ["BW causal fc=%g" % fc, "1€ causal", "KF"] + [s["name"] for s in dstar.values() if s] + ["BW zero-phase"]
    reps = list(dict.fromkeys(r for r in reps if r in stride_err))
    M = np.column_stack([np.concatenate(stride_err[r]) for r in reps])
    M = M[np.all(np.isfinite(M), axis=1)]
    if M.shape[0] >= 5 and M.shape[1] >= 3:
        Fs, pF = stats.friedmanchisquare(*M.T)
        lines += ["", "## 통계 (보폭별 HS 시점 오차, 같은 보폭끼리 대응)", "",
                  f"- Friedman χ² = {Fs:.1f}, p = {pF:.2g} (보폭 {M.shape[0]}개, 조건 {M.shape[1]}개)"]
        base = reps.index("BW zero-phase")
        ps = []
        for j, r in enumerate(reps):
            if j != base:
                ps.append((r, stats.wilcoxon(M[:, j], M[:, base]).pvalue))
        ps.sort(key=lambda x: x[1]); m = len(ps)
        for i, (r, p) in enumerate(ps):
            lines.append(f"- {r} vs 사후: Wilcoxon p = {p:.2g}, Holm 보정 p = {min(1, p * (m - i)):.2g}")
    _write(out, "gait", lines)

    # 그림 1: 지연–정확도
    fig, axs = plt.subplots(1, 2, figsize=(12, 4.5))
    for fam in ("Butterworth", "1euro", "Kalman"):
        ss = [s for s in summ if s["family"] == fam]
        for tim, mk in (("causal", "o"), ("fixed-lag", "s"), ("offline", "*")):
            q = [s for s in ss if s["timing"] == tim]
            if not q:
                continue
            xs = [s["lat"] for s in q]
            axs[0].plot(xs, [s["hs_sd"] for s in q], mk + ("-" if tim == "fixed-lag" else ""), color=COL[fam], ms=8 if tim == "offline" else 6,
                        label=f"{fam} {tim}")
            axs[1].plot(xs, [s["rmse"] for s in q], mk + ("-" if tim == "fixed-lag" else ""), color=COL[fam], ms=8 if tim == "offline" else 6)
        if dstar[fam]:
            axs[0].axvline(dstar[fam]["lat"], color=COL[fam], ls=":", lw=1)
    raw = next(s for s in summ if s["family"] == "raw")
    axs[0].plot(raw["lat"], raw["hs_sd"], "x", color="k", ms=8, label="raw")
    axs[0].axhline(off["hs_sd"] * (1 + tol), color="gray", ls="--", lw=1)
    axs[0].set(xlabel="실효 지연 (ms, 사후 대비)", ylabel="HS 지터 SD (ms)", title="지연-정밀도 (점선: 계열별 d*)")
    axs[1].set(xlabel="실효 지연 (ms, 사후 대비)", ylabel="파형 RMSE vs 사후 (deg/s)", title="지연-파형 오차")
    axs[0].legend(fontsize=7, ncol=2)
    fig.tight_layout(); fig.savefig(os.path.join(out, "latency_accuracy.png")); plt.close(fig)

    # 그림 2: 한 보폭 파형
    t, res, hs_true, fs, fname = example
    if len(hs_true) > 3:
        c = hs_true[len(hs_true) // 2]; m = (t > c - 0.8) & (t < c + 0.4)
        fig, ax = plt.subplots(figsize=(9, 4.2))
        pick = ["raw", "BW causal fc=%g" % fc, "KF", "1€ causal", "BW zero-phase"]
        for s in dstar.values():
            if s:
                pick.append(s["name"])
        for r in res:
            if r["name"] in pick:
                fam = r["family"]
                ax.plot(t[m], r["y"][m], lw=2 if r["timing"] == "offline" else 1.2,
                        ls="--" if r["timing"] == "fixed-lag" else "-",
                        color=COL.get(fam, "k") if r["timing"] != "offline" else "k", alpha=0.5 if fam == "raw" else 1,
                        label=r["name"])
        ax.axvline(c, color="r", lw=1, label="참값 HS")
        ax.set(xlabel="시간 (s)", ylabel="정강이 각속도 (deg/s)", title=f"한 보폭 (파일 {fname})")
        ax.legend(fontsize=7); fig.tight_layout(); fig.savefig(os.path.join(out, "stride_example.png")); plt.close(fig)
    print("\n".join(lines))


def _bias(est, true, win=0.5):
    if len(est) == 0 or len(true) == 0:
        return 0.0
    diffs = [est[np.argmin(np.abs(est - t))] - t for t in true]
    diffs = [x for x in diffs if abs(x) < win]
    return float(np.median(diffs)) if diffs else 0.0


def _aligned_err(est, true, win=0.25):
    """참값 순서대로 가장 가까운 추정과의 차이(s). 없거나 win 밖이면 NaN."""
    out = np.full(len(true), np.nan)
    if len(est):
        for i, t in enumerate(true):
            j = int(np.argmin(np.abs(est - t)))
            if abs(est[j] - t) < win:
                out[i] = est[j] - t
    return out


def _write(out, name, lines):
    with open(os.path.join(out, f"{name}.md"), "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"[저장] {os.path.join(out, name + '.md')}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("mode", choices=["static", "vib", "gait"])
    p.add_argument("files", nargs="+")
    p.add_argument("--out", default="../results")
    p.add_argument("--video", nargs="*", help="gait: 영상 주석 CSV (파일 순서대로)")
    p.add_argument("--fc", type=float, default=10.0)
    p.add_argument("--kf-r", type=float, default=1.0)
    p.add_argument("--tol", type=float, default=0.10)
    p.add_argument("--wtol", type=float, default=0.30)
    a = p.parse_args()
    if a.mode in ("static", "vib"):
        cmd_noise(a.files, a.out, vib=a.mode == "vib")
    else:
        cmd_gait(a.files, a.out, a.video, a.fc, kf_r=a.kf_r, tol=a.tol, wtol=a.wtol)


if __name__ == "__main__":
    main()
