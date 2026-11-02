# 26-2 센서 및 액추에이터: 기말 프로젝트

**주제**: MPU-6050 자이로 신호에 고정지연 필터를 적용한 저지연 보행 이벤트 검출 (실시간 · 고정지연 · 사후 필터의 정확도–지연 비교)

| 경로 | 내용 |
|---|---|
| [`docs/01_midterm_plan.md`](docs/01_midterm_plan.md) | 연구 계획서 최종안: 아이디어 변경 이유, 가설, 필터 식, 하드웨어(STM32 / Arduino), 실험 설계, 지표, 일정, 위험 요소 |
| [`docs/02_midterm_script_5min.md`](docs/02_midterm_script_5min.md) | 중간발표(재발표) 5분 대본: 슬라이드 7장 + 시간 배분, 예상 질문 |
| [`slides/midterm_presentation.pptx`](slides/midterm_presentation.pptx) | 중간발표 PowerPoint (7장, 발표자 노트 포함) |
| [`sim/prelim_sim.py`](sim/prelim_sim.py) | 예비 시뮬레이션 (합성 보행 신호. Butterworth / 1€ / 칼만 계열의 사전·고정지연·사후 비교, 앨리어싱, 학습형 필터 검토) |
| [`sim/results_table.md`](sim/results_table.md) | 시뮬레이션 결과 표 |
| [`sim/figures/`](sim/figures/) | 발표용 그림 (`fig1_waveform`, `fig2_aliasing_psd`, `fig3_latency_budget`) |

```bash
pip install numpy scipy matplotlib scikit-learn
python3 sim/prelim_sim.py
```
