// 대회 당일엔 이 파일만 고치면 된다.
// - 등장인물·단계·지표 이름을 실제 문제에 맞게 바꾸고
// - SCRIPT 의 이벤트를 실제 에이전트 실행 로그로 바꾸거나, 브라우저 콘솔에서 OFFICE.push({...}) 로 흘려 넣는다.
// 이미지: assets/ 폴더에 같은 이름 파일이 있으면 그걸 쓰고, 없으면 cdn 주소(힉스필드 생성본)를 쓴다.

const CDN = "https://d8j0ntlcm91z4.cloudfront.net/user_3CcgVfpOILliMlFGtPT4VAEt7Ab/hf_20261002_023338_";

window.OFFICE_DATA = {
  title: "교동·갯마을 AX 오피스",
  subtitle: "조합 업무 자동화 에이전트 관제실",
  scene: { local: "assets/village.png", cdn: CDN + "ca41f431-6d5d-43d4-94d1-80d2c931a5a6.png" },

  // 장면 위 핫스팟 위치(%) — 배경 그림을 바꾸면 좌표만 다시 맞춘다
  people: [
    { id: "farm",  name: "김영식", role: "교동농협 조합장", village: "교동", x: 22, y: 58,
      img: { local: "assets/farm.png",  cdn: CDN + "3e888f5a-109c-4cbc-89af-ea5d3c39fae4.png" } },
    { id: "sea",   name: "박순자", role: "갯마을 어촌계장", village: "갯마을", x: 78, y: 60,
      img: { local: "assets/sea.png",   cdn: CDN + "30aed728-0b51-4a5a-99b8-e0b69a95769f.png" } },
    { id: "clerk", name: "이준호", role: "조합 사무장",     village: "공동", x: 38, y: 74,
      img: { local: "assets/clerk.png", cdn: CDN + "a24c8688-842e-429a-bf0d-80af42916151.png" } },
    { id: "agent", name: "AX-01", role: "조합 업무 에이전트", village: "허브", x: 50, y: 46, isAgent: true,
      img: { local: "assets/agent.png", cdn: CDN + "2ecd012f-fe1e-4566-bb7c-63813aef2fea.png" } },
  ],

  // 수집 → 검증 → 정제 → 실행 (미션 브리프의 흐름 그대로)
  stages: [
    { id: "collect",  label: "수집", desc: "인터뷰·장부·영수증" },
    { id: "validate", label: "검증", desc: "출처·이상치·중복" },
    { id: "refine",   label: "정제", desc: "단위·품목명 통일" },
    { id: "act",      label: "실행", desc: "에이전트 자동 처리" },
  ],

  kpis: [
    { id: "records", label: "처리한 기록", unit: "건", value: 0 },
    { id: "fixed",   label: "바로잡은 오류", unit: "건", value: 0 },
    { id: "saved",   label: "아낀 업무 시간", unit: "시간/주", value: 0 },
    { id: "acc",     label: "검증 통과율", unit: "%", value: 0 },
  ],

  // 시연용 각본. t = 시작 후 초. kpi 는 더할 값(acc 는 덮어쓸 값).
  SCRIPT: [
    { t: 1,  who: "clerk", stage: "collect",  text: "출하 장부 3개월치, 엑셀 4개로 흩어져 있어요.", kind: "talk" },
    { t: 3,  who: "agent", stage: "collect",  text: "장부 4개 · 영수증 사진 212장 수집 완료", kpi: { records: 212 } },
    { t: 5,  who: "farm",  stage: "collect",  text: "사과는 '관', 배는 '상자'로 적어서 합계가 안 맞아.", kind: "talk" },
    { t: 7,  who: "agent", stage: "validate", text: "중복 거래 17건 · 단가 이상치 6건 발견", kpi: { fixed: 23 }, level: "warn" },
    { t: 9,  who: "sea",   stage: "collect",  text: "경매 시세는 매일 아침 칠판에만 적어요.", kind: "talk" },
    { t: 11, who: "agent", stage: "collect",  text: "칠판 사진 OCR → 위판 시세표 38일치 생성", kpi: { records: 38 } },
    { t: 13, who: "agent", stage: "validate", text: "출처 교차검증: 공판장 공시가와 오차 1.2% 이내", kpi: { acc: 96 } },
    { t: 15, who: "agent", stage: "refine",   text: "단위 통일: 관·상자·근 → kg (환산표 적용)", kpi: { fixed: 41 } },
    { t: 17, who: "agent", stage: "refine",   text: "품목명 통일: '고등어(대)', '고딩어' → 고등어", kpi: { fixed: 9 } },
    { t: 19, who: "agent", stage: "act",      text: "주간 출하·위판 정산서 자동 작성", kpi: { saved: 6 }, level: "ok" },
    { t: 21, who: "agent", stage: "act",      text: "제철 알림: 다음 주 사과·전어 출하 피크 예상", kpi: { saved: 2 }, level: "ok" },
    { t: 23, who: "clerk", stage: "act",      text: "금요일 야근이 없어졌어요!", kind: "talk" },
    { t: 25, who: "agent", stage: "validate", text: "최종 검증 통과율", kpi: { acc: 99 }, level: "ok" },
  ],

  // 하단 차트: 주간 처리량(건) — 실제 데이터로 바꿔 쓴다
  trend: {
    label: "주간 정산 소요 시간 (시간)",
    before: [9, 10, 8.5, 11, 9.5, 10, 12, 9],
    after:  [9, 8, 5,   3,  2.5, 2,  1.5, 1],
    weeks:  ["1주", "2주", "3주", "4주", "5주", "6주", "7주", "8주"],
  },
};
