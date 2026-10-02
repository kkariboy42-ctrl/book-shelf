# 영상·이미지 문제 명령 모음 (2025 예선 3번 「영상 팩트 체크」 유형)

이 PC에 설치됨: `yt-dlp`(Python 3.10 쪽), `ffmpeg 8.1`. 대회 당일 쓸 PC에서 `yt-dlp --version`, `ffmpeg -version` 이 둘 다 나오는지 먼저 확인한다.

## 원칙

- **음성으로 답하는 문제** → 자막을 텍스트로 받아 검색한다. 영상을 다시 볼 필요가 없다.
- **화면으로 답하는 문제**(마신 음료, 마커 개수, 화면 자막 속 숫자) → 자막으로 대략 시각을 찾고, 그 앞뒤 프레임을 뽑아 **직접 확대해서 본다.** 개수 세기는 비전 모델에게 맡기지 않는다.
- 「영상에서 확인할 수 있는」 것만 답이다. AI가 바깥 지식으로 채운 답은 타임코드를 대지 못하면 버린다.

## 자막 받기

```bash
yt-dlp --skip-download --write-subs --write-auto-subs --sub-langs "en.*,ko.*" --convert-subs srt -o "%(title)s.%(ext)s" "영상URL"
```

```bash
yt-dlp --skip-download --write-auto-subs --sub-langs en --convert-subs srt -o "ep%(playlist_index)s" "재생목록URL"
```

자막에서 낱말 찾기(타임코드와 함께):

```bash
grep -n -i -B2 "pit stop" *.srt
```

## 영상 받기 (화면 확인용, 720p면 충분)

```bash
yt-dlp -f "bv*[height<=720]+ba/b[height<=720]" -o "%(title)s.%(ext)s" "영상URL"
```

## 프레임 뽑기

특정 시각 앞뒤 10초를 초당 2장:

```bash
ffmpeg -ss 00:12:30 -t 20 -i 영상.mp4 -vf fps=2 frame_%03d.png
```

장면이 바뀔 때마다 한 장(영상 전체 훑기용 콘택트 시트 재료):

```bash
ffmpeg -i 영상.mp4 -vf "select='gt(scene,0.3)',scale=640:-1" -vsync vfr scene_%04d.png
```

한 화면에 4×4 콘택트 시트(10초 간격):

```bash
ffmpeg -i 영상.mp4 -vf "fps=1/10,scale=480:-1,tile=4x4" sheet_%02d.png
```

## 이미지 속 글자·코드 (석판·메뉴판 유형)

- 두 모델(예: Claude·Gemini)에 같은 이미지를 따로 옮기게 하고 `csv_diff.py` 또는 `fc /n a.txt b.txt` 로 비교한다. 다른 곳만 원본을 확대해서 본다.
- 코드는 **머리로 풀지 말고 실행한다.** 언어가 애매하면 후보 언어로 다 돌려 본다(석판은 C처럼 보이지만 파이썬으로만 돌았다 → `problems/석판_STOP_판독본.py`).
- 희미한 글자는 대비를 키운다: `python pdf_stealth.py 문서.pdf --enhance out/` (PDF가 아니면 이미지를 PDF로 감싸거나 PIL `ImageOps.equalize`).

## 인수인계 유형 — 암호 걸린 zip

`비밀번호(생일4자리).zip` 처럼 힌트가 파일명에 있으면, 자료에서 생일을 찾기 전에 0101~1231 날짜 366개만 시험해도 된다(이건 자기 대회 자료에 한해서다). 정석은 메일·메모에서 생일을 찾는 것이고, 출제 의도도 그쪽이다.

> ⚠ 아래 코드는 **아직 시험 못 했다**(이 PC에 암호 zip 만드는 도구가 없음). 파이썬 기본 `zipfile` 은 옛 방식(ZipCrypto) 암호만 연다. AES 암호면 `pip install pyzipper` 후 `pyzipper.AESZipFile` 로 바꾼다. 연습 때 한 번 돌려 볼 것.

```bash
py -3 -c "import zipfile,datetime as D;z=zipfile.ZipFile('파일.zip');d=D.date(2024,1,1)
for i in range(366):
    p=(d+D.timedelta(i)).strftime('%m%d')
    try: z.extractall('풀림',pwd=p.encode()); print('비밀번호',p); break
    except Exception: pass"
```
