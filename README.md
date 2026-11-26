# 26-2 센서 및 액추에이터: 기말 프로젝트

**주제**: IMU 신호에 고정지연 필터를 적용한 저지연 보행 이벤트 검출 (실시간 · 고정지연 · 사후 필터의 정확도–지연 비교)

## 최종 프로젝트 (1주 실행)

| 경로 | 내용 |
|---|---|
| [`docs/03_final_week_plan.md`](docs/03_final_week_plan.md) | **1주 실행 계획**: D1–D7 시간표, 실험 E1–E5 설계, 지표 정의, 발표 구성, 라이브 데모 시나리오, 위험 관리 |
| [`docs/lab_notebook.md`](docs/lab_notebook.md) | 실험 노트 양식 (보정값, 실험 기록) |
| [`hardware/`](hardware/README.md) | 정강이 모사 벤치 리그 + 바늘 표시기: OpenSCAD 원본, STL, BOM, 조립, 배선, 보정 |
| [`firmware/rig_arduino/`](firmware/rig_arduino/rig_arduino.ino) | Arduino Uno: 서보 보행 패턴, 진동모터, HS/TO/SYNC 참값 펄스, 동기 LED |
| [`firmware/sensor_stm32/`](firmware/sensor_stm32/sensor_stm32.ino) | STM32 Nucleo-F446RE: MPU-6050(AAF 켬/끔), 실시간 필터 4종, 이벤트 타임스탬프, 바늘 서보 |
| [`tools/`](tools/) | `log_serial.py` 기록 · `live_view.py` 실시간 화면 · `analyze.py` 분석 · `video_events.py` 영상 참값 · `bench_sim.py` 가상 데이터 · `filters.py` 기준 구현 |
| [`results/sim/`](results/sim/README.md) | 가상 데이터로 돌려 본 리허설 출력 (실제 결과 아님) |

```bash
pip install numpy scipy matplotlib pyserial pyqtgraph PyQt5 opencv-python
cd tools
python live_view.py --port COM5 --rig-port COM6       # 장비 연결 시
python bench_sim.py --exp gait --impact 1 --out ../data/sim/E3.csv && python live_view.py --replay ../data/sim/E3.csv   # 장비 없이
```

## 중간발표

| 경로 | 내용 |
|---|---|
| [`docs/01_midterm_plan.md`](docs/01_midterm_plan.md) | 연구 계획서: 아이디어 변경 이유, 가설, 필터 식, 하드웨어, 실험 설계, 지표, 일정, 위험 요소 |
| [`docs/02_midterm_script_5min.md`](docs/02_midterm_script_5min.md) | 중간발표(재발표) 5분 대본: 슬라이드 8장 + 시간 배분, 예상 질문 |
| [`slides/midterm_presentation.pptx`](slides/midterm_presentation.pptx) | 중간발표 PowerPoint (8장, 발표자 노트 포함) |
| [`sim/prelim_sim.py`](sim/prelim_sim.py) | 예비 시뮬레이션 (합성 보행 신호에서 사전·고정지연·사후 비교) |
| [`sim/results_table.md`](sim/results_table.md) | 예비 시뮬레이션 결과 표 |
