"""실험 기록기 — STM32 출력 그대로 CSV로 저장 (그래프 없이 가볍게, 실험 본 기록용).

  python log_serial.py --port COM5 --sec 60 --out ../data/E3_gait_imp_r1.csv --cmd a1 --cmd F10 \
         --rig-port COM6 --rig-cmd P3 --sync --note "bench gait impact rep1"

동작 순서: (선택) STM32 명령 전송 → (선택) 리그 명령 → 2 s 대기 → 기록 시작 → (--sync) 시작 직후 SYNC 펄스
→ sec 초 기록 → (--sync) 끝나기 1 s 전 SYNC 펄스 → 저장. 기록 중 받은 '#' 메타데이터도 그대로 저장한다.
"""
import argparse
import time
import serial


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--port", required=True); p.add_argument("--baud", type=int, default=921600)
    p.add_argument("--sec", type=float, default=60); p.add_argument("--out", required=True)
    p.add_argument("--cmd", action="append", default=[], help="STM32 명령 (여러 번 가능)")
    p.add_argument("--rig-port"); p.add_argument("--rig-cmd", action="append", default=[])
    p.add_argument("--sync", action="store_true", help="시작·끝에 Arduino 'y' 동기 펄스 (영상 정렬용)")
    p.add_argument("--note", default="")
    a = p.parse_args()

    s = serial.Serial(a.port, a.baud, timeout=0.05)
    rig = serial.Serial(a.rig_port, 115200, timeout=0.05) if a.rig_port else None
    time.sleep(2.0 if rig else 0.2)                      # Arduino는 포트 열면 리셋됨
    for c in a.cmd:
        s.write((c + "\n").encode()); time.sleep(0.3)
    for c in a.rig_cmd:
        rig.write((c + "\n").encode()); time.sleep(0.1)
    if any(c.startswith("b") for c in a.cmd):
        time.sleep(2.5)
    s.write(b"?\n"); time.sleep(1.5); s.reset_input_buffer(); s.write(b"?\n")

    lines, buf = [f"# note={a.note.replace(' ', '_')} start={time.strftime('%Y-%m-%dT%H:%M:%S')}"], b""
    t0 = time.time(); synced = [False, False]
    while time.time() - t0 < a.sec:
        if a.sync and rig and not synced[0] and time.time() - t0 > 1.0:
            rig.write(b"y\n"); synced[0] = True
        if a.sync and rig and not synced[1] and time.time() - t0 > a.sec - 1.0:
            rig.write(b"y\n"); synced[1] = True
        buf += s.read(4096)
        *ls, buf = buf.split(b"\n")
        lines += [x.decode(errors="replace").strip() for x in ls if x.strip()]
    with open(a.out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    n = sum(1 for x in lines if x and x[0].isdigit())
    print(f"saved {a.out}: {n} samples ({n / a.sec:.1f} Hz)")
    if rig:
        rig.write(b"P0\n")


if __name__ == "__main__":
    main()
