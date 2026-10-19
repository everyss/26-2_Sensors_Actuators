# 26-2 센서 및 액추에이터: 기말 프로젝트

**주제**: 하지 착용형 IMU 신호의 사전(실시간)·사후(오프라인) 필터링 비교, 정확도–지연 트레이드오프 분석

| 경로 | 내용 |
|---|---|
| [`docs/01_midterm_plan.md`](docs/01_midterm_plan.md) | 아이디어 평가, 발전시킨 연구 설계, 중간발표 원고(연구 배경 / 주제 선정 이유 / 연구 진행 방법), 슬라이드 구성안, 예상 질문 |
| [`sim/prelim_sim.py`](sim/prelim_sim.py) | 예비 시뮬레이션 (합성 보행 신호, MAF / LPF / KF의 사전형·사후형 비교, 앨리어싱) |
| [`sim/results_table.md`](sim/results_table.md) | 시뮬레이션 결과 표 |
| [`sim/figures/`](sim/figures/) | 발표용 그림 |

```bash
pip install numpy scipy matplotlib
python3 sim/prelim_sim.py
```
