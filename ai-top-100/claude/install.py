"""aitop 에이전트·스킬·도구를 ~/.claude 에 설치(덮어쓰기)한다.

  py -3 install.py

원본은 이 저장소(ai-top-100/claude, ai-top-100/toolkit)다. ~/.claude 쪽을 고치지 말고 여기를 고친 뒤 다시 설치한다.
"""
import shutil
from pathlib import Path

here = Path(__file__).resolve().parent
home = Path.home() / ".claude"
for f in sorted((here / "agents").glob("aitop-*.md")):
    shutil.copy2(f, home / "agents" / f.name)
    print("에이전트", f.name)
dst = home / "skills" / "aitop-solve"
if dst.exists():
    shutil.rmtree(dst)
shutil.copytree(here / "skills" / "aitop-solve", dst)
shutil.copytree(here.parent / "toolkit", dst / "toolkit", ignore=shutil.ignore_patterns("__pycache__", "_selftest_out"))
print("스킬", dst, "(+ toolkit)")
