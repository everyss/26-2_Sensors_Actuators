/*
 * rig_arduino.ino  —  벤치 리그 구동기 (Arduino Uno)
 *
 * 역할: 액추에이터 쪽 전담
 *   - 표준 서보로 정강이 모사 암을 보행 패턴으로 구동
 *   - 코인 진동모터 PWM (앨리어싱/흔들림 실험)
 *   - 이벤트 참값 펄스: HS / TO / SYNC 를 STM32 로 보냄 (펄스 폭으로 구분)
 *   - 동기 LED: 카메라(100 fps)와 IMU 기록의 시간 맞춤용
 *
 * 배선 (README_hardware 참고)
 *   D9  → 서보 신호 (서보 전원은 외부 5~6 V, GND 공통)
 *   D5  → MOSFET 게이트 (진동모터, 다이오드 병렬)
 *   D6  → 동기 LED (+220 Ω)
 *   D7  → 이벤트 펄스 → 분압(2.0k/3.3k) → STM32 PB3(D3)
 *   D2  → 프리셋 버튼 (GND로 누름, 내부 풀업)
 *
 * 직렬 명령 (115200 baud, 줄 끝 \n)
 *   m0 정지 유지  m1 사인  m2 보행  | p<deg> 유지 각도  a<deg> 사인 진폭  f<Hz> 사인 주파수
 *   t<ms> 보행 주기  h<deg> HS 각도  o<deg> TO 각도  s<0..1> 입각기 비율
 *   i<0|1> 충격 모드(HS 때 스토퍼를 지나치게 명령)  v<0..255> 진동 PWM
 *   y 동기 펄스(LED+SYNC) 1회   c<us> 서보 중심   g<us/deg> 서보 이득   ? 상태 출력
 *   버튼: 프리셋 0→1→2→3→4 순환 (아래 PRESETS 참고)
 */
#include <Servo.h>

const uint8_t PIN_SERVO = 9, PIN_VIB = 5, PIN_LED = 6, PIN_TRIG = 7, PIN_BTN = 2;

// 펄스 폭 (STM32가 폭으로 이벤트 종류를 구분)
const uint16_t PULSE_HS_US = 3000, PULSE_TO_US = 9000, PULSE_SYNC_US = 30000;
const uint16_t LED_MS = 40;                 // 100 fps 카메라에서 4프레임

// 서보 보정 (조립 후 타워 눈금으로 0°가 수직이 되게 c, 각도가 맞게 g 조정)
int   servoCenterUs = 1500;
float servoUsPerDeg = 10.3f;                // 표준 서보 ≈ 1000 us / 97° 근방 (실측)
int   servoSign = 1;
const float LIM_DEG = 60.0f;

// 동작 파라미터
uint8_t mode = 0;           // 0 HOLD, 1 SINE, 2 GAIT
float holdDeg = 0, sineAmp = 30, sineHz = 0.5f;
float gaitT = 1.2f;         // s
float hsDeg = 20, toDeg = -25, stanceFrac = 0.6f;
bool  impact = false;
float overshootDeg = 6;     // 충격 모드에서 스토퍼 너머로 명령하는 각
uint8_t vibDuty = 0;

Servo sv;
uint32_t t0us, lastUpd, ledOffAt = 0;
uint32_t pulseEndUs = 0; bool pulseOn = false;
float lastPhase = 0;
uint8_t preset = 0;

void startPulse(uint16_t widthUs, bool led) {
  digitalWrite(PIN_TRIG, HIGH);
  pulseOn = true; pulseEndUs = micros() + widthUs;
  if (led) { digitalWrite(PIN_LED, HIGH); ledOffAt = millis() + LED_MS; }
}

void writeDeg(float deg) {
  deg = constrain(deg, -LIM_DEG, LIM_DEG);
  sv.writeMicroseconds(servoCenterUs + (int)(servoSign * servoUsPerDeg * deg));
}

float ease(float u) { return 0.5f * (1 - cos(PI * u)); }

// 보행 패턴: 위상 0 = 유각기 끝(HS 각도). 입각기에 hs→to로 후퇴하며 점점 빨라지고(TO 직전 음의 최소),
// 유각기에 to→hs로 빠르게 전진(mid-swing 양의 피크). 충격 모드에서는 hs 너머로 명령해 스토퍼에 부딪힘.
float gaitAngle(float ph) {
  float target = hsDeg + (impact ? overshootDeg : 0);
  if (ph < stanceFrac) {
    float u = ph / stanceFrac;
    float s = 0.4f * u + 0.6f * u * u;
    return hsDeg + (toDeg - hsDeg) * s;
  }
  float u = (ph - stanceFrac) / (1 - stanceFrac);
  return toDeg + (target - toDeg) * ease(u);
}

void applyPreset(uint8_t p) {
  // 0: 정지(0°)          — 센서 기본 잡음
  // 1: 정지 + 진동       — 흔들림/앨리어싱 데모
  // 2: 느린 보행 (2.0 s) — 필터 지연 눈으로 보기
  // 3: 보행 1.2 s + 충격 — HS 충격 포함
  // 4: 보행 + 충격 + 진동
  preset = p % 5;
  switch (preset) {
    case 0: mode = 0; holdDeg = 0; vibDuty = 0; break;
    case 1: mode = 0; holdDeg = 0; vibDuty = 160; break;
    case 2: mode = 2; gaitT = 2.0f; impact = false; vibDuty = 0; break;
    case 3: mode = 2; gaitT = 1.2f; impact = true;  vibDuty = 0; break;
    case 4: mode = 2; gaitT = 1.2f; impact = true;  vibDuty = 160; break;
  }
  analogWrite(PIN_VIB, vibDuty);
  t0us = micros(); lastPhase = 0;
  Serial.print(F("# preset ")); Serial.println(preset);
}

void status() {
  Serial.print(F("# mode=")); Serial.print(mode);
  Serial.print(F(" hold=")); Serial.print(holdDeg);
  Serial.print(F(" sine=")); Serial.print(sineAmp); Serial.print('@'); Serial.print(sineHz);
  Serial.print(F(" gaitT=")); Serial.print(gaitT, 3);
  Serial.print(F(" hs=")); Serial.print(hsDeg); Serial.print(F(" to=")); Serial.print(toDeg);
  Serial.print(F(" stance=")); Serial.print(stanceFrac, 2);
  Serial.print(F(" impact=")); Serial.print(impact);
  Serial.print(F(" vib=")); Serial.print(vibDuty);
  Serial.print(F(" center=")); Serial.print(servoCenterUs);
  Serial.print(F(" usPerDeg=")); Serial.println(servoUsPerDeg, 2);
}

void handleSerial() {
  static char buf[24]; static uint8_t n = 0;
  while (Serial.available()) {
    char ch = Serial.read();
    if (ch == '\r') continue;
    if (ch != '\n' && n < sizeof(buf) - 1) { buf[n++] = ch; continue; }
    buf[n] = 0; n = 0;
    if (!buf[0]) continue;
    float v = atof(buf + 1);
    switch (buf[0]) {
      case 'm': mode = (uint8_t)v; t0us = micros(); lastPhase = 0; break;
      case 'p': holdDeg = v; break;
      case 'a': sineAmp = v; break;
      case 'f': sineHz = v; break;
      case 't': gaitT = v / 1000.0f; break;
      case 'h': hsDeg = v; break;
      case 'o': toDeg = v; break;
      case 's': stanceFrac = constrain(v, 0.3f, 0.8f); break;
      case 'i': impact = v > 0.5f; break;
      case 'v': vibDuty = (uint8_t)constrain(v, 0, 255); analogWrite(PIN_VIB, vibDuty); break;
      case 'y': startPulse(PULSE_SYNC_US, true); Serial.println(F("# sync")); break;
      case 'c': servoCenterUs = (int)v; break;
      case 'g': servoUsPerDeg = v; break;
      case 'P': applyPreset((uint8_t)v); break;
      case '?': break;
      default: Serial.println(F("# ?cmd")); break;
    }
    status();
  }
}

void handleButton() {
  static bool last = HIGH; static uint32_t tChange = 0;
  bool b = digitalRead(PIN_BTN);
  if (b != last && millis() - tChange > 40) {
    tChange = millis(); last = b;
    if (b == LOW) applyPreset(preset + 1);
  }
}

void setup() {
  pinMode(PIN_VIB, OUTPUT); pinMode(PIN_LED, OUTPUT); pinMode(PIN_TRIG, OUTPUT);
  pinMode(PIN_BTN, INPUT_PULLUP);
  Serial.begin(115200);
  sv.attach(PIN_SERVO, 500, 2500);
  writeDeg(0);
  t0us = lastUpd = micros();
  Serial.println(F("# rig_arduino ready. '?' for status"));
  status();
}

void loop() {
  uint32_t now = micros();
  if (pulseOn && (int32_t)(now - pulseEndUs) >= 0) { digitalWrite(PIN_TRIG, LOW); pulseOn = false; }
  if (ledOffAt && (int32_t)(millis() - ledOffAt) >= 0) { digitalWrite(PIN_LED, LOW); ledOffAt = 0; }
  handleSerial();
  handleButton();

  if (now - lastUpd < 5000) return;          // 200 Hz 명령 갱신 (서보 자체는 50 Hz 프레임)
  lastUpd = now;
  float t = (now - t0us) * 1e-6f;

  if (mode == 0) {
    writeDeg(holdDeg);
  } else if (mode == 1) {
    writeDeg(sineAmp * sin(2 * PI * sineHz * t));
  } else {
    float ph = fmod(t / gaitT, 1.0f);
    float deg = gaitAngle(ph);
    // 명령 기준 참값 이벤트: HS = 유각기에 명령이 hs 각도(스토퍼 위치)를 위로 지날 때, TO = 입각기 끝
    static float lastDeg = 0;
    if (ph >= stanceFrac && lastPhase >= stanceFrac && lastDeg < hsDeg && deg >= hsDeg) startPulse(PULSE_HS_US, true);
    if (lastPhase < stanceFrac && ph >= stanceFrac) startPulse(PULSE_TO_US, false);
    lastPhase = ph; lastDeg = deg;
    writeDeg(deg);
  }
}
