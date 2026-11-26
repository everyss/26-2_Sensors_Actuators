"""벤치 리그 가상 데이터 생성기 — 장비가 오기 전 분석·데모 리허설용.

STM32 펌웨어와 같은 CSV 형식(100 Hz 또는 1 kHz)을 만든다.
물리 모델: Arduino와 같은 보행 명령 → 서보(사수시간 + 2차 지연 + 속도 제한) → 스토퍼 충돌
→ 회전 팔의 IMU(자이로, 가속도) → 센서 내부 처리(AAF 켬: 1 kHz + 2차 42 Hz / 끔: 8 kHz 무필터)
→ SMPLRT 솎아내기 → 잡음.

예)
  python3 bench_sim.py --exp static  --aaf 1 --out ../data/sim_E1_static_aaf1.csv
  python3 bench_sim.py --exp vib     --aaf 0 --out ../data/sim_E2_vib_aaf0.csv
  python3 bench_sim.py --exp gait --impact 1 --vib 0 --out ../data/sim_E3_gait_imp.csv
"""
import argparse
import numpy as np
from scipy import signal
import filters as F

FS_IN = 8000            # 내부 시뮬레이션 속도
R_IMU = 0.070           # 축→IMU (m)
G = 9.81


def gait_cmd(t, T=1.2, hs=20.0, to=-25.0, stance=0.6, impact=False, over=6.0):
    ph = np.mod(t / T, 1.0)
    ease = lambda u: 0.5 * (1 - np.cos(np.pi * u))
    u1 = ph / stance
    st = hs + (to - hs) * (0.4 * u1 + 0.6 * u1 ** 2)
    u2 = (ph - stance) / (1 - stance)
    sw = to + (hs + (over if impact else 0) - to) * ease(np.clip(u2, 0, 1))
    return np.where(ph < stance, st, sw), ph


def servo_response(cmd, fs, dead=0.020, wn=2 * np.pi * 6, zeta=0.75, vmax=400.0):
    """사수시간 + 속도 제한 + 2차 지연 (간단한 취미용 서보 모델)."""
    n = len(cmd); k = int(dead * fs)
    c = np.concatenate([np.full(k, cmd[0]), cmd[:-k]]) if k else cmd
    th = np.empty(n); x, v = c[0], 0.0; dt = 1 / fs
    for i in range(n):
        acc = wn * wn * (c[i] - x) - 2 * zeta * wn * v
        v = np.clip(v + acc * dt, -vmax, vmax)
        x += v * dt; th[i] = x
    return th


def simulate(exp, aaf, dur, fs_out=100, T=1.2, impact=False, vib_amp=0.0, vib_hz=203.0, stop_deg=20.0, seed=0):
    rng = np.random.default_rng(seed)
    t = np.arange(0, dur, 1 / FS_IN)
    ev_t, ev_c = [], []
    if exp == "gait":
        cmd, ph = gait_cmd(t, T=T, impact=impact)
        th = servo_response(cmd, FS_IN)
        sw = ph >= 0.6
        hs_idx = np.where(sw[:-1] & sw[1:] & (cmd[:-1] < 20.0) & (cmd[1:] >= 20.0))[0] + 1
        to_idx = np.where((ph[:-1] < 0.6) & (ph[1:] >= 0.6))[0] + 1
        ev_t = list(t[hs_idx]) + list(t[to_idx]); ev_c = [1] * len(hs_idx) + [2] * len(to_idx)
    else:
        th = np.zeros_like(t)
    # 동기 펄스 (Arduino 'y' 명령과 같은 SYNC): 시작 1 s, 끝 1 s 전
    ev_t += [1.0, dur - 1.0]; ev_c += [3, 3]
    w = np.gradient(th, 1 / FS_IN)                                   # deg/s
    # 스토퍼 충돌: 각도를 막고 감쇠 진동(약 45 Hz)을 더함
    ring = np.zeros_like(t)
    if exp == "gait" and impact:
        hit = np.where((th[:-1] < stop_deg) & (th[1:] >= stop_deg))[0]
        for h in hit:
            dt = t[h:] - t[h]
            v0 = max(w[h], 50)
            ring[h:] += -0.9 * v0 * np.exp(-dt / 0.012) * np.cos(2 * np.pi * 45 * dt)
        over = th > stop_deg
        th = np.minimum(th, stop_deg)
        w = np.where(over, 0.0, w)
    w = w + ring
    phys = dict(hs=None, to=None)
    if exp == "gait":     # '영상에서 보일' 물리 이벤트: HS = 암이 스토퍼(또는 hs 각)에 닿는 순간, TO = 후퇴 끝
        crossing = np.where((th[:-1] < stop_deg - 0.5) & (th[1:] >= stop_deg - 0.5))[0]
        phys["hs"] = t[crossing]
        mins = signal.argrelmin(th, order=int(0.3 * FS_IN))[0]
        phys["to"] = t[mins]
    wr = np.deg2rad(w); al = np.gradient(wr, 1 / FS_IN); thr = np.deg2rad(th)
    ax = (-R_IMU * wr ** 2 - G * np.cos(thr)) / G
    ay = (R_IMU * al + G * np.sin(thr)) / G
    az = np.zeros_like(t)
    # 진동모터 + 서보 떨림 + 백색잡음
    vib = np.sin(2 * np.pi * vib_hz * t + rng.uniform(0, 6.28))
    gx = 0.6 * vib_amp * vib; gy = 0.4 * vib_amp * vib; gz = w + vib_amp * vib
    ax = ax + 0.008 * vib_amp * vib; ay = ay + 0.012 * vib_amp * vib; az = az + 0.01 * vib_amp * vib
    chans = [ax, ay, az, gx, gy, gz]
    noise = [0.004, 0.004, 0.004, 0.08, 0.08, 0.08]
    if aaf:
        b, a = signal.butter(2, 42, fs=FS_IN)
        chans = [signal.lfilter(b, a, c, zi=signal.lfilter_zi(b, a) * c[0])[0] for c in chans]
    step = FS_IN // fs_out
    out = [c[::step] + s * rng.standard_normal(c[::step].size) for c, s in zip(chans, noise)]
    tt = t[::step]
    return tt, out, np.array(ev_t), np.array(ev_c, int), phys


def to_csv(path, tt, out, ev_t, ev_c, fs_out, aaf, note, fc=10.0, d=5, kf_q=376000.0):
    ax, ay, az, gx, gy, gz = out
    n = len(tt)
    ev = np.zeros(n, int); ev_us = np.zeros(n, np.int64)
    for t_e, c in zip(ev_t, ev_c):
        k = int(np.ceil(t_e * fs_out + 1e-9))            # 다음 샘플 줄에 기록 (펌웨어와 동일)
        if k < n:
            ev[k] = c; ev_us[k] = int(round(t_e * 1e6)) + 1_000_000
    t_us = (tt * 1e6).astype(np.int64) + 1_000_000
    with open(path, "w") as f:
        f.write(f"# source=bench_sim {note}\n")
        f.write(f"# fs={fs_out} aaf={int(aaf)} fc={fc} fir_d={d} euro=8.00,0.0100,10.00 kf_q={kf_q} kf_r=1.00\n")
        if fs_out <= 200:
            w = gz
            cols = [w, F.butter_causal(w, fc, fs_out), F.one_euro(w, fs_out),
                    F.kalman_family(w, fs_out, kf_q, 1.0, (0,))[0], F.fir_fixed_lag(w, fc, fs_out, d)]
            tilt = np.degrees(np.arctan2(ay, -ax)); tilt_f = F.butter_causal(tilt, fc, fs_out)
            f.write("t_us,ax,ay,az,gx,gy,gz,ev,ev_us,w,w_bw,w_1e,w_kf,w_fir,tilt,tilt_f\n")
            for i in range(n):
                f.write(f"{t_us[i]},{ax[i]:.4f},{ay[i]:.4f},{az[i]:.4f},{gx[i]:.2f},{gy[i]:.2f},{gz[i]:.2f},"
                        f"{ev[i]},{ev_us[i]}," + ",".join(f"{c[i]:.2f}" for c in cols) + f",{tilt[i]:.2f},{tilt_f[i]:.2f}\n")
        else:
            f.write("t_us,ax,ay,az,gx,gy,gz,ev,ev_us\n")
            for i in range(n):
                f.write(f"{t_us[i]},{ax[i]:.4f},{ay[i]:.4f},{az[i]:.4f},{gx[i]:.2f},{gy[i]:.2f},{gz[i]:.2f},{ev[i]},{ev_us[i]}\n")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--exp", choices=["static", "vib", "gait"], required=True)
    p.add_argument("--aaf", type=int, default=1)
    p.add_argument("--fs", type=int, default=100)
    p.add_argument("--dur", type=float, default=60)
    p.add_argument("--impact", type=int, default=1)
    p.add_argument("--vib", type=float, default=None, help="진동 진폭(deg/s). 기본: vib 실험 20, 그 외 0")
    p.add_argument("--vib-hz", type=float, default=203.0)
    p.add_argument("--T", type=float, default=1.2037, help="보행 주기(s). 1.2와 살짝 다르게 해 샘플링 위상이 보폭마다 바뀌게 함(실제 두 MCU 시계 차이 모사)")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--out", required=True)
    p.add_argument("--video-out", help="가상 영상 주석 CSV(100 fps, 프레임 양자화) 저장 — gait 분석 경로 시험용")
    a = p.parse_args()
    vib = a.vib if a.vib is not None else (20.0 if a.exp == "vib" else 0.0)
    tt, out, ev_t, ev_c, phys = simulate(a.exp, a.aaf, a.dur, a.fs, a.T, bool(a.impact), vib, a.vib_hz, seed=a.seed)
    to_csv(a.out, tt, out, ev_t, ev_c, a.fs, a.aaf, f"exp={a.exp} impact={a.impact} vib={vib} vib_hz={a.vib_hz} T={a.T}")
    print("wrote", a.out)
    if a.video_out and a.exp == "gait":
        fps = 100.0; off = 0.437    # 카메라 녹화 시작이 IMU 기록보다 0.437 s 늦었다고 가정
        rows = [(1.0, "SYNC"), (a.dur - 1.0, "SYNC")] + [(x, "HS") for x in phys["hs"]] + [(x, "TO") for x in phys["to"]]
        with open(a.video_out, "w") as f:
            f.write(f"# fps={fps}\nframe,type\n")
            for tv, typ in sorted(rows):
                f.write(f"{int(np.floor((tv - off) * fps))},{typ}\n")
        print("wrote", a.video_out)


if __name__ == "__main__":
    main()
