# 책호스터이프로 책장

인스타그램 @kkariboy42 에 올린 추리·미스터리 게시물을 책별로 모은 사이트.

## 갱신

1. 새 게시물 주소를 `links.txt` 에 한 줄 추가
2. `py -3 collect.py` — 캡션을 읽어 책별로 분류하고 `site/data.js` 를 다시 만든다
3. 커밋·푸시하면 GitHub Pages 가 다시 배포한다

분류가 틀리면 `overrides.json` 에 적는다:
`{"<shortcode>": {"book": "제목", "spoiler": true, "hide": true, "kind": "서평"}}`
