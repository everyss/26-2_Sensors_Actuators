- 파일 2개, 참값 HS 47개, fc = 10.0 Hz, 칼만 q = 376177 (R = 1.0)
- 참값: Arduino 명령 펄스(서보 지연 포함 → 실효 지연은 사후 대비 차이로 봄)
- 사후 수준 판정: HS 지터 ≤ 사후 지터 × 1.10 + 1 ms, 그리고 파형 RMSE(사후 기준 대비) ≤ 원신호 RMSE × 0.30  (= 원신호가 사후 결과와 다른 정도를 70% 이상 줄임)
- 실효 지연은 사후(영위상) 대비 값이라 음수가 될 수 있음 (충격 파형을 덜 평활하면 극소가 더 일찍 잡힘)
- 참값 치우침(사후 기준 대비 중앙값, 제거 후 비교) HS / TO (ms): E3_gait_impact.csv +228 / +11; E3_gait_noimpact.csv +0 / +10

| 계열 | 시점 | 설정 | 실효 지연 (ms) | HS 지터 SD (ms) | TO 오차 평균±SD (ms) | 파형 지연 D (ms) | 파형 RMSE (deg/s) | 사후 수준 |
|---|---|---|---:|---:|---:|---:|---:|:---:|
| raw | raw | raw | -13.5 | 1.0 | +10.9 ± 1.0 | 0.0 | 3.19 |  |
| Butterworth | causal | BW causal fc=10 | +23.5 | 0.6 | +23.2 ± 0.4 | 21.6 | 1.86 |  |
| Butterworth | fixed-lag | FIR fixed-lag d=1 | -2.8 | 0.8 | +19.8 ± 0.9 | 10.0 | 2.73 |  |
| Butterworth | fixed-lag | FIR fixed-lag d=2 | +11.6 | 0.7 | +25.1 ± 0.5 | 20.0 | 1.41 |  |
| Butterworth | fixed-lag | FIR fixed-lag d=3 | +24.7 | 0.5 | +31.0 ± 0.5 | 30.0 | 0.92 | O |
| Butterworth | fixed-lag | FIR fixed-lag d=5 | +50.4 | 0.6 | +45.0 ± 0.4 | 50.0 | 1.31 |  |
| Butterworth | fixed-lag | FIR fixed-lag d=8 | +84.9 | 0.4 | +73.2 ± 0.3 | 80.0 | 1.51 |  |
| Butterworth | fixed-lag | FIR fixed-lag d=10 | +106.4 | 0.4 | +94.2 ± 0.3 | 100.0 | 1.22 |  |
| Butterworth | fixed-lag | FIR fixed-lag d=15 | +157.9 | 0.5 | +146.2 ± 0.2 | 150.0 | 1.01 |  |
| Butterworth | offline | BW zero-phase | +0.0 | 0.6 | +0.1 ± 0.3 | 0.0 | 0.00 | O |
| 1euro | causal | 1€ causal | -5.2 | 1.0 | +14.8 ± 0.6 | 7.6 | 3.74 |  |
| 1euro | fixed-lag | 1€ fwd-bwd lag d=1 | -1.8 | 0.8 | +15.5 ± 0.5 | 10.7 | 2.57 |  |
| 1euro | fixed-lag | 1€ fwd-bwd lag d=2 | +8.6 | 0.8 | +18.4 ± 0.3 | 20.1 | 2.32 |  |
| 1euro | fixed-lag | 1€ fwd-bwd lag d=3 | +18.7 | 0.8 | +22.2 ± 0.4 | 30.0 | 2.33 |  |
| 1euro | fixed-lag | 1€ fwd-bwd lag d=5 | +38.7 | 0.8 | +49.7 ± 0.7 | 50.0 | 2.36 |  |
| 1euro | fixed-lag | 1€ fwd-bwd lag d=8 | +68.7 | 0.8 | +80.8 ± 0.5 | 80.0 | 2.33 |  |
| 1euro | fixed-lag | 1€ fwd-bwd lag d=10 | +88.7 | 0.8 | +100.7 ± 0.5 | 100.0 | 2.33 |  |
| 1euro | fixed-lag | 1€ fwd-bwd lag d=15 | +138.7 | 0.8 | +150.7 ± 0.5 | 150.0 | 2.32 |  |
| 1euro | offline | 1€ fwd-bwd | -11.3 | 0.8 | +0.7 ± 0.5 | 0.0 | 2.33 |  |
| Kalman | causal | KF | -5.1 | 0.5 | +12.3 ± 0.8 | 0.0 | 3.11 |  |
| Kalman | fixed-lag | KF fixed-lag d=1 | +7.2 | 0.2 | +15.2 ± 0.6 | 10.2 | 1.06 |  |
| Kalman | fixed-lag | KF fixed-lag d=2 | +19.6 | 0.5 | +21.0 ± 0.5 | 20.2 | 0.64 | O |
| Kalman | fixed-lag | KF fixed-lag d=3 | +29.6 | 0.5 | +31.2 ± 0.4 | 30.2 | 0.63 | O |
| Kalman | fixed-lag | KF fixed-lag d=5 | +49.2 | 0.5 | +50.8 ± 0.3 | 50.1 | 0.24 | O |
| Kalman | fixed-lag | KF fixed-lag d=8 | +79.3 | 0.5 | +79.8 ± 0.3 | 80.0 | 0.13 | O |
| Kalman | fixed-lag | KF fixed-lag d=10 | +99.3 | 0.5 | +99.8 ± 0.3 | 100.0 | 0.12 | O |
| Kalman | fixed-lag | KF fixed-lag d=15 | +149.3 | 0.5 | +149.8 ± 0.3 | 150.0 | 0.12 | O |
| Kalman | offline | RTS | -0.7 | 0.5 | -0.2 ± 0.3 | 0.0 | 0.12 | O |

## 최소 지연 d* (계열별, 실시간 중 '사후 수준'을 처음 만족하는 설정)

- Butterworth: **24.7 ms** (FIR fixed-lag d=3)
- 1euro: 조건 만족 설정 없음
- Kalman: **19.6 ms** (KF fixed-lag d=2)

## 통계 (보폭별 HS 시점 오차, 같은 보폭끼리 대응)

- Friedman χ² = 228.4, p = 2.3e-47 (보폭 47개, 조건 6개)
- BW causal fc=10 vs 사후: Wilcoxon p = 1.4e-14, Holm 보정 p = 7.1e-14
- 1€ causal vs 사후: Wilcoxon p = 1.4e-14, Holm 보정 p = 5.7e-14
- KF vs 사후: Wilcoxon p = 1.4e-14, Holm 보정 p = 4.3e-14
- FIR fixed-lag d=3 vs 사후: Wilcoxon p = 1.4e-14, Holm 보정 p = 2.8e-14
- KF fixed-lag d=2 vs 사후: Wilcoxon p = 1.4e-14, Holm 보정 p = 1.4e-14
