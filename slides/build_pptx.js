const pptxgen = require("pptxgenjs");
const fs = require("fs");
const S = "/tmp/claude-0/-home-user/2d881f96-9a89-58f2-99b0-73650f4069d7/scratchpad/";
const notes = JSON.parse(fs.readFileSync(S + "pp_notes.json", "utf8"));
const OUT = "/home/user/26-2_Sensors_Actuators/slides/midterm_presentation.pptx";

const F = "Malgun Gothic", M = "Courier New";
const NAVY = "16202E", BG = "F7F6F2", BG2 = "ECEFF3", WHITE = "FDFCFA", ACC = "D9572B", ACCD = "B4471D",
  BLUE = "1F5FAD", TXT = "3D4756", MUTE = "646D7A", LINE = "CDD3DA", LBLUE = "2A6FC9", CREAM = "F3F1EA", PEACH = "FFF6F1";

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.33 x 7.5
pres.title = "하지 IMU 필터링의 정확도–지연 트레이드오프 — 중간발표";
const FOOT = "하지 IMU 필터링의 정확도–지연 트레이드오프 · 중간발표";
let n = 0;

function base(bg, kicker, title, dark) {
  const s = pres.addSlide();
  s.background = { color: bg };
  n += 1;
  s.addNotes(notes[n - 1]);
  if (title) {
    s.addText(kicker, { x: 0.7, y: 0.45, w: 11, h: 0.35, fontFace: F, fontSize: 14, bold: true, color: dark ? "F08A5D" : ACCD, margin: 0, isTextBox: true });
    s.addText(title, { x: 0.7, y: 0.8, w: 11.9, h: 0.9, fontFace: F, fontSize: 30, bold: true, color: dark ? CREAM : NAVY, margin: 0, valign: "top", isTextBox: true });
    s.addText(FOOT, { x: 0.7, y: 7.0, w: 9, h: 0.3, fontFace: F, fontSize: 11, color: dark ? "AEB6C2" : MUTE, margin: 0, isTextBox: true });
    s.addText(String(n).padStart(2, "0") + " / 12", { x: 11.6, y: 7.0, w: 1.03, h: 0.3, fontFace: M, fontSize: 11, color: dark ? "AEB6C2" : MUTE, align: "right", margin: 0, isTextBox: true });
  }
  return s;
}
const T = (s, text, o) => s.addText(text, Object.assign({ fontFace: F, fontSize: 16, color: TXT, margin: 0, valign: "top", isTextBox: true }, o));
const card = (s, x, y, w, h, o = {}) => s.addShape(pres.shapes.ROUNDED_RECTANGLE, Object.assign({ x, y, w, h, rectRadius: 0.1, fill: { color: o.fill || WHITE }, line: { color: o.line || LINE, width: o.lw || 1 } }, o.extra || {}));
const takeaway = (s, text, y) => {
  card(s, 0.7, y, 11.93, 0.7, { fill: "FFFFFF", line: ACC, lw: 1.5 });
  T(s, text, { x: 0.95, y, w: 11.4, h: 0.7, fontSize: 18, bold: true, color: NAVY, valign: "middle" });
};

// 1 cover
{
  const s = base(NAVY, "", "", true);
  T(s, "센서 및 액추에이터 · 기말 프로젝트 중간발표", { x: 0.9, y: 0.7, w: 11, h: 0.4, fontSize: 16, color: "AEB6C2" });
  T(s, "하지 IMU 필터링의\n정확도–지연 트레이드오프", { x: 0.9, y: 2.2, w: 11.5, h: 2.2, fontSize: 54, bold: true, color: CREAM, valign: "top" });
  T(s, "인과 · 고정지연 · 비인과(사후) 필터의 비교 연구 계획", { x: 0.9, y: 4.6, w: 11.5, h: 0.6, fontSize: 24, color: "F08A5D" });
  T(s, "[이름] · [학번]", { x: 0.9, y: 6.6, w: 6, h: 0.4, fontSize: 16, color: "AEB6C2" });
  T(s, "2026. 10", { x: 10.4, y: 6.6, w: 2.0, h: 0.4, fontSize: 16, color: "AEB6C2", align: "right", fontFace: M });
}

// 2 gait
{
  const s = base(BG, "연구 배경 1", "보행 이벤트 기반 제어에는 저지연 신호가 필요하다");
  const items = [["측정 신호", "정강이 부착 IMU의 시상면 각속도 (자이로 1축)"], ["활용", "보행 이벤트(TO · MS · HS) 검출 → 외골격 · 의족의 보조 타이밍 결정"], ["요구 조건", "보행 주기 ≈ 1 s → 수십 ms의 지연도 제어 성능에 직접 영향"]];
  items.forEach((it, i) => {
    const y = 2.1 + i * 1.5;
    s.addShape(pres.shapes.OVAL, { x: 0.7, y: y + 0.05, w: 0.5, h: 0.5, fill: { color: ACC }, line: { color: ACC } });
    T(s, String(i + 1), { x: 0.7, y: y + 0.05, w: 0.5, h: 0.5, fontSize: 16, bold: true, color: "FFFFFF", align: "center", valign: "middle", fontFace: M });
    T(s, it[0], { x: 1.45, y, w: 4.3, h: 0.35, fontSize: 14, bold: true, color: ACCD });
    T(s, it[1], { x: 1.45, y: y + 0.4, w: 4.3, h: 1.0, fontSize: 18, color: NAVY });
  });
  card(s, 6.1, 1.95, 6.5, 4.45);
  s.addImage({ path: S + "pp_gait.png", x: 6.25, y: 2.1, w: 6.2, h: 3.35 });
  T(s, "정강이 시상면 각속도 (한 보행 주기)", { x: 6.25, y: 5.6, w: 6.2, h: 0.3, fontSize: 14, color: MUTE, align: "center" });
  T(s, "회색 = 입각기(stance) · 주황 = 유각기(swing)", { x: 6.25, y: 5.95, w: 6.2, h: 0.3, fontSize: 14, color: MUTE, align: "center" });
}

// 3 lag
{
  const s = base(BG, "연구 배경 2", "인과 필터는 잡음을 줄이는 대신 위상 지연을 만든다");
  card(s, 0.7, 1.95, 6.9, 4.5);
  s.addImage({ path: S + "pp_lag.png", x: 0.9, y: 2.1, w: 6.5, h: 3.6 });
  s.addShape(pres.shapes.LINE, { x: 0.95, y: 6.05, w: 0.5, h: 0, line: { color: NAVY, width: 3 } });
  T(s, "참 신호", { x: 1.55, y: 5.9, w: 1.4, h: 0.3, fontSize: 14 });
  s.addShape(pres.shapes.LINE, { x: 3.2, y: 6.05, w: 0.5, h: 0, line: { color: LBLUE, width: 3 } });
  T(s, "인과 저역통과 필터 출력 (개념도)", { x: 3.8, y: 5.9, w: 3.7, h: 0.3, fontSize: 14 });
  card(s, 7.9, 1.95, 4.73, 2.1);
  T(s, "잡음원과 신호 대역", { x: 8.1, y: 2.05, w: 4.4, h: 0.3, fontSize: 14, bold: true, color: ACCD });
  T(s, "착지 충격 · 연부조직 아티팩트(10–30 Hz) · 외부 진동 · 센서 잡음. 보행 성분은 대부분 10 Hz 이하 → 저역통과 필터로 분리", { x: 8.1, y: 2.45, w: 4.4, h: 1.5, fontSize: 15, color: NAVY });
  card(s, 7.9, 4.25, 4.73, 2.2);
  T(s, "지연의 원인", { x: 8.1, y: 4.35, w: 4.4, h: 0.3, fontSize: 14, bold: true, color: BLUE });
  T(s, "인과 필터는 현재 · 과거 샘플만 사용 → 위상 지연 불가피", { x: 8.1, y: 4.75, w: 4.4, h: 0.7, fontSize: 15, color: NAVY });
  T(s, "예: 2차 Butterworth 10 Hz ≈ 30 ms\nMPU-6050 DLPF 42 Hz → 4.8 ms, 5 Hz → 18.6 ms", { x: 8.1, y: 5.5, w: 4.4, h: 0.85, fontSize: 13, color: TXT });
}

// 4 window
{
  const s = base(BG, "연구 배경 3", "사전/사후의 본질적 차이는 미래 샘플의 사용 여부다");
  const xs = [4.3, 5.2, 6.1, 7.0, 7.9, 8.8, 9.7, 10.6, 11.5, 12.4].slice(0, 0); // unused
  const x0 = 3.7, dx = 0.82, cur = 5; // index of "now" among 11 samples (0..10)
  const px = (i) => x0 + i * dx;
  // rows
  const y1 = 2.75, y2 = 4.95;
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: px(1) - 0.2, y: y1 - 0.3, w: 4 * dx + 0.4, h: 0.6, rectRadius: 0.3, fill: { color: "DCE8F8" }, line: { color: LBLUE, width: 1.5 } });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: px(3) - 0.2, y: y2 - 0.3, w: 4 * dx + 0.4, h: 0.6, rectRadius: 0.3, fill: { color: "FBE3D7" }, line: { color: ACC, width: 1.5 } });
  s.addShape(pres.shapes.LINE, { x: px(cur), y: 2.0, w: 0, h: 3.7, line: { color: ACCD, width: 1.5, dashType: "dash" } });
  for (let i = 0; i <= 10; i++) {
    const future = i > cur;
    s.addShape(pres.shapes.OVAL, { x: px(i) - 0.11, y: y1 - 0.11, w: 0.22, h: 0.22, fill: { color: future ? BG : "3D4756" }, line: { color: future ? "9AA3AF" : "3D4756", width: 1.5 } });
    s.addShape(pres.shapes.OVAL, { x: px(i) - 0.11, y: y2 - 0.11, w: 0.22, h: 0.22, fill: { color: "3D4756" }, line: { color: "3D4756" } });
  }
  T(s, "k (현재)", { x: px(cur) - 0.8, y: 1.7, w: 1.6, h: 0.3, fontSize: 14, bold: true, color: ACCD, align: "center", fontFace: M });
  T(s, "인과 이동평균 (사전)", { x: 0.7, y: y1 - 0.4, w: 2.9, h: 0.35, fontSize: 16, bold: true, color: NAVY });
  T(s, "y[k] = mean(x[k−4 … k])", { x: 0.7, y: y1 - 0.02, w: 2.9, h: 0.3, fontSize: 12, color: MUTE, fontFace: M });
  T(s, "출력 ≈ 2샘플 전 값 (군지연)", { x: px(1) - 0.2, y: y1 + 0.4, w: 4 * dx + 0.4, h: 0.3, fontSize: 14, bold: true, color: BLUE, align: "center" });
  T(s, "미수신(미래) 샘플", { x: px(6), y: y1 + 0.4, w: 3.3, h: 0.3, fontSize: 14, color: MUTE });
  T(s, "중심 이동평균 (사후)", { x: 0.7, y: y2 - 0.4, w: 2.9, h: 0.35, fontSize: 16, bold: true, color: NAVY });
  T(s, "y[k] = mean(x[k−2 … k+2])", { x: 0.7, y: y2 - 0.02, w: 2.9, h: 0.3, fontSize: 12, color: MUTE, fontFace: M });
  T(s, "출력 = 현재 값 (영위상, 지연 0)", { x: px(3) - 0.2, y: y2 + 0.4, w: 4 * dx + 0.4, h: 0.3, fontSize: 14, bold: true, color: ACCD, align: "center" });
  T(s, [{ text: "동일 필터의 결과는 계산 시점과 무관 → 차이는 ", options: {} }, { text: "인과성(미래 샘플 사용)", options: { color: ACCD, bold: true } }], { x: 0.7, y: 5.95, w: 11.9, h: 0.5, fontSize: 22, color: NAVY });
  T(s, "비인과 필터는 기록 완료 후에만 적용 가능 → 실시간 제어에는 사용 불가", { x: 0.7, y: 6.5, w: 11.9, h: 0.35, fontSize: 14, color: MUTE });
}

// 5 fixed-lag
{
  const s = base(BG2, "연구 배경 4 · 핵심 관점", "고정지연 스무딩: 사전과 사후 사이의 설계 공간");
  card(s, 0.7, 1.85, 11.93, 0.65);
  T(s, "추정 이론의 구분", { x: 0.9, y: 1.85, w: 2.3, h: 0.65, fontSize: 14, bold: true, color: BLUE, valign: "middle" });
  T(s, "filtering x(k|k) · fixed-lag smoothing x(k−d|k) · smoothing x(k|N)", { x: 3.2, y: 1.85, w: 9.3, h: 0.65, fontSize: 16, color: NAVY, valign: "middle", fontFace: M });
  s.addShape(pres.shapes.LINE, { x: 0.8, y: 3.0, w: 11.7, h: 0, line: { color: "9AA3AF", width: 2.5, endArrowType: "triangle" } });
  T(s, "허용 지연 d", { x: 10.5, y: 2.55, w: 2.1, h: 0.3, fontSize: 14, color: MUTE, align: "right" });
  [[2.9, 0.22, "3D4756"], [6.55, 0.34, ACC], [10.4, 0.22, "3D4756"]].forEach(([cx, d, c]) =>
    s.addShape(pres.shapes.OVAL, { x: cx + 0.55 - d / 2, y: 3.0 - d / 2, w: d, h: d, fill: { color: c }, line: { color: c } }));
  const cols = [[0.7, "d = 0", "인과 필터 (사전)", "현재 · 과거 샘플만 사용 → 위상 지연 발생", false], [4.75, "0 < d < ∞", "고정지연 필터", "d 만큼의 지연을 허용하고 미래 샘플 활용 → 실시간 동작 + 정확도 향상", true], [8.8, "d = ∞", "비인과 필터 (사후)", "전체 기록 사용 → 영위상, 실시간 적용 불가", false]];
  cols.forEach(([x, tag, h, d, hi]) => {
    card(s, x, 3.45, 3.83, 2.35, { fill: hi ? PEACH : WHITE, line: hi ? ACC : LINE, lw: hi ? 2.5 : 1 });
    T(s, tag, { x: x + 0.25, y: 3.6, w: 3.3, h: 0.3, fontSize: 14, bold: hi, color: hi ? ACCD : MUTE, fontFace: M });
    T(s, h, { x: x + 0.25, y: 3.95, w: 3.3, h: 0.45, fontSize: 20, bold: true, color: NAVY });
    T(s, d, { x: x + 0.25, y: 4.5, w: 3.35, h: 1.25, fontSize: 15, color: TXT });
  });
  takeaway(s, "본 연구: 허용 지연 d를 독립변수로 두고, 사후 수준 정확도에 도달하는 최소 지연을 정량화", 6.05);
}

// 6 aliasing
{
  const s = base(BG, "연구 배경 5", "앨리어싱은 샘플링 이전 단계에서만 억제할 수 있다");
  card(s, 0.7, 1.95, 7.2, 3.8);
  s.addImage({ path: S + "pp_alias.png", x: 0.85, y: 2.1, w: 6.9, h: 3.07 });
  s.addShape(pres.shapes.LINE, { x: 0.95, y: 5.4, w: 0.4, h: 0, line: { color: "AEB6C2", width: 2 } });
  T(s, "실제 진동 104 Hz", { x: 1.45, y: 5.25, w: 2.0, h: 0.3, fontSize: 12 });
  s.addShape(pres.shapes.OVAL, { x: 3.6, y: 5.3, w: 0.2, h: 0.2, fill: { color: ACC }, line: { color: ACC } });
  T(s, "샘플 (fs = 100 Hz)", { x: 3.9, y: 5.25, w: 1.9, h: 0.3, fontSize: 12 });
  s.addShape(pres.shapes.LINE, { x: 5.85, y: 5.4, w: 0.4, h: 0, line: { color: ACC, width: 3 } });
  T(s, "관측 4 Hz (alias)", { x: 6.35, y: 5.25, w: 1.5, h: 0.3, fontSize: 12 });
  card(s, 8.2, 1.95, 4.43, 1.1);
  T(s, "나이퀴스트 주파수(fs/2 = 50 Hz)를 넘는 성분은 |f − n·fs|로 접혀 관측된다", { x: 8.4, y: 1.95, w: 4.05, h: 1.1, fontSize: 15, color: NAVY, valign: "middle" });
  [["1", "104 Hz 진동 → |104 − 100| = 4 Hz로 접힘"], ["2", "4 Hz는 보행 운동 대역과 중첩 → 샘플링 후에는 분리 불가"], ["3", "대가: 센서 내부 필터의 지연 (예: DLPF 42 Hz → 4.8 ms)"]].forEach(([k, t], i) => {
    const y = 3.3 + i * 0.82;
    T(s, k, { x: 8.2, y, w: 0.4, h: 0.4, fontSize: 18, bold: true, color: ACCD, fontFace: M });
    T(s, t, { x: 8.65, y, w: 3.95, h: 0.75, fontSize: 15 });
  });
  takeaway(s, "센서 내부 안티앨리어싱 필터 = 사후로 대체할 수 없는 사전 필터", 6.0);
}

// 7 motivation
{
  const s = base(BG, "주제 선정", "연구 질문: 허용 지연에 따른 최적 필터 구성");
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.7, y: 1.85, w: 11.93, h: 1.2, rectRadius: 0.1, fill: { color: NAVY }, line: { color: NAVY } });
  T(s, "RESEARCH QUESTION", { x: 1.0, y: 1.95, w: 6, h: 0.3, fontSize: 12, bold: true, color: "F08A5D" });
  T(s, "허용 지연 d에서 어떤 필터를 어느 단계에 두어야 정확도가 최대인가?", { x: 1.0, y: 2.3, w: 11.4, h: 0.65, fontSize: 24, color: CREAM, bold: true, valign: "middle" });
  T(s, "주제 선정 이유", { x: 0.7, y: 3.3, w: 5, h: 0.3, fontSize: 14, bold: true, color: ACCD });
  ["실시간 제어와 오프라인 분석의 최적 필터는 다르나, 지연–정확도의 정량 비교가 부족", "샘플링 · 앨리어싱 · 센서 내부 필터 · 위상 지연 = 센서 시스템 설계의 핵심", "적응형 · 고정지연 필터를 실제 하지 신호와 임베디드 환경에서 검증"].forEach((t, i) => {
    const y = 3.75 + i * 1.0;
    T(s, String(i + 1), { x: 0.7, y, w: 0.4, h: 0.4, fontSize: 18, bold: true, color: ACCD, fontFace: M });
    T(s, t, { x: 1.15, y, w: 4.9, h: 0.95, fontSize: 15 });
  });
  T(s, "가설", { x: 6.5, y: 3.3, w: 5, h: 0.3, fontSize: 14, bold: true, color: BLUE });
  [["H1", "동일 인과 필터는 MCU와 PC에서 같은 출력 (검증용)"], ["H2", "d ≤ 10 ms에서는 적응형(1€) 필터가 고정 차단 필터보다 정확"], ["H3", "d ≈ 20 ms에서 고정지연 필터가 사후 필터 수준에 도달"], ["H4", "센서 내부 AAF는 사후로 제거 불가능한 앨리어싱을 억제"], ["H5", "동일 필터의 사전 · 사후 중복은 지연 개선 없이 과평활만 유발"]].forEach(([k, t], i) => {
    const y = 3.75 + i * 0.6;
    T(s, k, { x: 6.5, y, w: 0.6, h: 0.5, fontSize: 15, bold: true, color: BLUE, fontFace: M });
    T(s, t, { x: 7.15, y, w: 5.45, h: 0.55, fontSize: 14, bold: k === "H3", color: k === "H3" ? NAVY : TXT });
  });
}

// 8 system
{
  const s = base(BG, "연구 방법 1", "단일 클럭 동기화 기반 측정 시스템");
  const box = (x, y, w, h, t, sub, o = {}) => { card(s, x, y, w, h, o); T(s, t, { x: x + 0.2, y: y + 0.12, w: w - 0.4, h: 0.4, fontSize: 16, bold: true, color: NAVY }); if (sub) T(s, sub, { x: x + 0.2, y: y + 0.55, w: w - 0.4, h: h - 0.6, fontSize: 13, color: MUTE }); };
  box(0.7, 1.85, 3.6, 1.0, "IMU · ICM-42688-P", "정강이 각속도 · SPI 1 kHz");
  box(0.7, 3.0, 3.6, 1.0, "고속 카메라 + 동기 LED", "240 fps · 보행 이벤트 참값");
  box(0.7, 4.15, 3.6, 1.0, "자기 엔코더 · AS5600", "벤치 회전축 → 각도 참값");
  [2.35, 3.5, 4.65].forEach((y) => s.addShape(pres.shapes.LINE, { x: 4.35, y, w: 0.7, h: 0, line: { color: "8A939F", width: 2, endArrowType: "triangle" } }));
  card(s, 5.1, 1.85, 4.0, 3.3, { fill: PEACH, line: ACC, lw: 2.5 });
  T(s, "STM32 Nucleo-F446RE", { x: 5.35, y: 2.0, w: 3.5, h: 0.45, fontSize: 18, bold: true, color: NAVY });
  T(s, "Cortex-M4F 180 MHz · FPU", { x: 5.35, y: 2.5, w: 3.5, h: 0.3, fontSize: 12, color: ACCD, fontFace: M });
  T(s, ["1 µs 타이머 공통 타임스탬프", "실시간 인과 · 고정지연 필터", "raw + 필터 출력 동시 로깅"].map((t, i, a) => ({ text: t, options: { bullet: true, breakLine: i < a.length - 1 } })), { x: 5.35, y: 3.0, w: 3.55, h: 2.0, fontSize: 15, paraSpaceAfter: 8 });
  s.addShape(pres.shapes.LINE, { x: 9.15, y: 3.5, w: 0.8, h: 0, line: { color: "8A939F", width: 2, endArrowType: "triangle" } });
  T(s, "UART", { x: 9.15, y: 3.15, w: 0.8, h: 0.3, fontSize: 12, color: MUTE, align: "center", fontFace: M });
  box(10.0, 2.85, 2.63, 1.3, "PC", "비인과 필터 · 지표 · 통계");
  box(0.7, 5.5, 4.4, 1.15, "Arduino Uno", "서보 구동 · 저사양 MCU 연산 비교");
  s.addShape(pres.shapes.LINE, { x: 5.15, y: 6.07, w: 0.9, h: 0, line: { color: "8A939F", width: 2, endArrowType: "triangle" } });
  T(s, "PWM", { x: 5.15, y: 5.72, w: 0.9, h: 0.3, fontSize: 12, color: MUTE, align: "center", fontFace: M });
  box(6.1, 5.5, 3.0, 1.15, "MG996R 서보", "벤치 링크 구동");
  s.addShape(pres.shapes.LINE, { x: 3.0, y: 5.5, w: 2.1, h: -0.35, flipV: false, line: { color: "8A939F", width: 1.5, dashType: "dash" } });
  T(s, "단일 클럭 동기화 = ms 단위 지연 측정의 전제 조건", { x: 9.3, y: 5.6, w: 3.3, h: 1.0, fontSize: 16, bold: true, color: NAVY });
}

// 9 filters
{
  const s = base(BG, "연구 방법 2", "비교 필터: 세 계열 × 세 처리 시점");
  const hdr = (t, c) => ({ text: t, options: { bold: true, color: c || CREAM, fill: { color: NAVY }, fontFace: F, fontSize: 15 } });
  const cell = (t, f, b) => ({ text: t, options: { fontFace: F, fontSize: 15, color: b ? NAVY : TXT, fill: { color: f }, bold: !!b } });
  s.addTable([
    [hdr("필터 계열"), hdr("인과 (d = 0)"), hdr("고정지연 (0 < d < ∞)", "F08A5D"), hdr("비인과 · 사후 (d = ∞)")],
    [cell("고전 선형 (기준선)", WHITE, 1), cell("2차 Butterworth IIR", WHITE), cell("선형위상 FIR", WHITE), cell("영위상 Butterworth", WHITE)],
    [cell("적응형", BG2, 1), cell("1€ filter", BG2), cell("–", BG2), cell("–", BG2)],
    [cell("모델 기반", WHITE, 1), cell("Kalman filter", WHITE), cell("고정지연 칼만 스무더", WHITE), cell("RTS 스무더", WHITE)],
  ], { x: 0.7, y: 1.85, w: 11.93, colW: [2.9, 2.9, 3.2, 2.93], rowH: 0.55, border: { type: "solid", color: LINE, pt: 1 }, valign: "middle", margin: [0, 0.15, 0, 0.15] });
  [["Butterworth", "최대 평탄 응답의 표준 저역통과 필터. 사후형은 정 · 역방향 통과(filtfilt)로 영위상"], ["1€ filter (Casiez 2012)", "변화율에 따라 차단 주파수 적응: f_c = f_min + β·|dx/dt| → 저속 구간 평활, 고속 구간 저지연"], ["Kalman 계열", "상태 [ω, ω′] 등속 모델. filtering → fixed-lag → RTS smoothing이 세 시점에 일대일 대응"]].forEach(([h, d], i) => {
    const x = 0.7 + i * 4.05;
    card(s, x, 4.4, 3.83, 1.75);
    T(s, h, { x: x + 0.2, y: 4.5, w: 3.45, h: 0.35, fontSize: 15, bold: true, color: ACCD });
    T(s, d, { x: x + 0.2, y: 4.9, w: 3.45, h: 1.2, fontSize: 14 });
  });
  [["+ 센서 내부 AAF ON / OFF", 3.1], ["+ 공통 전처리: 정지 10 s 구간 재귀 평균으로 자이로 바이어스 보정", 7.2]].forEach(([t, w], i) => {
    const x = i === 0 ? 0.7 : 4.0;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 6.35, w: i === 0 ? 3.0 : 8.6, h: 0.45, rectRadius: 0.22, fill: { color: BG2 }, line: { color: BG2 } });
    T(s, t, { x: x + 0.2, y: 6.35, w: (i === 0 ? 3.0 : 8.6) - 0.3, h: 0.45, fontSize: 13, color: NAVY, valign: "middle" });
  });
}

// 10 experiments
{
  const s = base(BG, "연구 방법 3", "참값을 확보할 수 있는 세 가지 실험");
  [["실험 1", "벤치 실험", "참값: AS5600 엔코더 각도", ["서보 구동 링크 (정강이 모형)", "사인파 · 보행 궤적 재생", "충돌 · 진동모터로 잡음 통제"]],
   ["실험 2", "인체 보행 실험", "참값: 고속 영상 (240 fps)", ["3–5명 · 트레드밀 3속도 × 2분", "영상에서 HS/TO 프레임 판독 → 검출 시점 오차", "동기 LED로 영상–IMU 시간 정렬"]],
   ["실험 3", "임베디드 실험", "기준: PC 연산 결과", ["동일 raw를 MCU에 재생 (HIL)", "샘플당 연산 시간 · 메모리", "PC 출력과 수치 일치 (H1)"]]].forEach(([k, h, g, l], i) => {
    const x = 0.7 + i * 4.05;
    card(s, x, 1.95, 3.83, 4.6);
    T(s, k, { x: x + 0.3, y: 2.15, w: 2.5, h: 0.3, fontSize: 14, bold: true, color: ACCD, fontFace: M });
    T(s, h, { x: x + 0.3, y: 2.55, w: 3.3, h: 0.5, fontSize: 24, bold: true, color: NAVY });
    T(s, g, { x: x + 0.3, y: 3.2, w: 3.3, h: 0.35, fontSize: 14, bold: true, color: BLUE });
    T(s, l.map((t, j, a) => ({ text: t, options: { bullet: true, breakLine: j < a.length - 1 } })), { x: x + 0.3, y: 3.8, w: 3.3, h: 2.6, fontSize: 16, paraSpaceAfter: 10 });
  });
}

// 11 metrics
{
  const s = base(BG, "연구 방법 4", "평가 지표: 지연과 지연 보정 오차를 함께 본다");
  [["01", "지연 D (ms)", "출력과 참값 x(t − D)의 상호상관이 최대가 되는 D"], ["02", "지연 보정 RMSE", "D만큼 정렬한 뒤의 오차 → 파형 왜곡 + 잔여 잡음"], ["03", "이벤트 시점 오차", "HS/TO 오차의 평균(보정 가능한 지연)과 표준편차(지터)"], ["04", "연산 비용", "샘플당 µs · 메모리 (Uno vs STM32)"]].forEach(([k, h, d], i) => {
    const x = 0.7 + (i % 2) * 3.7, y = 1.95 + Math.floor(i / 2) * 2.2;
    card(s, x, y, 3.5, 2.0);
    T(s, k, { x: x + 0.25, y: y + 0.15, w: 1, h: 0.3, fontSize: 14, bold: true, color: ACCD, fontFace: M });
    T(s, h, { x: x + 0.25, y: y + 0.5, w: 3.0, h: 0.4, fontSize: 18, bold: true, color: NAVY });
    T(s, d, { x: x + 0.25, y: y + 0.95, w: 3.0, h: 1.0, fontSize: 14 });
  });
  card(s, 8.2, 1.95, 4.43, 4.2);
  T(s, "산출물: 필터 계열별 지연–정확도 곡선", { x: 8.4, y: 2.05, w: 4.1, h: 0.35, fontSize: 14, bold: true, color: BLUE });
  s.addImage({ path: S + "pp_curve.png", x: 8.55, y: 2.5, w: 3.75, h: 2.6 });
  T(s, "RMSE", { x: 8.45, y: 2.45, w: 0.8, h: 0.3, fontSize: 12, color: MUTE, fontFace: M });
  T(s, "허용 지연 d →", { x: 10.4, y: 5.1, w: 2.1, h: 0.3, fontSize: 12, color: MUTE, align: "right" });
  T(s, "사후 필터 기준선 · 도달 최소 지연 d*", { x: 8.4, y: 5.4, w: 4.1, h: 0.6, fontSize: 13, bold: true, color: ACCD });
  T(s, "통계: 보폭 단위 반복측정 설계 · Friedman 검정 + Wilcoxon 사후검정 (Bonferroni 보정)", { x: 0.7, y: 6.45, w: 11.9, h: 0.35, fontSize: 14, color: MUTE });
}

// 12 schedule
{
  const s = base(NAVY, "향후 계획", "연구 일정 및 기대 효과", true);
  const wk = [["9주", "측정 시스템 구축"], ["10주", "벤치 실험"], ["11주", "임베디드 실험"], ["12주", "인체 보행 실험"], ["13주", "분석 · 통계"], ["14주", "결과 정리"], ["15주", "기말 발표"]];
  s.addShape(pres.shapes.LINE, { x: 0.9, y: 2.75, w: 11.5, h: 0, line: { color: "3A4658", width: 3 } });
  wk.forEach(([w, t], i) => {
    const cx = 1.6 + i * 1.7;
    s.addShape(pres.shapes.OVAL, { x: cx - 0.13, y: 2.62, w: 0.26, h: 0.26, fill: { color: "F08A5D" }, line: { color: "F08A5D" } });
    T(s, w, { x: cx - 0.8, y: 3.0, w: 1.6, h: 0.3, fontSize: 14, bold: true, color: "F08A5D", align: "center", fontFace: M });
    T(s, t, { x: cx - 0.8, y: 3.4, w: 1.6, h: 0.7, fontSize: 15, color: CREAM, align: "center" });
  });
  T(s, "기대 효과", { x: 0.9, y: 4.6, w: 4, h: 0.3, fontSize: 14, bold: true, color: "AEB6C2" });
  T(s, "허용 지연에 따른 필터 선택 가이드라인\n“d ms가 허용되면, 이 필터를 이 단계에”", { x: 0.9, y: 5.0, w: 11.5, h: 1.2, fontSize: 26, color: CREAM });
  T(s, "감사합니다", { x: 0.9, y: 6.3, w: 6, h: 0.6, fontSize: 28, bold: true, color: CREAM });
}

pres.writeFile({ fileName: OUT }).then(() => console.log("written", OUT));
