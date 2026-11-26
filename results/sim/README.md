# 가상 데이터 리허설 결과 (실제 실험 결과 아님)

`tools/bench_sim.py`가 만든 **가상 벤치 데이터**로 분석 파이프라인 전체가 돌아가는지 확인한 출력이다.
발표 자료에 넣지 않는다. 실제 실험 결과는 `results/E1` … `results/E4`에 새로 생성된다.

| 폴더 | 명령 | 확인한 것 |
|---|---|---|
| `E1/` | `analyze.py static` | 정지 잡음 표, PSD, 칼만 R 추천 |
| `E2/` | `analyze.py vib` | AAF 끔에서 203 Hz 진동이 3 Hz로 접힘, 필터로 안 줄어듦 (`shake_bar.png`) |
| `E3/` | `analyze.py gait` (명령 펄스 참값) | 지연-정확도 곡선, d*, 한 보폭 비교, Friedman/Wilcoxon |
| `E4test/` | `analyze.py gait --video` | 영상 주석 CSV + SYNC 정렬 경로 |
| `live_view_replay.png` | `live_view.py --replay` | 데모 화면 구성 |
