- 파일 1개, 참값 HS 47개, fc = 10.0 Hz, 칼만 q = 376177 (R = 1.0)
- 참값: 영상 주석(SYNC 정렬)
- 사후 수준 판정: HS 지터 ≤ 사후 지터 × 1.10 + 1 ms, 그리고 파형 RMSE(사후 기준 대비) ≤ 원신호 RMSE × 0.30  (= 원신호가 사후 결과와 다른 정도를 70% 이상 줄임)
- 실효 지연은 사후(영위상) 대비 값이라 음수가 될 수 있음 (충격 파형을 덜 평활하면 극소가 더 일찍 잡힘)
- 참값 치우침(사후 기준 대비 중앙값, 제거 후 비교) HS / TO (ms): E3_gait_impact.csv +174 / -66

| 계열 | 시점 | 설정 | 실효 지연 (ms) | HS 지터 SD (ms) | TO 오차 평균±SD (ms) | 파형 지연 D (ms) | 파형 RMSE (deg/s) | 사후 수준 |
|---|---|---|---:|---:|---:|---:|---:|:---:|
| raw | raw | raw | -13.5 | 3.0 | +10.5 ± 3.2 | 0.0 | 5.75 |  |
| Butterworth | causal | BW causal fc=10 | +23.5 | 3.3 | +22.8 ± 2.6 | 21.9 | 2.36 |  |
| Butterworth | fixed-lag | FIR fixed-lag d=1 | -2.8 | 2.6 | +19.4 ± 3.4 | 10.0 | 4.90 |  |
| Butterworth | fixed-lag | FIR fixed-lag d=2 | +11.6 | 3.4 | +24.7 ± 2.6 | 20.0 | 2.44 |  |
| Butterworth | fixed-lag | FIR fixed-lag d=3 | +24.7 | 3.3 | +30.6 ± 3.0 | 30.0 | 1.37 | O |
| Butterworth | fixed-lag | FIR fixed-lag d=5 | +50.4 | 3.2 | +44.6 ± 2.7 | 50.0 | 1.66 | O |
| Butterworth | fixed-lag | FIR fixed-lag d=8 | +84.9 | 3.2 | +72.8 ± 2.7 | 80.0 | 2.06 |  |
| Butterworth | fixed-lag | FIR fixed-lag d=10 | +106.4 | 3.0 | +93.9 ± 2.7 | 100.0 | 1.81 |  |
| Butterworth | fixed-lag | FIR fixed-lag d=15 | +157.9 | 3.1 | +145.9 ± 2.9 | 150.0 | 1.66 | O |
| Butterworth | offline | BW zero-phase | +0.0 | 3.1 | -0.2 ± 3.0 | 0.0 | 0.00 | O |
| 1euro | causal | 1€ causal | -5.2 | 3.6 | +14.5 ± 2.5 | 6.2 | 5.72 |  |
| 1euro | fixed-lag | 1€ fwd-bwd lag d=1 | -1.8 | 2.3 | +15.1 ± 2.7 | 10.6 | 4.00 |  |
| 1euro | fixed-lag | 1€ fwd-bwd lag d=2 | +8.6 | 2.3 | +18.0 ± 2.9 | 20.1 | 3.91 |  |
| 1euro | fixed-lag | 1€ fwd-bwd lag d=3 | +18.7 | 2.3 | +21.9 ± 3.1 | 30.0 | 3.90 |  |
| 1euro | fixed-lag | 1€ fwd-bwd lag d=5 | +38.7 | 2.3 | +49.3 ± 3.1 | 50.1 | 3.92 |  |
| 1euro | fixed-lag | 1€ fwd-bwd lag d=8 | +68.7 | 2.3 | +80.4 ± 2.9 | 80.1 | 3.89 |  |
| 1euro | fixed-lag | 1€ fwd-bwd lag d=10 | +88.7 | 2.3 | +100.3 ± 2.9 | 100.1 | 3.88 |  |
| 1euro | fixed-lag | 1€ fwd-bwd lag d=15 | +138.7 | 2.3 | +150.3 ± 2.9 | 150.1 | 3.88 |  |
| 1euro | offline | 1€ fwd-bwd | -11.3 | 2.3 | +0.3 ± 2.9 | 0.0 | 3.90 |  |
| Kalman | causal | KF | -5.1 | 3.3 | +11.9 ± 2.7 | 0.0 | 4.97 |  |
| Kalman | fixed-lag | KF fixed-lag d=1 | +7.2 | 2.9 | +14.8 ± 2.6 | 10.3 | 1.78 |  |
| Kalman | fixed-lag | KF fixed-lag d=2 | +19.6 | 3.1 | +20.6 ± 3.0 | 20.3 | 0.93 | O |
| Kalman | fixed-lag | KF fixed-lag d=3 | +29.6 | 3.1 | +30.9 ± 2.9 | 30.3 | 0.92 | O |
| Kalman | fixed-lag | KF fixed-lag d=5 | +49.2 | 3.0 | +50.5 ± 3.0 | 50.1 | 0.38 | O |
| Kalman | fixed-lag | KF fixed-lag d=8 | +79.3 | 3.1 | +79.4 ± 3.1 | 80.0 | 0.20 | O |
| Kalman | fixed-lag | KF fixed-lag d=10 | +99.3 | 3.1 | +99.4 ± 3.1 | 100.0 | 0.19 | O |
| Kalman | fixed-lag | KF fixed-lag d=15 | +149.3 | 3.1 | +149.4 ± 3.1 | 150.0 | 0.19 | O |
| Kalman | offline | RTS | -0.7 | 3.1 | -0.6 ± 3.1 | 0.0 | 0.19 | O |

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
