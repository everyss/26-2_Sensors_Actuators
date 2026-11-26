/*
 * sensor_stm32.ino  —  센서 노드 (STM32 Nucleo-F446RE, Arduino IDE + STM32duino 코어)
 *
 * 역할: 센서 + 실시간 필터 전담
 *   - MPU-6050 을 데이터 준비(INT) 인터럽트로 100 Hz(또는 1 kHz) 정확히 읽음
 *   - 내부 AAF(DLPF) 켬/끔 전환  → 앨리어싱 실험
 *   - 정강이 시상면 각속도에 인과 필터 4종을 실시간 적용
 *       Butterworth 2차(biquad) / 1€ / 칼만(등속 모델) / 선형위상 FIR(고정지연 d)
 *   - Arduino 가 보낸 이벤트 참값 펄스(HS/TO/SYNC)를 같은 시계로 타임스탬프
 *   - 바늘 표시기 서보 2개: RAW / 선택한 필터 출력
 *   - 각 필터 1샘플 처리 시간(us) 측정 → MCU 연산 비용 지표
 *
 * 배선
 *   MPU-6050: VCC 3V3, GND, SCL D15(PB8), SDA D14(PB9), INT D2(PA10), AD0 GND(주소 0x68)
 *   이벤트 입력: D3(PB3) ← Arduino D7 (2.0k/3.3k 분압으로 5V→3.1V)
 *   바늘 서보: RAW D5(PB4), FILTERED D6(PB10)  (서보 전원 외부 5 V, GND 공통)
 *   버튼: D7(PA8) → GND  (바늘 FILTERED 쪽 필터 순환)
 *
 * 출력 (Serial = ST-LINK 가상 COM, 921600 baud). '#'로 시작하는 줄은 메타데이터.
 *   100 Hz 모드: t_us,ax,ay,az,gx,gy,gz,ev,ev_us,w,w_bw,w_1e,w_kf,w_fir,tilt,tilt_f
 *     a*: g, g*: deg/s(바이어스 제거), w: 시상면 각속도, ev: 0/1=HS/2=TO/3=SYNC, ev_us: 이벤트 시각
 *     tilt: 가속도 기반 기울기(deg), tilt_f: 바늘에 표시 중인 필터 출력
 *   1 kHz 모드(r1000): t_us,ax,ay,az,gx,gy,gz,ev,ev_us  (필터 생략, 원신호 특성화용)
 *
 * 직렬 명령 (줄 끝 \n)
 *   a0/a1   내부 AAF(DLPF) 끔/켬          r100 / r1000   출력 속도
 *   b       자이로 바이어스 재측정(2 s 정지) c   필터별 처리 시간 출력
 *   F<Hz>   Butterworth/FIR 차단 주파수     d<n> FIR 고정지연 샘플 수(1..15)
 *   e<min_cut>,<beta>,<d_cut>  1€ 파라미터   q<q>,<r>  칼만 파라미터
 *   n0/n1   바늘 신호: 기울기 / 각속도     k<0..4> 바늘 필터 선택    ?  상태
 */
#include <Wire.h>
#include <Servo.h>

// ------------------------------------------------------------------ 설정
#define MPU_ADDR 0x68
const uint8_t PIN_INT = D2, PIN_EV = D3, PIN_BTN = D7, PIN_NEEDLE_RAW = D5, PIN_NEEDLE_FILT = D6;

// 장착 방향: 보드 X 화살표가 암 끝(아래)을 향하고 부품면이 앞을 보도록 붙였을 때의 기본값
const uint8_t W_AXIS = 2;    // 시상면 각속도 = gz
float W_SIGN = 1.0f;         // 앞으로 스윙할 때 + 가 되도록 (첫 실험에서 확인 후 수정)
float TILT_SIGN = 1.0f;

const float GYRO_LSB = 32.8f;    // ±1000 dps
const float ACC_LSB = 4096.0f;   // ±8 g

// ------------------------------------------------------------------ 필터
struct Biquad {                      // Direct Form II transposed
  float b0, b1, b2, a1, a2, z1 = 0, z2 = 0; bool init = false;
  void design(float fc, float fs) {  // 2차 Butterworth LPF, 쌍선형 변환 + 주파수 사전왜곡
    float K = tanf(PI * fc / fs), Q = 0.70710678f, norm = 1.0f / (1 + K / Q + K * K);
    b0 = K * K * norm; b1 = 2 * b0; b2 = b0;
    a1 = 2 * (K * K - 1) * norm; a2 = (1 - K / Q + K * K) * norm; init = false;
  }
  float step(float x) {
    if (!init) { z1 = x * (1 - b0); z2 = x * (b2 - a2); init = true; }   // 정상상태 초기화
    float y = b0 * x + z1; z1 = b1 * x - a1 * y + z2; z2 = b2 * x - a2 * y; return y;
  }
};

struct OneEuro {                     // Casiez et al., CHI 2012
  float minCut = 8, beta = 0.01f, dCut = 10, fs = 100;
  float xPrev = 0, xh = 0, dxh = 0; bool init = false;
  float alpha(float fc) { return 1.0f / (1.0f + fs / (2 * PI * fc)); }
  float step(float x) {
    if (!init) { xPrev = xh = x; dxh = 0; init = true; }
    dxh += alpha(dCut) * ((x - xPrev) * fs - dxh);
    xh += alpha(minCut + beta * fabsf(dxh)) * (x - xh);
    xPrev = x; return xh;
  }
};

struct KalmanCV {                    // 상태 [w, dw], 측정 w
  float q = 376000, r = 1, T = 0.01f;   // q/r: RTS(사후)의 -3 dB가 10 Hz가 되는 값 (tools/filters.py kalman_q_for_cutoff)
  float x0 = 0, x1 = 0, P00 = 1, P01 = 0, P11 = 1e4f; bool init = false;
  float step(float z) {
    if (!init) { x0 = z; x1 = 0; P00 = 0.5f * r; P01 = 0; P11 = 1e4f; init = true; return x0; }  // PC 구현과 동일한 첫 갱신 결과
    // 예측
    x0 += T * x1;
    float p00 = P00 + T * (2 * P01 + T * P11) + q * T * T * T / 3;
    float p01 = P01 + T * P11 + q * T * T / 2;
    float p11 = P11 + q * T;
    // 갱신
    float s = p00 + r, k0 = p00 / s, k1 = p01 / s, e = z - x0;
    x0 += k0 * e; x1 += k1 * e;
    P00 = (1 - k0) * p00; P01 = (1 - k0) * p01; P11 = p11 - k1 * p01;
    return x0;
  }
};

const int FIR_MAXD = 15;
struct FirLag {                      // 선형위상(Hamming 창 sinc), 길이 2d+1, 지연 정확히 d 샘플
  float h[2 * FIR_MAXD + 1], buf[2 * FIR_MAXD + 1]; int d = 5, n = 11, idx = 0; bool init = false;
  void design(float fc, float fs, int d_) {
    d = constrain(d_, 1, FIR_MAXD); n = 2 * d + 1; float sum = 0;
    for (int i = 0; i < n; i++) {
      float m = i - d, wc = 2 * fc / fs;
      float s = (m == 0) ? wc : sinf(PI * wc * m) / (PI * m);
      float w = 0.54f - 0.46f * cosf(2 * PI * i / (n - 1));
      h[i] = s * w; sum += h[i];
    }
    for (int i = 0; i < n; i++) h[i] /= sum;
    init = false;
  }
  float step(float x) {
    if (!init) { for (int i = 0; i < n; i++) buf[i] = x; idx = 0; init = true; }
    buf[idx] = x; float y = 0; int j = idx;
    for (int i = 0; i < n; i++) { y += h[i] * buf[j]; j = (j == 0) ? n - 1 : j - 1; }
    idx = (idx + 1) % n; return y;
  }
};

// 각속도용
Biquad bwW; OneEuro euW; KalmanCV kfW; FirLag firW;
// 기울기(바늘)용
Biquad bwT, bwT3; OneEuro euT; KalmanCV kfT; FirLag firT;

float fcHz = 10, fs = 100; int firD = 5;
uint8_t needleFilter = 0;  // 0 BW10, 1 BW3(강한 필터), 2 1€, 3 KF, 4 FIR
const char* NEEDLE_NAMES[] = {"Butterworth fc", "Butterworth 3Hz", "1-Euro", "Kalman", "FIR fixed-lag"};
bool needleGyro = false;
uint32_t costUs[5] = {0}; uint32_t costN = 0;

// ------------------------------------------------------------------ 상태
volatile bool dataReady = false; volatile uint32_t drUs = 0;
volatile uint32_t evRise = 0; volatile uint8_t evCode = 0; volatile uint32_t evUs = 0;
bool aafOn = true; int rateHz = 100;
float gBias[3] = {0, 0, 0};
Servo needleRaw, needleFilt;

void isrDR() { drUs = micros(); dataReady = true; }
void isrEV() {
  uint32_t t = micros();
  if (digitalRead(PIN_EV)) evRise = t;
  else {
    uint32_t w = t - evRise;
    evCode = (w < 6000) ? 1 : (w < 18000) ? 2 : 3;   // 3 ms HS / 9 ms TO / 30 ms SYNC
    evUs = evRise;
  }
}

void mpuWrite(uint8_t reg, uint8_t v) { Wire.beginTransmission(MPU_ADDR); Wire.write(reg); Wire.write(v); Wire.endTransmission(); }
uint8_t mpuRead(uint8_t reg) {
  Wire.beginTransmission(MPU_ADDR); Wire.write(reg); Wire.endTransmission(false);
  Wire.requestFrom((uint8_t)MPU_ADDR, (uint8_t)1); return Wire.read();
}

void mpuConfig() {
  // DLPF_CFG=3: 자이로 42 Hz / 가속도 44 Hz, 내부 1 kHz  |  DLPF_CFG=0: 자이로 256 Hz, 내부 8 kHz(가속도 1 kHz)
  uint8_t dlpf = aafOn ? 3 : 0;
  uint16_t base = aafOn ? 1000 : 8000;
  uint8_t div = (uint8_t)(base / rateHz - 1);
  mpuWrite(0x6B, 0x01);        // PWR_MGMT_1: 깨우기, 클록 = 자이로 X PLL
  mpuWrite(0x1A, dlpf);        // CONFIG
  mpuWrite(0x19, div);         // SMPLRT_DIV
  mpuWrite(0x1B, 0x10);        // GYRO_CONFIG ±1000 dps
  mpuWrite(0x1C, 0x10);        // ACCEL_CONFIG ±8 g
  mpuWrite(0x37, 0x10);        // INT_PIN_CFG: 아무 레지스터 읽으면 INT 해제, 액티브 하이, 50 us 펄스
  mpuWrite(0x38, 0x01);        // INT_ENABLE: DATA_RDY
  fs = rateHz;
}

bool readMPU(float a[3], float g[3]) {
  Wire.beginTransmission(MPU_ADDR); Wire.write(0x3B);
  if (Wire.endTransmission(false) != 0) return false;
  if (Wire.requestFrom((uint8_t)MPU_ADDR, (uint8_t)14) != 14) return false;
  int16_t v[7];
  for (int i = 0; i < 7; i++) v[i] = (Wire.read() << 8) | Wire.read();
  for (int i = 0; i < 3; i++) { a[i] = v[i] / ACC_LSB; g[i] = v[i + 4] / GYRO_LSB - gBias[i]; }
  return true;
}

void designFilters() {
  bwW.design(fcHz, fs); bwT.design(fcHz, fs); bwT3.design(3, fs);
  euW.fs = euT.fs = fs; euW.init = euT.init = false;
  kfW.T = kfT.T = 1.0f / fs; kfW.init = kfT.init = false;
  firW.design(fcHz, fs, firD); firT.design(fcHz, fs, firD);
  memset(costUs, 0, sizeof(costUs)); costN = 0;
}

void calibrateBias() {
  Serial.println("# bias: 2 s 동안 움직이지 마세요");
  double s[3] = {0, 0, 0}; int n = 0; uint32_t t0 = millis();
  float a[3], g[3]; float old[3]; memcpy(old, gBias, sizeof(old)); memset(gBias, 0, sizeof(gBias));
  while (millis() - t0 < 2000) {
    if (dataReady) { dataReady = false; if (readMPU(a, g)) { for (int i = 0; i < 3; i++) s[i] += g[i]; n++; } }
  }
  for (int i = 0; i < 3; i++) gBias[i] = n ? s[i] / n : old[i];
  Serial.print("# bias_dps="); Serial.print(gBias[0], 3); Serial.print(','); Serial.print(gBias[1], 3); Serial.print(','); Serial.println(gBias[2], 3);
}

void header() {
  Serial.print("# fs="); Serial.print(rateHz); Serial.print(" aaf="); Serial.print(aafOn);
  Serial.print(" fc="); Serial.print(fcHz); Serial.print(" fir_d="); Serial.print(firD);
  Serial.print(" euro="); Serial.print(euW.minCut); Serial.print(','); Serial.print(euW.beta, 4); Serial.print(','); Serial.print(euW.dCut);
  Serial.print(" kf_q="); Serial.print(kfW.q); Serial.print(" kf_r="); Serial.print(kfW.r);
  Serial.print(" needle="); Serial.print(NEEDLE_NAMES[needleFilter]); Serial.print(needleGyro ? " (gyro)" : " (tilt)");
  Serial.print(" w_axis="); Serial.print(W_AXIS); Serial.print(" w_sign="); Serial.println(W_SIGN);
  if (rateHz <= 200) Serial.println("t_us,ax,ay,az,gx,gy,gz,ev,ev_us,w,w_bw,w_1e,w_kf,w_fir,tilt,tilt_f");
  else Serial.println("t_us,ax,ay,az,gx,gy,gz,ev,ev_us");
}

void handleSerial() {
  static char buf[40]; static uint8_t n = 0;
  while (Serial.available()) {
    char ch = Serial.read();
    if (ch == '\r') continue;
    if (ch != '\n' && n < sizeof(buf) - 1) { buf[n++] = ch; continue; }
    buf[n] = 0; n = 0; if (!buf[0]) continue;
    float v = atof(buf + 1);
    switch (buf[0]) {
      case 'a': aafOn = v > 0.5f; mpuConfig(); designFilters(); break;
      case 'r': rateHz = (v >= 500) ? 1000 : 100; mpuConfig(); designFilters(); break;
      case 'b': calibrateBias(); break;
      case 'F': fcHz = constrain(v, 0.5f, 40.0f); designFilters(); break;
      case 'd': firD = (int)v; designFilters(); break;
      case 'e': { float m, b, d; if (sscanf(buf + 1, "%f,%f,%f", &m, &b, &d) == 3) { euW.minCut = euT.minCut = m; euW.beta = euT.beta = b; euW.dCut = euT.dCut = d; } designFilters(); break; }
      case 'q': { float q, r; if (sscanf(buf + 1, "%f,%f", &q, &r) == 2) { kfW.q = kfT.q = q; kfW.r = kfT.r = r; } designFilters(); break; }
      case 'n': needleGyro = v > 0.5f; break;
      case 'k': needleFilter = ((int)v) % 5; break;
      case 'c': {
        Serial.print("# cost_us_per_sample (BW,1E,KF,FIR,read) n="); Serial.print(costN); Serial.print(" : ");
        for (int i = 0; i < 5; i++) { Serial.print(costN ? (float)costUs[i] / costN : 0, 2); Serial.print(i < 4 ? ',' : '\n'); }
        break; }
      case '?': break;
      default: Serial.println("# ?cmd"); break;
    }
    header();
  }
}

void handleButton() {
  static bool last = HIGH; static uint32_t tc = 0;
  bool b = digitalRead(PIN_BTN);
  if (b != last && millis() - tc > 40) { tc = millis(); last = b; if (b == LOW) { needleFilter = (needleFilter + 1) % 5; header(); } }
}

// 바늘: ±60° 범위. 기울기는 그대로, 각속도는 ±300 dps → ±60°
void writeNeedle(Servo& s, float deg) { s.writeMicroseconds(1500 + (int)(constrain(deg, -60, 60) * 10.3f)); }

void setup() {
  Serial.begin(921600);
  Wire.begin(); Wire.setClock(400000);
  pinMode(PIN_INT, INPUT); pinMode(PIN_EV, INPUT); pinMode(PIN_BTN, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(PIN_INT), isrDR, RISING);
  attachInterrupt(digitalPinToInterrupt(PIN_EV), isrEV, CHANGE);
  needleRaw.attach(PIN_NEEDLE_RAW); needleFilt.attach(PIN_NEEDLE_FILT);
  delay(100);
  uint8_t who = mpuRead(0x75);
  Serial.print("# WHO_AM_I=0x"); Serial.println(who, HEX);   // 0x68 이어야 정상
  mpuConfig(); designFilters();
  calibrateBias();
  header();
}

void loop() {
  handleSerial(); handleButton();
  if (!dataReady) return;
  noInterrupts(); uint32_t t = drUs; dataReady = false; uint8_t ev = evCode; uint32_t evt = evUs; evCode = 0; interrupts();

  float a[3], g[3];
  uint32_t c0 = micros();
  if (!readMPU(a, g)) { Serial.println("# i2c error"); return; }
  uint32_t c1 = micros();

  Serial.print(t); Serial.print(',');
  for (int i = 0; i < 3; i++) { Serial.print(a[i], 4); Serial.print(','); }
  for (int i = 0; i < 3; i++) { Serial.print(g[i], 2); Serial.print(','); }
  Serial.print(ev); Serial.print(','); Serial.print(ev ? evt : 0);
  if (rateHz > 200) { Serial.println(); return; }

  float w = W_SIGN * g[W_AXIS];
  uint32_t k0 = micros(); float yb = bwW.step(w);
  uint32_t k1 = micros(); float ye = euW.step(w);
  uint32_t k2 = micros(); float yk = kfW.step(w);
  uint32_t k3 = micros(); float yf = firW.step(w);
  uint32_t k4 = micros();
  costUs[0] += k1 - k0; costUs[1] += k2 - k1; costUs[2] += k3 - k2; costUs[3] += k4 - k3; costUs[4] += c1 - c0; costN++;

  // 기울기: 보드 X가 아래(암 끝)를 향할 때 정지 상태 0°
  float tilt = TILT_SIGN * atan2f(a[1], -a[0]) * 180.0f / PI;
  float tb = bwT.step(tilt), tb3 = bwT3.step(tilt), te = euT.step(tilt), tk = kfT.step(tilt), tf = firT.step(tilt);
  float sel[5] = {tb, tb3, te, tk, tf};
  float tiltF = sel[needleFilter];

  Serial.print(','); Serial.print(w, 2); Serial.print(','); Serial.print(yb, 2); Serial.print(',');
  Serial.print(ye, 2); Serial.print(','); Serial.print(yk, 2); Serial.print(','); Serial.print(yf, 2); Serial.print(',');
  Serial.print(tilt, 2); Serial.print(','); Serial.println(tiltF, 2);

  // 바늘 (50 Hz로 충분 — 서보 프레임 20 ms)
  static uint8_t div = 0;
  if (++div >= 2) {
    div = 0;
    if (needleGyro) {
      float wsel[5] = {yb, yb, ye, yk, yf};
      writeNeedle(needleRaw, w * 0.2f); writeNeedle(needleFilt, wsel[needleFilter] * 0.2f);
    } else {
      writeNeedle(needleRaw, tilt); writeNeedle(needleFilt, tiltF);
    }
  }
}
