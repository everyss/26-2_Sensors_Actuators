const pptxgen = require("pptxgenjs");
const fs = require("fs");
const S = "/tmp/claude-0/-home-user/2d881f96-9a89-58f2-99b0-73650f4069d7/scratchpad/";
const notes = JSON.parse(fs.readFileSync(S + "pp_notes8.json", "utf8"));
const OUT = "/home/user/26-2_Sensors_Actuators/slides/midterm_presentation.pptx";

const F = "Malgun Gothic", M = "Courier New";
const NAVY = "16202E", BG = "F7F6F2", BG2 = "ECEFF3", WHITE = "FDFCFA", ACC = "D9572B", ACCD = "B4471D",
  BLUE = "1F5FAD", TXT = "3D4756", MUTE = "646D7A", LINE = "CDD3DA", LBLUE = "2A6FC9", CREAM = "F3F1EA", PEACH = "FFF6F1", ORL = "F08A5D";
const TOTAL = 8;
const DEFAULT_FOOT = "MPU-6050 자이로 신호에 고정지연 필터를 적용한 저지연 보행 이벤트 검출 · 중간발표";

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.33 x 7.5 in
pres.title = "IMU 신호에 고정지연 필터를 적용한 저지연 보행 이벤트 검출 (중간발표)";
let n = 0;

const T = (s, text, o) => s.addText(text, Object.assign({ fontFace: F, fontSize: 16, color: TXT, margin: 0, valign: "top", isTextBox: true }, o));
const card = (s, x, y, w, h, o = {}) => s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.1, fill: { color: o.fill || WHITE }, line: { color: o.line || LINE, width: o.lw || 1 } });
const pill = (s, x, y, w, text, o = {}) => {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h: 0.42, rectRadius: 0.21, fill: { color: o.fill || BG2 }, line: { color: o.fill || BG2 } });
  T(s, text, { x, y, w, h: 0.42, fontSize: 13, bold: !!o.bold, color: o.color || NAVY, align: "center", valign: "middle" });
};
const arrowR = (s, x, y, w, color) => s.addShape(pres.shapes.LINE, { x, y, w, h: 0, line: { color: color || "8A939F", width: 2.5, endArrowType: "triangle" } });
const bullets = (items) => items.map((t, i, a) => ({ text: t, options: { bullet: true, breakLine: i < a.length - 1 } }));

function slide(bg, kicker, title, foot, dark) {
  const s = pres.addSlide();
  s.background = { color: bg };
  n += 1;
  s.addNotes(notes[n - 1]);
  if (title) {
    T(s, kicker, { x: 0.7, y: 0.45, w: 11, h: 0.35, fontSize: 14, bold: true, color: dark ? ORL : ACCD });
    T(s, title, { x: 0.7, y: 0.8, w: 11.9, h: 0.9, fontSize: 30, bold: true, color: dark ? CREAM : NAVY });
  }
  T(s, foot || DEFAULT_FOOT, { x: 0.7, y: 7.0, w: 10.4, h: 0.3, fontSize: 11, color: dark ? "AEB6C2" : MUTE });
  T(s, `${n} / ${TOTAL}`, { x: 11.6, y: 7.0, w: 1.03, h: 0.3, fontSize: 11, color: dark ? "AEB6C2" : MUTE, align: "right", fontFace: M });
  return s;
}

// 1 제목과 저자
{
  const s = slide(NAVY, "", "", " ", true);
  T(s, "IMU 신호에\n고정지연 필터를 적용한\n저지연 보행 이벤트 검출", { x: 0.9, y: 1.8, w: 11.5, h: 2.7, fontSize: 40, bold: true, color: CREAM });
  T(s, "실시간 · 고정지연 · 사후 필터의 정확도–지연 비교", { x: 0.9, y: 4.6, w: 11.5, h: 0.5, fontSize: 22, color: ORL });
}

// 2 연구배경 (1장)
{
  const s = slide(BG, "2. 연구 배경", "연구 배경: 필터는 정확도와 지연이 상충한다", "출처: Aminian et al., J. Biomech., 2002 · Winter, Biomechanics and Motor Control of Human Movement, 2009");
  [["HS(뒤꿈치 닿기) · TO(발끝 떼기)를 정강이 IMU(관성측정장치)로 검출 → 외골격 보조 타이밍", ACC],
   ["실시간 필터: 잡음 제거 대신 지연 발생 (10 Hz Butterworth ≈ 30 ms)", LBLUE],
   ["사후 필터: 지연 0, 그러나 측정 후에만 가능 → 실시간 불가", LBLUE]].forEach(([t, c], i) => {
    const y = 2.0 + i * 1.05;
    s.addShape(pres.shapes.OVAL, { x: 0.7, y: y + 0.05, w: 0.42, h: 0.42, fill: { color: c }, line: { color: c } });
    T(s, String(i + 1), { x: 0.7, y: y + 0.05, w: 0.42, h: 0.42, fontSize: 14, bold: true, color: "FFFFFF", align: "center", valign: "middle", fontFace: M });
    T(s, t, { x: 1.3, y, w: 4.5, h: 0.95, fontSize: 16, color: NAVY });
  });
  card(s, 0.7, 5.25, 5.1, 0.75, { fill: "FFFFFF", line: ACC, lw: 1.5 });
  T(s, "문제: 얼마나 기다리면 충분한지 기준이 없다", { x: 0.9, y: 5.25, w: 4.8, h: 0.75, fontSize: 15, bold: true, color: NAVY, valign: "middle" });
  card(s, 6.1, 1.95, 6.5, 4.45);
  s.addImage({ path: S + "pp_gait.png", x: 6.25, y: 2.1, w: 6.2, h: 3.35 });
  T(s, "정강이 각속도 (한 보행 주기) · 회색 = 입각기 · 주황 = 유각기", { x: 6.25, y: 5.7, w: 6.2, h: 0.35, fontSize: 13, color: MUTE, align: "center" });
}

// 3 연구목표
{
  const s = slide(BG2, "3. 연구 목적", "연구 목적: IMU에 필터를 적용해 늦지 않게 검출한다", "AAF = Anti-Aliasing Filter(앨리어싱 방지 필터) · 출처: Rauch et al., AIAA J., 1965 · Casiez et al., CHI 2012");
  card(s, 0.7, 1.95, 3.35, 2.75);
  T(s, "센서", { x: 0.95, y: 2.1, w: 3, h: 0.3, fontSize: 13, bold: true, color: BLUE });
  T(s, "MPU-6050", { x: 0.95, y: 2.5, w: 3, h: 0.55, fontSize: 24, bold: true, color: NAVY });
  T(s, "정강이 자이로 각속도\n100 Hz 샘플링\n내부 AAF ON/OFF", { x: 0.95, y: 3.15, w: 3, h: 1.4, fontSize: 15, color: TXT, paraSpaceAfter: 4 });
  s.addShape(pres.shapes.RIGHT_ARROW, { x: 4.12, y: 3.1, w: 0.42, h: 0.36, fill: { color: ACC }, line: { color: ACC } });
  card(s, 4.6, 1.95, 4.15, 2.75, { fill: PEACH, line: ACC, lw: 2.5 });
  T(s, "적용 필터", { x: 4.85, y: 2.1, w: 3.7, h: 0.3, fontSize: 13, bold: true, color: ACCD });
  T(s, "Butterworth · 1€ · 칼만", { x: 4.85, y: 2.5, w: 3.8, h: 0.55, fontSize: 20, bold: true, color: NAVY });
  T(s, "각각 3가지 시점으로 적용", { x: 4.85, y: 3.15, w: 3.7, h: 0.4, fontSize: 15, color: TXT });
  pill(s, 4.85, 3.75, 0.95, "실시간");
  pill(s, 5.88, 3.75, 1.75, "고정지연 (d ms)", { fill: ACC, color: "FFFFFF", bold: true });
  pill(s, 7.71, 3.75, 0.85, "사후");
  s.addShape(pres.shapes.RIGHT_ARROW, { x: 8.82, y: 3.1, w: 0.42, h: 0.36, fill: { color: ACC }, line: { color: ACC } });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 9.3, y: 1.95, w: 3.33, h: 2.75, rectRadius: 0.1, fill: { color: NAVY }, line: { color: NAVY } });
  T(s, "목표", { x: 9.55, y: 2.1, w: 2.9, h: 0.3, fontSize: 13, bold: true, color: ORL });
  T(s, "HS · TO를 실시간 검출", { x: 9.55, y: 2.5, w: 2.9, h: 0.8, fontSize: 19, bold: true, color: CREAM });
  T(s, "사후 필터 수준 정확도에 도달하는 최소 지연 d* 찾기", { x: 9.55, y: 3.35, w: 2.9, h: 1.2, fontSize: 15, color: "D5D9DF" });
  card(s, 0.7, 5.0, 11.93, 1.25);
  T(s, [{ text: "핵심 아이디어 · 고정지연 필터: ", options: { bold: true, color: NAVY } }, { text: "d ms만 기다렸다가 미래 샘플 몇 개를 함께 써서, 실시간이면서 사후에 가까운 정확도를 얻는다" }], { x: 0.95, y: 5.0, w: 11.4, h: 1.25, fontSize: 17, color: NAVY, valign: "middle" });
}

// 5 연구내용 1: 흐름도
{
  const s = slide(BG, "4. 연구내용 ①", "연구내용 ①: 연구 흐름도", " ");
  const boxes = [
    ["① 측정", "MPU-6050", "정강이 각속도\n센서 내부 AAF ON/OFF\n100 Hz 영상 = 참값", 0],
    ["② 실시간", "STM32", "인과 필터\n고정지연 필터 (d)\n공통 타임스탬프", 1],
    ["③ 사후", "PC", "비인과 필터\n(영위상 · RTS)", 0],
    ["④ 평가", "지표 계산", "지연 D\n지연 보정 RMSE\n이벤트 시점 오차", 0],
    ["⑤ 산출물", "선택 기준", "지연–정확도 곡선\n최소 지연 d*", 2],
  ];
  const w = 2.15, gap = 0.3;
  boxes.forEach(([k, h, d, style], i) => {
    const x = 0.7 + i * (w + gap);
    if (style === 2) s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 1.95, w, h: 2.6, rectRadius: 0.1, fill: { color: NAVY }, line: { color: NAVY } });
    else card(s, x, 1.95, w, 2.6, style === 1 ? { fill: PEACH, line: ACC, lw: 2.5 } : {});
    T(s, k, { x: x + 0.18, y: 2.1, w: w - 0.3, h: 0.3, fontSize: 13, bold: true, color: style === 2 ? ORL : ACCD, fontFace: M });
    T(s, h, { x: x + 0.18, y: 2.45, w: w - 0.3, h: 0.4, fontSize: 17, bold: true, color: style === 2 ? CREAM : NAVY });
    T(s, d, { x: x + 0.18, y: 2.95, w: w - 0.3, h: 1.5, fontSize: 13, color: style === 2 ? "D5D9DF" : TXT, paraSpaceAfter: 4 });
    if (i < boxes.length - 1) arrowR(s, x + w + 0.02, 3.25, gap - 0.04);
  });
  card(s, 0.7, 4.9, 11.93, 1.55);
  T(s, "세 가지 실험 → ① 측정 데이터", { x: 0.95, y: 5.05, w: 8, h: 0.3, fontSize: 13, bold: true, color: BLUE });
  pill(s, 0.95, 5.6, 3.7, "벤치: 서보 모터로 정강이 모형 구동");
  pill(s, 4.85, 5.6, 3.6, "인체 보행: 3명 · 트레드밀 3속도");
  pill(s, 8.65, 5.6, 3.75, "임베디드: Arduino vs STM32 연산 비용");
}

// 6 연구내용 2: 적용 방법
{
  const s = slide(BG, "4. 연구내용 ②", "연구내용 ②: 필터를 세 시점으로 적용한다", "출처: Casiez et al., CHI 2012 (1€ 필터) · Rauch et al., AIAA J. 1965 (RTS)");
  const hdr = (t, c) => ({ text: t, options: { bold: true, color: c || CREAM, fill: { color: NAVY }, fontFace: F, fontSize: 15 } });
  const cell = (t, f, b) => ({ text: t, options: { fontFace: F, fontSize: 15, color: b ? NAVY : TXT, fill: { color: f }, bold: !!b } });
  s.addTable([
    [hdr("필터 계열"), hdr("실시간 (d = 0)"), hdr("고정지연 (0 < d < ∞)", ORL), hdr("사후 (d = ∞)")],
    [cell("저역통과", WHITE, 1), cell("2차 Butterworth", WHITE), cell("선형위상 FIR", WHITE), cell("영위상 Butterworth", WHITE)],
    [cell("적응형", BG2, 1), cell("1€ 필터", BG2), cell("–", BG2), cell("–", BG2)],
    [cell("칼만", WHITE, 1), cell("칼만 필터", WHITE), cell("고정지연 스무더", WHITE), cell("RTS 스무더", WHITE)],
  ], { x: 0.7, y: 1.95, w: 11.93, colW: [2.3, 3.2, 3.23, 3.2], rowH: 0.5, border: { type: "solid", color: LINE, pt: 1 }, valign: "middle", margin: [0, 0.15, 0, 0.15] });
  [[0.7, "수업 내용 적용", ACCD, ["이동평균 · 저역통과 → Butterworth · FIR", "칼만 필터 → 실시간 · 고정지연 · RTS", "재귀 평균 필터 → 자이로 바이어스 보정", "샘플링 · 앨리어싱 → 센서 내부 AAF ON/OFF"]],
   [6.75, "평가 지표 · 장비", BLUE, ["지연 D · 지연 보정 RMSE(평균제곱근오차)", "HS/TO 이벤트 시점 오차 (평균 · 지터)", "MCU(마이크로컨트롤러) 연산 시간 · 메모리", "MPU-6050 · STM32 · Arduino · 100 Hz 카메라"]]].forEach(([x, h, c, items]) => {
    card(s, x, 4.25, 5.88, 2.5);
    T(s, h, { x: x + 0.25, y: 4.4, w: 5.4, h: 0.3, fontSize: 13, bold: true, color: c });
    T(s, bullets(items), { x: x + 0.25, y: 4.8, w: 5.45, h: 1.9, fontSize: 14, paraSpaceAfter: 6 });
  });
}

// 7 연구내용 3: 진행 현황
{
  const s = slide(BG, "4. 연구내용 ③", "연구내용 ③: 진행 현황 및 향후 계획", " ");
  const rows = [["완료", BLUE, "FFFFFF", "연구 설계 · 가설 수립\n필터 구현 및 합성 신호 예비 검증 (Python)", {}],
    ["진행 중", ACCD, "FFFFFF", "측정 시스템 구축: STM32 + MPU-6050 + 동기 LED", { fill: PEACH, line: ACC, lw: 2.5 }],
    ["예정", "D5D9DF", NAVY, "벤치 · 임베디드 · 인체 보행 실험, 분석", {}]];
  rows.forEach(([tag, bg, fg, d, o], i) => {
    const y = 1.95 + i * 1.45;
    card(s, 0.7, y, 7.2, 1.25, o);
    pill(s, 0.95, y + 0.2, 1.15, tag, { fill: bg, color: fg, bold: true });
    T(s, d, { x: 2.35, y: y + 0.18, w: 5.4, h: 0.95, fontSize: 16, color: NAVY });
  });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 8.2, y: 1.95, w: 4.43, h: 4.15, rectRadius: 0.1, fill: { color: NAVY }, line: { color: NAVY } });
  T(s, "향후 일정", { x: 8.45, y: 2.1, w: 3.9, h: 0.3, fontSize: 13, bold: true, color: ORL });
  [["9–10주", "시스템 구축 · 벤치 실험"], ["11주", "임베디드 실험"], ["12주", "인체 보행 실험"], ["13–14주", "분석 · 결과 정리"], ["15주", "기말 발표"]].forEach(([w, t], i) => {
    const y = 2.6 + i * 0.66;
    T(s, w, { x: 8.45, y, w: 1.2, h: 0.35, fontSize: 14, color: ORL, fontFace: M });
    T(s, t, { x: 9.75, y, w: 2.7, h: 0.35, fontSize: 14, color: CREAM });
  });
}

// 8 기대효과
{
  const s = slide(BG2, "5. 기대효과", "기대효과: 허용 지연별 필터 선택 기준", " ");
  [["새로운 방법론", "허용 지연별 필터 선택 가이드라인", "“d ms 허용 → 이 필터를 이 단계에”", {}],
   ["분석 틀", "지연과 지연 보정 오차를 분리한 평가", "필터 계열별 지연–정확도 곡선", {}],
   ["연구실 기여", "[소속 연구실]의 보행 보조 · 웨어러블 연구에 실시간 신호처리 설계 기준으로 활용", "저사양 MCU에서 가능한 필터 범위도 제시", { fill: PEACH, line: ACC, lw: 2.5 }]].forEach(([k, h, d, o], i) => {
    const x = 0.7 + i * 4.05;
    card(s, x, 1.95, 3.83, 4.4, o);
    s.addShape(pres.shapes.OVAL, { x: x + 0.3, y: 2.2, w: 0.6, h: 0.6, fill: { color: ACC }, line: { color: ACC } });
    T(s, String(i + 1), { x: x + 0.3, y: 2.2, w: 0.6, h: 0.6, fontSize: 18, bold: true, color: "FFFFFF", align: "center", valign: "middle", fontFace: M });
    T(s, k, { x: x + 0.3, y: 3.05, w: 3.3, h: 0.3, fontSize: 13, bold: true, color: ACCD });
    T(s, h, { x: x + 0.3, y: 3.45, w: 3.3, h: 1.6, fontSize: 18, bold: true, color: NAVY });
    T(s, d, { x: x + 0.3, y: 5.15, w: 3.3, h: 1.0, fontSize: 14, color: TXT });
  });
}

// 8 결언
{
  const s = slide(NAVY, "6. 결언", "결언", " ", true);
  [["무엇을", "MPU-6050 자이로에 3종 필터 × 3시점(실시간 · 고정지연 · 사후) 적용"], ["어떻게", "같은 데이터 · 영상 참값으로 지연과 이벤트 검출 정확도 비교"], ["결과물", "사후 수준에 도달하는 최소 지연 d* → 허용 지연별 필터 선택 기준"]].forEach(([k, t], i) => {
    const y = 2.1 + i * 0.9;
    T(s, k, { x: 0.7, y, w: 1.6, h: 0.6, fontSize: 18, bold: true, color: ORL });
    T(s, t, { x: 2.4, y, w: 10.2, h: 0.7, fontSize: 18, color: CREAM });
  });
}

pres.writeFile({ fileName: OUT }).then(() => console.log("written", OUT));
