// =====================================================================
//  정강이 모사 벤치 리그 (Shank Swing Rig) + 필터 비교 바늘 표시기
//  - 서보 1개가 정강이 모사 암을 보행 패턴으로 흔든다
//  - 암 끝이 스토퍼에 부딪혀 HS(뒤꿈치 닿기) 충격을 만든다
//  - 암 뒷면의 코인 진동모터로 고주파 진동(앨리어싱 실험)을 준다
//  - 표시기: 마이크로 서보 2개 바늘(RAW / FILTERED)로 흔들림을 눈으로 비교
//
//  사용법: PART 값을 바꿔 부품별로 STL 출력
//    openscad -D 'PART="arm"' -o stl/arm.stl rig.scad
//  좌표: x = 앞(암이 앞으로 흔들리는 방향), y = 깊이(+y 쪽에 암), z = 위
//        베이스 윗면 z = 0, 타워 앞면 y = 0, 서보 축 (x, z) = (0, H)
//  치수 단위: mm.  ★ 표시는 가진 부품을 캘리퍼로 재서 맞출 값
// =====================================================================

PART = "assembly";   // assembly | base | tower | arm | stopper | display | needle | print_layout
$fn = 72;

// ---------- 표준형 서보 (MG996R 크기 계열) ----------
SV_L = 41.0;          // ★ 몸체 길이 + 여유
SV_W = 20.4;          // ★ 몸체 폭 + 여유
SV_HOLE_DX = 49.5;    // ★ 플랜지 나사 구멍 간격 (길이 방향)
SV_HOLE_DY = 10.0;    // ★ 플랜지 나사 구멍 간격 (폭 방향)
SV_HOLE_D = 3.4;      // M3
SV_SHAFT_OFF = 10.2;  // ★ 몸체 중심 → 출력축 거리 (길이 방향)

// ---------- 마이크로 서보 (SG90 계열, 바늘용) ----------
MS_L = 23.2; MS_W = 12.8;
MS_HOLE_DX = 27.8; MS_HOLE_D = 2.2;
MS_SHAFT_OFF = 5.9;   // ★

// ---------- 리그 주요 치수 ----------
H = 170;          // 베이스 윗면 → 서보 축 높이
ARM_L = 130;      // 축 → 암 끝(범퍼 면)
IMU_R = 70;       // 축 → IMU 포켓 중심
VIB_R = 105;      // 축 → 진동모터 포켓 중심
ARM_T = 6;        // 암 두께
ARM_W = 16;       // 암 폭
IMU_PAD_W = 30;   // IMU 부분 암 폭
ARM_Y = 26;       // ★ 타워 앞면 → 암 중심면 (서보 윗면 + 혼 높이에 맞춰 조정)

T_W = 190;        // 타워 폭
T_TH = 6;         // 타워 두께
T_TOP = 28;       // 축 위 여유 높이
FOOT_BACK = 40;   // 뒤쪽 발 깊이
FOOT_T = 6;

BASE_L = 210; BASE_T = 6;
BASE_Y0 = -T_TH - FOOT_BACK - 6;      // 베이스 뒤 끝
BASE_Y1 = ARM_Y + 46;                  // 베이스 앞 끝
SLOT_X0 = 22; SLOT_X1 = 98;            // 스토퍼 슬롯 범위 (|x|)

// GY-521 (MPU-6050 보드)
GY_L = 21.6; GY_W = 16.6; GY_DEPTH = 1.4;   // ★ 보드 크기 + 여유
// 코인 진동모터
VM_D = 10.6; VM_DEPTH = 3.2;                 // ★
// 서보 혼 (원형 혼 자리, 0이면 생략)
HORN_D = 25.6; HORN_DEPTH = 2.0;             // ★

DIAL_R0 = 92; DIAL_R1 = 104; DIAL_R2 = 109;  // 눈금 안/짧은/긴 반지름
DIAL_A = 60;                                  // 눈금 범위 ±60°
ENGRAVE = 0.8;
FONT = "Liberation Sans:style=Bold";

M3 = 3.4;

// =====================================================================
// 공용
// =====================================================================
module servo_cut(L, W, dx, dy, hd, off, t) {
  // 축이 원점에 오도록 몸체를 off만큼 +x로 이동
  translate([off, 0, 0]) {
    cube([L, W, t * 3], center = true);
    for (sx = [-1, 1]) for (sy = (dy > 0 ? [-1, 1] : [0]))
      translate([sx * dx / 2, sy * dy / 2, 0]) cylinder(d = hd, h = t * 3, center = true);
  }
}

// 각도 눈금 (2D). 0° = 아래 방향. 2D 각 b의 눈금에 str(sgn*b) 라벨
// 앞면 음각은 front_engrave()로 감싸 정면(+y)에서 보았을 때 글자가 바로 읽히게 한다.
// 정면에서 보면 월드 +x(앞 스윙)는 관찰자 왼쪽이므로, 타워 눈금은 sgn = -1.
module dial_2d(r0, r1, r2, amax, step = 5, label_step = 10, label_r = 0, fs = 6, sgn = 1) {
  for (a = [-amax : step : amax]) {
    long = (a % label_step == 0);
    w = long ? 1.4 : 0.8;
    rotate(a) translate([-w / 2, -(long ? r2 : r1)]) square([w, (long ? r2 : r1) - r0]);
  }
  // 바깥 호
  difference() {
    intersection() { circle(r = r0 + 0.8); arc_wedge(amax, r2 + 2); }
    circle(r = r0);
  }
  if (label_r > 0)
    for (a = [-amax : label_step : amax])
      rotate(a) translate([0, -label_r]) rotate(-a)
        text(str(sgn * a), size = fs, font = FONT, halign = "center", valign = "center");
}
// 2D(u=관찰자 오른쪽, v=위)를 y=0 앞면에 depth만큼 음각. 월드 x = -u
module front_engrave(depth) {
  translate([0, 0.01, 0]) rotate([90, 0, 0]) mirror([1, 0, 0]) linear_extrude(depth + 0.01) children();
}
module arc_wedge(amax, r) {
  polygon(concat([[0, 0]], [for (a = [-amax : 2 : amax]) [r * sin(a), -r * cos(a)]]));
}

module slot_2d(x0, x1, w) { hull() { translate([x0, 0]) circle(d = w); translate([x1, 0]) circle(d = w); } }

// =====================================================================
// 1) 베이스
// =====================================================================
module base() {
  difference() {
    translate([-BASE_L / 2, BASE_Y0, -BASE_T]) cube([BASE_L, BASE_Y1 - BASE_Y0, BASE_T]);
    // 타워 고정 구멍 (뒤 발 2곳)
    for (x = [-70, 70]) translate([x, -T_TH - FOOT_BACK / 2, -BASE_T]) cylinder(d = M3, h = 20, center = true);
    // 스토퍼 슬롯 (앞/뒤 스윙 양쪽)
    for (s = [-1, 1]) translate([0, ARM_Y, -BASE_T - 1]) linear_extrude(BASE_T + 2)
      if (s > 0) slot_2d(SLOT_X0, SLOT_X1, M3); else slot_2d(-SLOT_X1, -SLOT_X0, M3);
    // 슬롯 옆 눈금 (스토퍼 위치 기록용, 10 mm 간격)
    for (x = [SLOT_X0 : 10 : SLOT_X1]) for (s = [-1, 1])
      translate([s * x - 0.4, ARM_Y + 6, -ENGRAVE]) cube([0.8, 5, 2]);
    // 고무발 자리
    for (x = [-BASE_L / 2 + 10, BASE_L / 2 - 10]) for (y = [BASE_Y0 + 10, BASE_Y1 - 10])
      translate([x, y, -BASE_T - 0.01]) cylinder(d = 10.5, h = 1.0);
    // 클램프 고정용 양끝 슬롯
    for (s = [-1, 1]) translate([s * (BASE_L / 2 - 8), (BASE_Y0 + BASE_Y1) / 2, -BASE_T - 1])
      linear_extrude(BASE_T + 2) rotate(90) slot_2d(-15, 15, 4.5);
    // 라벨
    translate([0, BASE_Y1 - 9, -ENGRAVE]) linear_extrude(2) rotate(180)   // 앞(+y)에서 읽히게
      text("SHANK SWING RIG", size = 6, font = FONT, halign = "center", valign = "center");
  }
}

// =====================================================================
// 2) 타워 (서보 고정 + 각도 눈금판 일체형). 인쇄: 앞면을 베드에
// =====================================================================
module tower() {
  difference() {
    union() {
      // 판
      translate([-T_W / 2, -T_TH, 0]) cube([T_W, T_TH, H + T_TOP]);
      // 뒤 발 (앞면은 평평하게 두어 앞면을 베드에 놓고 인쇄)
      translate([-T_W / 2, -T_TH - FOOT_BACK, 0]) cube([T_W, FOOT_BACK, FOOT_T]);
      // 보강 리브 (뒤쪽 3개)
      for (x = [-T_W / 2, -3, T_W / 2 - 6])
        translate([x, -T_TH, 0]) rotate([90, 0, 90]) linear_extrude(6)
          polygon([[0, 0], [-FOOT_BACK, 0], [-FOOT_BACK, FOOT_T], [0, H - 30]]);
      // 서보 주변 보강 (뒤쪽 테두리)
      translate([SV_SHAFT_OFF, -T_TH - 5, H]) difference() {
        cube([SV_HOLE_DX + 12, 10, SV_W + 14], center = true);
        cube([SV_L, 12, SV_W], center = true);
      }
    }
    // 서보 컷아웃 (축 = (0, H))
    translate([0, -T_TH / 2, H]) rotate([90, 0, 0])
      servo_cut(SV_L, SV_W, SV_HOLE_DX, SV_HOLE_DY, SV_HOLE_D, SV_SHAFT_OFF, 40);
    // 베이스 고정 구멍
    for (x = [-70, 70]) translate([x, -T_TH - FOOT_BACK / 2, 0]) cylinder(d = M3, h = 30, center = true);
    // 앞면 각도 눈금 + 라벨 (음각, 정면에서 읽힘)
    front_engrave(ENGRAVE) {
      translate([0, H]) dial_2d(DIAL_R0, DIAL_R1, DIAL_R2, DIAL_A, 5, 10, DIAL_R0 - 9, 5.5, -1);
      translate([0, H + T_TOP - 10]) text("deg   (+ = forward swing)", size = 5, font = FONT, halign = "center");
      translate([0, 14]) text("<- FORWARD (HS side)", size = 5, font = FONT, halign = "center");
    }
    // 배선 구멍 (진동모터·IMU 선을 뒤로 넘김)
    translate([T_W / 2 - 14, 0, H + 8]) rotate([90, 0, 0]) cylinder(d = 8, h = 30, center = true);
  }
}

// =====================================================================
// 3) 정강이 모사 암.  원점 = 서보 축, 암은 -y(2D) 방향으로 늘어짐
//    앞면(+z, 인쇄 시 윗면) = IMU 포켓, 뒷면(z=0, 베드) = 혼 자리·진동모터
// =====================================================================
module arm_2d() {
  hull() { circle(d = 34); translate([0, -IMU_R + 20]) square([ARM_W, 1], center = true); }
  translate([-ARM_W / 2, -ARM_L + ARM_W / 2]) square([ARM_W, ARM_L - ARM_W / 2]);
  translate([0, -IMU_R]) square([IMU_PAD_W, GY_L + 14], center = true);
  translate([0, -VIB_R]) circle(d = VM_D + 7);
  // 끝 범퍼(HS 충격면): 양옆 납작한 면
  translate([0, -ARM_L + 9]) square([ARM_W + 6, 18], center = true);
}
module arm() {
  difference() {
    linear_extrude(ARM_T) arm_2d();
    // 혼 중심 구멍 + 방사형 슬롯 (혼 나사 M2, 여러 혼 대응)
    translate([0, 0, -1]) cylinder(d = 8.2, h = ARM_T + 2);
    for (a = [0 : 45 : 315]) rotate(a) translate([0, 0, -1])
      linear_extrude(ARM_T + 2) slot_2d(5.5, 11.5, 2.2);
    if (HORN_D > 0) translate([0, 0, -0.01]) cylinder(d = HORN_D, h = HORN_DEPTH);
    // IMU 포켓 (보드 긴 변 = 암 길이 방향), 핀 헤더 쪽 홈
    translate([0, -IMU_R, ARM_T - GY_DEPTH]) cube([GY_W, GY_L, GY_DEPTH * 2], center = true);
    translate([GY_W / 2 - 1.5, -IMU_R, ARM_T - 2.6]) cube([3, GY_L, 3], center = true);
    // 테이프/결속용 중앙 관통 구멍 + 케이블타이 슬롯
    translate([0, -IMU_R, -1]) cylinder(d = 5, h = ARM_T + 2);
    for (s = [-1, 1]) translate([s * (IMU_PAD_W / 2 - 3.2), -IMU_R, -1])
      linear_extrude(ARM_T + 2) square([2.6, 5], center = true);
    // 진동모터 포켓(뒷면) + 선 홈
    translate([0, -VIB_R, -0.01]) cylinder(d = VM_D, h = VM_DEPTH);
    translate([0, -VIB_R + 10, 0.8]) cube([2.4, 16, 2], center = true);
    // 케이블타이 슬롯 (축 근처)
    for (s = [-1, 1]) translate([s * (ARM_W / 2 - 2.5), -32, -1]) linear_extrude(ARM_T + 2) square([2.4, 4.5], center = true);
    // 중심선 + 화살표 (앞면 음각): 눈금판 읽기, IMU X축 방향 표시
    translate([0, -40, ARM_T - ENGRAVE]) linear_extrude(2) square([0.9, 50], center = true);
    translate([0, -IMU_R - GY_L / 2 - 4.5, ARM_T - ENGRAVE]) linear_extrude(2)
      polygon([[-3, 2], [3, 2], [0, -3]]);
    translate([0, -ARM_L + 9, ARM_T - ENGRAVE]) linear_extrude(2)
      text("HS", size = 6, font = FONT, halign = "center", valign = "center");
  }
}

// =====================================================================
// 4) 스토퍼 (HS 충격 모사). 슬롯을 따라 위치 조절, 고무 패드 부착
// =====================================================================
STOP_H = 75;
module stopper() {
  difference() {
    union() {
      translate([-18, -14, 0]) cube([36, 28, 5]);          // 발
      translate([0, -12, 0]) cube([14, 24, STOP_H]);       // 기둥 (충격면 x=0, -x 쪽을 향함)
      translate([14, -12, 0]) rotate([90, 0, 0]) mirror([0, 0, 1]) linear_extrude(24)
        polygon([[0, 0], [0, 40], [14, 0]]);               // 뒤 보강
    }
    translate([-10, 0, -1]) linear_extrude(8) slot_2d(-4, 4, M3);   // 고정 나사 슬롯
    translate([-0.01, -10, 20]) cube([1.6, 20, STOP_H - 26]);      // 고무 패드 자리
  }
}

// =====================================================================
// 5) 바늘 표시기 (마이크로 서보 2개). 인쇄: 앞면을 베드에
// =====================================================================
D_W = 200; D_H = 85; D_T = 5; D_SH = 24;  // 축 높이(판 바닥 기준)
D_X = 52;                                   // 두 바늘 축 x 위치 ±
D_R0 = 38; D_R1 = 44; D_R2 = 48;
module display() {
  difference() {
    union() {
      translate([-D_W / 2, -D_T, 0]) cube([D_W, D_T, D_H]);
      translate([-D_W / 2, -D_T - 45, 0]) cube([D_W, 45, 5]);
      for (x = [-D_W / 2, -3, D_W / 2 - 6]) translate([x, -D_T, 0]) rotate([90, 0, 90])
        linear_extrude(6) polygon([[0, 0], [-45, 0], [-45, 5], [0, 55]]);
    }
    for (s = [-1, 1]) {
      translate([s * D_X, -D_T / 2, D_SH]) rotate([90, 0, 0])
        servo_cut(MS_L, MS_W, MS_HOLE_DX, 0, MS_HOLE_D, MS_SHAFT_OFF, 20);
    }
    // 위쪽 반원 눈금 (0°=위, +는 관찰자 오른쪽=시계방향) + 라벨 (정면에서 읽힘)
    front_engrave(ENGRAVE) for (u = [-D_X, D_X]) translate([u, D_SH]) {
      rotate(180) dial_2d(D_R0, D_R1, D_R2, 60, 10, 30, 0);
      for (a = [-60 : 30 : 60]) rotate(-a) translate([0, D_R0 - 7]) rotate(a)
        text(str(a), size = 5, font = FONT, halign = "center", valign = "center");
    }
    front_engrave(ENGRAVE) {
      translate([-D_X, 6]) text("RAW", size = 7, font = FONT, halign = "center");
      translate([D_X, 6]) text("FILTERED", size = 7, font = FONT, halign = "center");
    }
    for (x = [-70, 70]) translate([x, -D_T - 25, 0]) cylinder(d = M3, h = 20, center = true);
  }
}
NEEDLE_L = 44;
module needle() {
  difference() {
    linear_extrude(2.4) hull() { circle(d = 11); translate([0, NEEDLE_L]) circle(d = 1.4); }
    translate([0, 0, -1]) cylinder(d = 2.4, h = 5);
    // 1자 혼 자리 (뒷면)
    translate([0, 0, -0.01]) linear_extrude(1.4) hull() { circle(d = 7.4); translate([0, 15]) circle(d = 4.4); }
  }
}

// =====================================================================
// 조립 / 출력 배치
// =====================================================================
SWING = 15;  // 조립 미리보기 각도
module assembly() {
  color("#cfd6de") base();
  color("#8fa7c4") tower();
  // 서보 (참고용 형상)
  color("#333") translate([SV_SHAFT_OFF, 4, H]) cube([SV_L - 0.8, 28, SV_W - 0.4], center = true);
  // 암: 2D 아래 방향(-y) → 3D -z, 앞면(+z) → +y
  // 암 로컬 좌표: 아래(-y) → 월드 -z, 앞면(+z) → 월드 +y
  color("#e07a4f") translate([0, ARM_Y - ARM_T / 2, H]) rotate([0, -SWING, 0])
    rotate([0, 180, 0]) rotate([-90, 0, 0]) arm();
  color("#3a7d44") translate([0, ARM_Y + 2.2, H]) rotate([0, -SWING, 0]) translate([0, 0, -IMU_R])
    cube([GY_W - 0.6, 1.6, GY_L - 0.6], center = true);
  // 스토퍼: 충격면이 +20° 근처
  color("#999") translate([ARM_L * sin(20) + ARM_W / 2 + 4, ARM_Y, 0]) stopper();
  // 표시기
  translate([0, -170, 0]) {
    color("#8fa7c4") display();
    for (s = [-1, 1]) color("#e07a4f") translate([s * D_X, 4, D_SH]) rotate([90, 0, 0])
      rotate(s > 0 ? -25 : 18) needle();
  }
}

module print_layout() {
  base();
}

if (PART == "assembly") assembly();
else if (PART == "base") translate([0, 0, BASE_T]) base();
else if (PART == "tower") rotate([-90, 0, 0]) tower();          // 앞면(y=0)이 베드(z=0)로
else if (PART == "arm") arm();
else if (PART == "stopper") stopper();
else if (PART == "display") rotate([-90, 0, 0]) display();
else if (PART == "needle") needle();
else if (PART == "tower_front") tower();
else if (PART == "display_front") display();
