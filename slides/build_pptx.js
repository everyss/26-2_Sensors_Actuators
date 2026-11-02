const pptxgen = require("pptxgenjs");
const fs = require("fs");
const S = "/tmp/claude-0/-home-user/2d881f96-9a89-58f2-99b0-73650f4069d7/scratchpad/";
const notes = JSON.parse(fs.readFileSync(S + "pp_notes9.json", "utf8"));
const OUT = "/home/user/26-2_Sensors_Actuators/slides/midterm_presentation.pptx";

const F = "Malgun Gothic", M = "Courier New";
const NAVY = "16202E", BG = "F7F6F2", BG2 = "ECEFF3", WHITE = "FDFCFA", ACC = "D9572B", ACCD = "B4471D",
  BLUE = "1F5FAD", TXT = "3D4756", MUTE = "646D7A", LINE = "CDD3DA", LBLUE = "2A6FC9", CREAM = "F3F1EA", PEACH = "FFF6F1", ORL = "F08A5D";
const TOTAL = 9;
const DEFAULT_FOOT = "실시간 보행 이벤트 검출을 위한 하지 IMU 필터링 · 중간발표";

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.33 x 7.5 in
pres.title = "실시간 보행 이벤트 검출을 위한 하지 IMU 신호의 필터링 시점별 정확도–지연 비교 (중간발표)";
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
  const s = slide(NAVY, "", "", "센서 및 액추에이터 · 2026-2", true);
  T(s, "센서 및 액추에이터 · 2026-2", { x: 0.9, y: 0.7, w: 11, h: 0.4, fontSize: 16, color: "AEB6C2" });
  T(s, "실시간 보행 이벤트 검출을 위한\n하지 IMU 신호의 필터링 시점별\n정확도–지연 비교", { x: 0.9, y: 1.6, w: 11.5, h: 2.7, fontSize: 40, bold: true, color: CREAM });
  T(s, "인과 · 고정지연 · 비인과 필터를 중심으로", { x: 0.9, y: 4.35, w: 11.5, h: 0.5, fontSize: 22, color: ORL });
  T(s, "(중간발표, [발표일])", { x: 0.9, y: 4.95, w: 11.5, h: 0.4, fontSize: 16, color: CREAM });
  T(s, "[1저자] · [2저자] · [3저자]", { x: 0.9, y: 5.9, w: 8, h: 0.4, fontSize: 18, bold: true, color: CREAM });
  T(s, "[소속 연구실]", { x: 0.9, y: 6.35, w: 8, h: 0.35, fontSize: 14, color: "AEB6C2" });
}

// 2 연구배경 1
{
  const s = slide(BG, "연구배경 1", "보행 보조에는 빠르고 정확한 IMU 신호가 필요하다", "출처: Aminian et al., J. Biomech. 35(5), 2002");
  [["측정", "IMU(관성측정장치)로 정강이 회전 각속도 측정"], ["활용", "HS(뒤꿈치 닿기) · TO(발끝 떼기) 시점에 외골격이 보조력 인가"], ["요구 조건", "보행 주기 ≈ 1 s → 수십 ms 지연도 보조 타이밍 오차"]].forEach(([h, d], i) => {
    const y = 2.1 + i * 1.5;
    s.addShape(pres.shapes.OVAL, { x: 0.7, y: y + 0.05, w: 0.5, h: 0.5, fill: { color: ACC }, line: { color: ACC } });
    T(s, String(i + 1), { x: 0.7, y: y + 0.05, w: 0.5, h: 0.5, fontSize: 16, bold: true, color: "FFFFFF", align: "center", valign: "middle", fontFace: M });
    T(s, h, { x: 1.45, y, w: 4.3, h: 0.35, fontSize: 14, bold: true, color: ACCD });
    T(s, d, { x: 1.45, y: y + 0.4, w: 4.3, h: 1.0, fontSize: 18, color: NAVY });
  });
  card(s, 6.1, 1.95, 6.5, 4.45);
  s.addImage({ path: S + "pp_gait.png", x: 6.25, y: 2.1, w: 6.2, h: 3.35 });
  T(s, "정강이 각속도 (한 보행 주기)", { x: 6.25, y: 5.6, w: 6.2, h: 0.3, fontSize: 14, color: MUTE, align: "center" });
  T(s, "회색 = 입각기 · 주황 = 유각기", { x: 6.25, y: 5.95, w: 6.2, h: 0.3, fontSize: 14, color: MUTE, align: "center" });
}

// 3 연구배경 2
{
  const s = slide(BG, "연구배경 2", "기존 방식의 한계: 실시간은 늦고, 사후는 쓸 수 없다", "출처: Winter, Biomechanics and Motor Control of Human Movement, 4th ed., 2009");
  const x0 = 3.7, dx = 0.8, cur = 5, px = (i) => x0 + i * dx, y1 = 2.5, y2 = 3.95;
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: px(1) - 0.2, y: y1 - 0.28, w: 4 * dx + 0.4, h: 0.56, rectRadius: 0.28, fill: { color: "DCE8F8" }, line: { color: LBLUE, width: 1.5 } });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: px(3) - 0.2, y: y2 - 0.28, w: 4 * dx + 0.4, h: 0.56, rectRadius: 0.28, fill: { color: "FBE3D7" }, line: { color: ACC, width: 1.5 } });
  s.addShape(pres.shapes.LINE, { x: px(cur), y: 1.95, w: 0, h: 2.45, line: { color: ACCD, width: 1.5, dashType: "dash" } });
  for (let i = 0; i <= 10; i++) {
    const fut = i > cur;
    s.addShape(pres.shapes.OVAL, { x: px(i) - 0.1, y: y1 - 0.1, w: 0.2, h: 0.2, fill: { color: fut ? BG : "3D4756" }, line: { color: fut ? "9AA3AF" : "3D4756", width: 1.5 } });
    s.addShape(pres.shapes.OVAL, { x: px(i) - 0.1, y: y2 - 0.1, w: 0.2, h: 0.2, fill: { color: "3D4756" }, line: { color: "3D4756" } });
  }
  T(s, "현재", { x: px(cur) - 0.6, y: 1.65, w: 1.2, h: 0.3, fontSize: 13, bold: true, color: ACCD, align: "center" });
  T(s, "실시간(인과) 필터", { x: 0.7, y: y1 - 0.35, w: 2.9, h: 0.35, fontSize: 16, bold: true, color: NAVY });
  T(s, "과거 샘플 5개 평균", { x: 0.7, y: y1 + 0.02, w: 2.9, h: 0.3, fontSize: 13, color: MUTE });
  T(s, "출력 = 2샘플 전 값 → 지연", { x: px(1) - 0.2, y: y1 + 0.35, w: 4 * dx + 0.4, h: 0.3, fontSize: 13, bold: true, color: BLUE, align: "center" });
  T(s, "미래 샘플 (아직 없음)", { x: px(6), y: y1 + 0.35, w: 3.2, h: 0.3, fontSize: 13, color: MUTE });
  T(s, "사후(비인과) 필터", { x: 0.7, y: y2 - 0.35, w: 2.9, h: 0.35, fontSize: 16, bold: true, color: NAVY });
  T(s, "앞뒤 샘플 5개 평균", { x: 0.7, y: y2 + 0.02, w: 2.9, h: 0.3, fontSize: 13, color: MUTE });
  T(s, "출력 = 현재 값 → 지연 0", { x: px(3) - 0.2, y: y2 + 0.35, w: 4 * dx + 0.4, h: 0.3, fontSize: 13, bold: true, color: ACCD, align: "center" });
  [[0.7, "실시간 필터", BLUE, "위상 지연 발생 (예: 10 Hz 2차 Butterworth ≈ 30 ms)"], [6.75, "사후 필터", ACCD, "지연 0, 단 측정 완료 후에만 가능 → 실시간 제어 불가"]].forEach(([x, h, c, d]) => {
    card(s, x, 4.85, 5.88, 1.15);
    T(s, h, { x: x + 0.25, y: 4.95, w: 5.4, h: 0.3, fontSize: 13, bold: true, color: c });
    T(s, d, { x: x + 0.25, y: 5.3, w: 5.4, h: 0.65, fontSize: 15, color: NAVY });
  });
  card(s, 0.7, 6.2, 11.93, 0.6, { fill: "FFFFFF", line: ACC, lw: 1.5 });
  T(s, "문제: ‘얼마나 기다리면 충분한가’에 대한 정량 기준이 없다", { x: 0.95, y: 6.2, w: 11.4, h: 0.6, fontSize: 16, bold: true, color: NAVY, valign: "middle" });
}

// 4 연구목적
{
  const s = slide(BG2, "연구목적", "‘허용 지연’을 기준으로 최적 필터를 정한다", "출처: Rauch, Tung, Striebel, AIAA J. 3(8), 1965 (고정지연 · RTS 스무더)");
  card(s, 0.7, 1.95, 4.6, 2.6);
  T(s, "문제 정의", { x: 0.95, y: 2.1, w: 4.1, h: 0.3, fontSize: 13, bold: true, color: BLUE });
  T(s, "필터 지연을 얼마까지 허용해야 사후 필터 수준의 정확도를 얻는가?", { x: 0.95, y: 2.5, w: 4.1, h: 1.9, fontSize: 20, bold: true, color: NAVY });
  s.addShape(pres.shapes.RIGHT_ARROW, { x: 5.42, y: 3.0, w: 0.5, h: 0.4, fill: { color: ACC }, line: { color: ACC } });
  card(s, 6.05, 1.95, 6.58, 2.6, { fill: PEACH, line: ACC, lw: 2.5 });
  T(s, "해결 방법", { x: 6.3, y: 2.1, w: 6, h: 0.3, fontSize: 13, bold: true, color: ACCD });
  T(s, [{ text: "허용 지연 d", options: { bold: true } }, { text: "를 독립변수로 둔 " }, { text: "고정지연 필터", options: { bold: true } }, { text: ": d만큼 기다려 미래 샘플을 활용" }], { x: 6.3, y: 2.5, w: 6.1, h: 1.1, fontSize: 18, color: NAVY });
  pill(s, 6.3, 3.85, 1.9, "d = 0 · 실시간");
  pill(s, 8.3, 3.85, 2.25, "0 < d < ∞ · 고정지연", { fill: ACC, color: "FFFFFF", bold: true });
  pill(s, 10.65, 3.85, 1.8, "d = ∞ · 사후");
  card(s, 0.7, 4.85, 11.93, 1.75);
  T(s, "차별점", { x: 0.95, y: 5.0, w: 4, h: 0.3, fontSize: 13, bold: true, color: ACCD });
  T(s, "기존: 필터 ‘종류’ 비교 중심 → 본 연구: 필터 ‘시점(허용 지연)’을 축으로 같은 데이터에서 정량 비교\n+ 센서 내부 AAF(Anti-Aliasing Filter, 앨리어싱 방지 필터) 효과까지 포함", { x: 0.95, y: 5.4, w: 11.4, h: 1.1, fontSize: 16, color: TXT, paraSpaceAfter: 6 });
}

// 5 연구내용 1: 흐름도
{
  const s = slide(BG, "연구내용 1 · 연구 흐름도", "측정 → 실시간 · 사후 필터 → 지연–정확도 평가", "모든 필터 조건을 같은 데이터에 적용 · 단일 클럭 동기화(STM32 + 동기 LED)");
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
  pill(s, 4.85, 5.6, 3.6, "인체 보행: 3–5명 · 트레드밀 3속도");
  pill(s, 8.65, 5.6, 3.75, "임베디드: Arduino vs STM32 연산 비용");
}

// 6 연구내용 2: 적용 방법
{
  const s = slide(BG, "연구내용 2 · 적용 방법", "수업에서 다룬 필터를 세 처리 시점으로 확장한다", "출처: Casiez et al., CHI 2012 (1€ 필터) · Rauch et al., AIAA J. 1965 (RTS)");
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
  const s = slide(BG, "연구내용 3", "진행 현황 및 향후 일정");
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
  const s = slide(BG2, "기대효과", "실시간 보행 보조를 위한 필터 설계 기준을 제공한다");
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

// 9 결언
{
  const s = slide(NAVY, "결언", "요약", null, true);
  ["사전/사후의 본질적 차이는 계산 시점이 아니라 미래 샘플 사용(허용 지연)이다", "허용 지연을 축으로 실시간 · 고정지연 · 사후 필터를 같은 데이터에서 비교한다", "실시간 보행 보조를 위한 필터 선택 기준을 제시한다"].forEach((t, i) => {
    const y = 1.95 + i * 0.8;
    T(s, String(i + 1), { x: 0.7, y, w: 0.5, h: 0.6, fontSize: 22, bold: true, color: ORL, fontFace: M });
    T(s, t, { x: 1.3, y, w: 11.3, h: 0.7, fontSize: 20, color: CREAM });
  });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.7, y: 4.55, w: 11.93, h: 1.0, rectRadius: 0.1, fill: { color: "22304A" }, line: { color: "22304A" } });
  T(s, "조언 요청: 100 Hz 영상 참값의 시간 해상도(±10 ms)가 비교할 지연 차이와 비슷함 → 참값 정밀도를 높일 방법", { x: 0.95, y: 4.55, w: 11.4, h: 1.0, fontSize: 16, color: CREAM, valign: "middle" });
  T(s, "감사합니다 · 질의응답", { x: 0.7, y: 6.0, w: 9, h: 0.6, fontSize: 26, bold: true, color: CREAM });
}

pres.writeFile({ fileName: OUT }).then(() => console.log("written", OUT));
