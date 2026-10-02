# 인수인계 — 클라우드 세션 → PC 로컬 세션

> 작성: 2026-10-02 · 브랜치 `claude/ai-top-100-prep-xdqiq8` · 폴더 `ai-top-100/`
> 이 문서만 읽으면 앞선 대화를 몰라도 이어서 작업할 수 있게 정리했다.

---

## 0. PC에서 이어서 하는 법 (3단계)

```bash
cd <book-shelf 폴더>
git fetch origin claude/ai-top-100-prep-xdqiq8
git checkout claude/ai-top-100-prep-xdqiq8
```

그다음 Claude Code(데스크톱 앱 또는 터미널)를 이 폴더에서 열고 **아래 프롬프트를 그대로 붙여넣는다.**

```
ai-top-100/HANDOFF.md 를 먼저 읽고 이어서 작업해줘.
1) C:\Users\kkari\Downloads\AI 100 폴더의 지난 대회 문제를 전부 읽고
   문제별로 유형·입력 데이터·요구 답·함정·좋은 풀이 전략을 ai-top-100/problems/분석.md 로 정리해줘.
2) 그 분석을 바탕으로 ai-top-100/README.md 의 '예상 함정' 표와 toolkit/ 을 보강해줘.
3) 사내 대시보드 http://192.168.30.91:8080/ 의 AI 오피스 화면을 보고,
   village-office/ 디자인을 그보다 세련되게 다듬어줘.
4) https://brunch.co.kr/@andkakao/323 같은 후기 글도 읽고 반영해줘.
```

---

## 1. 목표 (사용자 요청 원문 요약)

- **AI_TOP_100 [2026] 예선** 참가 (참가자: 이재호 님)
  - 예선 2026-10-31(토) 10:00~15:00 온라인, 문제 페이지 09:00 오픈, **사전 준비 약 20분 — 시작 전 미완료 시 실격**
  - 사전 안내 메일 10/23(금), 본선 11/21(토)
- 미션 브리프: 제철 농산물 **'교동마을'** + 수산물 **'갯마을'**. AX 전문가로서 마을 관계자와 **대화해 문제를 발굴**하고, 데이터를 **수집·검증·정제**해서 두 마을 조합 업무를 개선할 **AI 에이전트**를 만든다.
- 요청 사항
  1. 사전에 준비·작업할 것을 검토해서 모아 줄 것
  2. 경연이라 **비주얼이 중요** — 사내 대시보드(`http://192.168.30.91:8080/`)의 "AI 오피스"처럼, 더 세련되게 만들 것
  3. 필요하면 **힉스필드(Higgsfield)** 로 에셋 생성
  4. 지난 대회 예선 문제 학습 (→ 클라우드에서는 못 함, §4)

---

## 2. 지금까지 만든 것 (모두 이 브랜치에 커밋·푸시됨)

| 경로 | 내용 | 상태 |
|---|---|---|
| `ai-top-100/README.md` | 준비 체크리스트: 확인된 사실 / 10/23 메일에서 확인할 것, 날짜별 일정, 장비·계정, 미션별 포인트·예상 함정 표, 오피스 화면 사용법, 힉스필드 에셋 목록, 당일 5시간 시간표, 참고 링크 | 완료 |
| `ai-top-100/village-office/index.html` | "교동·갯마을 AX 오피스" 관제 화면. 마을 장면 + 관계자 말풍선 + 에이전트 이동, 수집→검증→정제→실행 파이프라인, KPI 카운터, 현장 로그, 도입 전/후 차트. 데스크톱·모바일 스크린샷 확인 완료 | 완료 (디자인은 사내 대시보드 미참고) |
| `ai-top-100/village-office/data.js` | 화면 내용 전부(인물·좌표·단계·지표·25초 시연 각본·차트 값). **당일엔 이 파일만 수정** | 예시 데이터 |
| `ai-top-100/toolkit/clean.py` | 날짜·품목명·단위(→kg) 통일, 중복 제거, 품목별 단가 이상치 탐지, 정제 보고. `python clean.py --demo` 로 동작 확인됨 | 환산값은 **예시** — 당일 기준으로 교체 필요 |
| `ai-top-100/toolkit/agent_prompt.md` | 관계자 인터뷰 질문 7개 + 기록표, 에이전트 시스템 프롬프트 틀, 제출 전 검증 루틴 | 완료 |

화면 기능 메모
- 브라우저 콘솔에서 `OFFICE.push({who:"agent", stage:"validate", text:"...", kpi:{fixed:3}, level:"warn"})` 로 실시간 이벤트 주입 가능
- `Space` = 일시정지, 이미지는 `assets/파일` → 없으면 CDN → 없으면 이니셜 순으로 대체

---

## 3. 힉스필드 에셋 (2026-10-02 생성, nano_banana_2)

생성 직후 크레딧 잔액은 약 915였다(생성 전 조회값). 컨테이너에서는 CDN 다운로드가 막혀 **아직 `assets/` 에 저장 안 됨** → PC에서 내려받아 `ai-top-100/village-office/assets/` 에 아래 이름으로 저장할 것.

| 저장 이름 | 내용 | URL |
|---|---|---|
| `village.png` | 교동+갯마을 아이소메트릭 배경 21:9 | https://d8j0ntlcm91z4.cloudfront.net/user_3CcgVfpOILliMlFGtPT4VAEt7Ab/hf_20261002_023338_ca41f431-6d5d-43d4-94d1-80d2c931a5a6.png |
| `farm.png` | 교동농협 조합장 | https://d8j0ntlcm91z4.cloudfront.net/user_3CcgVfpOILliMlFGtPT4VAEt7Ab/hf_20261002_023338_3e888f5a-109c-4cbc-89af-ea5d3c39fae4.png |
| `sea.png` | 갯마을 어촌계장 | https://d8j0ntlcm91z4.cloudfront.net/user_3CcgVfpOILliMlFGtPT4VAEt7Ab/hf_20261002_023338_30aed728-0b51-4a5a-99b8-e0b69a95769f.png |
| `clerk.png` | 조합 사무장 | https://d8j0ntlcm91z4.cloudfront.net/user_3CcgVfpOILliMlFGtPT4VAEt7Ab/hf_20261002_023338_a24c8688-842e-429a-bf0d-80af42916151.png |
| `agent.png` | AI 에이전트 로봇 | https://d8j0ntlcm91z4.cloudfront.net/user_3CcgVfpOILliMlFGtPT4VAEt7Ab/hf_20261002_023338_2ecd012f-fe1e-4566-bb7c-63813aef2fea.png |

PowerShell 한 번에 내려받기:

```powershell
$base = "https://d8j0ntlcm91z4.cloudfront.net/user_3CcgVfpOILliMlFGtPT4VAEt7Ab/hf_20261002_023338_"
$dir  = "ai-top-100\village-office\assets"; New-Item -ItemType Directory -Force $dir | Out-Null
@{ "village"="ca41f431-6d5d-43d4-94d1-80d2c931a5a6"; "farm"="3e888f5a-109c-4cbc-89af-ea5d3c39fae4";
   "sea"="30aed728-0b51-4a5a-99b8-e0b69a95769f"; "clerk"="a24c8688-842e-429a-bf0d-80af42916151";
   "agent"="2ecd012f-fe1e-4566-bb7c-63813aef2fea" }.GetEnumerator() | % {
  Invoke-WebRequest "$base$($_.Value).png" -OutFile "$dir\$($_.Key).png" }
```

할 일: 이미지를 **아직 아무도 눈으로 확인 안 했다.** 배경 속 건물 위치에 맞춰 `data.js` 의 `people[].x / y`(%) 조정, 마음에 안 들면 재생성.

---

## 4. 클라우드 세션에서 막혔던 것 (→ PC 로컬 세션이면 해결)

| 막힌 것 | 이유 |
|---|---|
| 사내 대시보드 `http://192.168.30.91:8080/` | 사내망 주소 — 클라우드에서 접속 불가 (타임아웃) |
| `aitop100.org`, `kakaoimpact.org`, `brianimpact.org`, `brunch.co.kr` | 클라우드 환경 네트워크 정책이 차단 (WebFetch·curl·내장 Chromium 모두 403) |
| `C:\Users\kkari\Downloads\AI 100` (사용자가 저장한 지난 문제) | 클라우드 컨테이너는 사용자 PC 파일에 접근 불가 |
| 힉스필드 이미지 다운로드 | CDN 도메인 차단 (생성은 됨) |

**그래서 지난 대회 문제는 아직 실제로 분석하지 못했다.** README 의 함정 표는 검색 요약만 보고 추정한 것이다.

---

## 5. 지금까지 알아낸 대회 정보 (검색 요약 기준 — 원문 미확인)

- 주최 카카오임팩트·브라이언임팩트. 2025년 예선 약 3,000명, 개인전, 각자 기기·**AI 도구 제한 없음**, 상위 100명 본선.
- 2025 예선 문제 제목: 춘식도락 메뉴 분석 챌린지 / 고대 유적의 비밀: 이상한 코드 석판 / 영상 팩트 체크 / 시뮬레이션을 통한 예측 / PDF 속 스텔스 텍스트 추적기
- 2025 본선: 방대한 데이터로 인수인계 문서 작성, 규칙 기반 암호 해석, 오목 AI 구현 (3시간에 9문제 제출했다는 후기)
- 후기 공통 교훈: AI 답을 그대로 쓰면 틀림 → **검증, 여러 모델 교차, 문제 쪼개기**가 핵심. "문제별로 적합한 AI 모델을 고르는 능력"이 평가 포인트.
- "예선 문제 다시 풀기" 사이트가 공개되어 있음 (점수 자동 계산).

---

## 6. 남은 할 일 (우선순위)

1. [ ] **지난 대회 문제 분석** — `C:\Users\kkari\Downloads\AI 100` + 브런치 후기(`https://brunch.co.kr/@andkakao/323` 등) → `ai-top-100/problems/분석.md`
2. [ ] 분석 결과로 README 함정 표·toolkit 보강, 마을 조합 테마의 **예상 문제 + 연습용 가짜 데이터 세트**(엑셀·영수증 이미지·PDF 숨은 글자) 제작
3. [ ] **사내 대시보드 AI 오피스 참고**해 `village-office` 디자인 고도화
4. [ ] 힉스필드 이미지 내려받기(§3) → 눈으로 확인 → 핫스팟 좌표 조정
5. [ ] 10/23 안내 메일 수신 후 README §1 "모르는 것" 채우기 — 특히 **미리 만든 코드·템플릿 사용 가능 여부**
6. [ ] 10/24~25 5시간 모의고사, 10/30 장비 리허설

---

## 7. 대화 기록 (요약)

1. **사용자**: 대회 안내문·미션 브리프 공유. 준비 사항 검토, 사내 AI 오피스처럼 세련된 비주얼, 필요시 힉스필드 에셋 요청.
   **Claude**: 사내 대시보드 접속 시도(실패), 대회 정보 웹 검색, 힉스필드로 배경 1 + 아바타 4장 생성, README·오피스 화면·toolkit 제작 후 커밋·푸시.
2. **사용자**: "예선문제들 학습했지?"
   **Claude**: 아니다 — 공식 사이트·문제 공개 글이 네트워크 정책에 막혀 제목 수준 요약만 봤다고 솔직히 답함. 붙여넣기/첨부/네트워크 허용 중 하나를 요청.
3. **사용자**: 브런치 링크(`@andkakao/323`) 읽히는지 확인 요청 → 403 차단. 네트워크 설정 변경 방법 안내.
4. **사용자**: "클로드 내부 브라우저로 열어봐" → 컨테이너 Chromium 으로도 같은 프록시라 실패(`ERR_TUNNEL_CONNECTION_FAILED`).
5. **사용자**: 문제를 `C:\Users\kkari\Downloads\AI 100` 에 저장했다고 함 → 클라우드에서 PC 파일 접근 불가, 업로드 폴더도 비어 있음 확인.
6. **사용자**: "왜 안 되냐, 계속 내 컴퓨터에 접속해서 했잖아" → 이전엔 PC 로컬 세션, 이번엔 클라우드 세션이라 다르다고 설명. 로컬 세션으로 옮길 것을 권장.
7. **사용자**: 이전용 자료와 대화 정리 요청 → 이 문서(`HANDOFF.md`)와 `ai-top-100/CLAUDE.md` 작성.

사용자 선호: **모든 답변 한국어**, 확실하지 않은 정보는 추측하지 말고 모른다고 말하기, 복잡한 건 단계별로 쉽게, 첨부 파일은 전부 읽고 답하기.
