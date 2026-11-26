"""100 fps 영상에서 참값 만들기.

1) 동기 LED 자동 검출 (SYNC):
   python video_events.py led  video.mp4 --roi 100,200,30,30 --out events.csv
   (--roi 없이 실행하면 첫 프레임에서 마우스로 LED 영역을 고름)
2) HS / TO 수동 주석 (프레임 단위):
   python video_events.py annotate video.mp4 --out events.csv
   키:  d/a 다음/이전 프레임   D/A ±10 프레임   h HS   t TO   s SYNC   u 되돌리기   q 저장 후 종료
   이미 있는 events.csv에 이어서 기록한다 (led 결과와 합쳐짐).

출력 CSV:  '# fps=100' 다음 'frame,type' — analyze.py gait --video 로 바로 사용
"""
import argparse
import os
import cv2
import numpy as np


def load_rows(path):
    rows = []
    if os.path.exists(path):
        for line in open(path):
            line = line.strip()
            if line and not line.startswith("#") and not line.startswith("frame"):
                f, t = line.split(",")[:2]
                rows.append((int(f), t.strip().upper()))
    return rows


def save_rows(path, rows, fps):
    rows = sorted(set(rows))
    with open(path, "w") as f:
        f.write(f"# fps={fps:g}\nframe,type\n")
        for fr, t in rows:
            f.write(f"{fr},{t}\n")
    print(f"saved {path}: " + ", ".join(f"{t} {sum(1 for _, x in rows if x == t)}" for t in ("SYNC", "HS", "TO")))


def cmd_led(a):
    cap = cv2.VideoCapture(a.video)
    fps = a.fps or cap.get(cv2.CAP_PROP_FPS)
    ok, frame = cap.read()
    if not ok:
        raise SystemExit("영상을 열 수 없습니다")
    if a.roi:
        x, y, w, h = map(int, a.roi.split(","))
    else:
        x, y, w, h = cv2.selectROI("LED 영역 선택 후 Enter", frame); cv2.destroyAllWindows()
    vals = []
    while ok:
        vals.append(float(cv2.cvtColor(frame[y:y + h, x:x + w], cv2.COLOR_BGR2GRAY).mean()))
        ok, frame = cap.read()
    v = np.array(vals)
    thr = a.thr if a.thr else (np.percentile(v, 5) + np.percentile(v, 99.9)) / 2
    on = v > thr
    rising = np.where(on[1:] & ~on[:-1])[0] + 1
    # HS 때마다 짧게 켜지는 LED(40 ms)와 SYNC(30 ms 펄스 + LED 40 ms)는 같은 LED → 명령으로 구분하려면
    # 리그의 HS LED를 끄거나, 사람 실험처럼 SYNC만 쓰는 경우에 사용
    rows = [(int(r), "SYNC") for r in rising]
    print(f"fps={fps:g}, 프레임 {len(v)}개, 임계값 {thr:.1f}, LED 켜짐 {len(rising)}회: {rising[:10]}")
    save_rows(a.out, load_rows(a.out) + rows, fps)


def cmd_annotate(a):
    cap = cv2.VideoCapture(a.video)
    fps = a.fps or cap.get(cv2.CAP_PROP_FPS)
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    rows = load_rows(a.out); i = 0; cache = {}

    def get(k):
        if k not in cache:
            cap.set(cv2.CAP_PROP_POS_FRAMES, k); ok, fr = cap.read()
            cache[k] = fr if ok else np.zeros((480, 640, 3), np.uint8)
            if len(cache) > 300:
                cache.pop(next(iter(cache)))
        return cache[k].copy()

    while True:
        img = get(i)
        marks = [t for f, t in rows if f == i]
        cv2.putText(img, f"frame {i}/{n - 1}  t={i / fps:.2f}s  {' '.join(marks)}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
        cv2.imshow("annotate (d/a, D/A, h, t, s, u, q)", img)
        k = cv2.waitKey(0) & 0xFF
        if k == ord("q"):
            break
        step = {ord("d"): 1, ord("a"): -1, ord("D"): 10, ord("A"): -10}.get(k)
        if step:
            i = int(np.clip(i + step, 0, n - 1))
        elif k in (ord("h"), ord("t"), ord("s")):
            rows.append((i, {ord("h"): "HS", ord("t"): "TO", ord("s"): "SYNC"}[k]))
        elif k == ord("u") and rows:
            rows.pop()
    cv2.destroyAllWindows()
    save_rows(a.out, rows, fps)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("mode", choices=["led", "annotate"]); p.add_argument("video")
    p.add_argument("--out", required=True); p.add_argument("--fps", type=float, default=0)
    p.add_argument("--roi"); p.add_argument("--thr", type=float, default=0)
    a = p.parse_args()
    cmd_led(a) if a.mode == "led" else cmd_annotate(a)


if __name__ == "__main__":
    main()
