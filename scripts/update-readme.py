"""README의 자동 갱신 구간을 채운다.

- notes: memories 위키 topics/ 아래 최근 노트
- repos: 최근에 손댄 퍼블릭 레포
"""

import json
import os
import re
import sys
import urllib.request
from pathlib import Path

USER = "WoodrowDy"
MEMORIES_DIR = Path(os.environ.get("MEMORIES_DIR", "memories"))
README = Path(os.environ.get("README_PATH", "README.md"))
NOTE_COUNT = 5
REPO_COUNT = 5
EXCLUDED_REPOS = {USER.lower(), "memories"}


def read_frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---", text, re.S)
    if not match:
        return {}
    fields = {}
    for line in match.group(1).splitlines():
        key, sep, value = line.partition(":")
        if sep and not line.startswith((" ", "\t")):
            fields[key.strip()] = value.split("#", 1)[0].strip().strip("'\"")
    return fields


def recent_notes() -> list[str]:
    notes = []
    for path in (MEMORIES_DIR / "topics").rglob("*.md"):
        if path.name.lower() == "readme.md":
            continue
        meta = read_frontmatter(path)
        if not meta.get("title") or meta.get("status") == "archived":
            continue
        rel = path.relative_to(MEMORIES_DIR).as_posix()
        category = rel.split("/")[1]
        notes.append((meta.get("updated", ""), meta["title"], category, rel))
    notes.sort(key=lambda n: (n[0], n[3]), reverse=True)
    return [
        f"- [{title}](https://github.com/{USER}/memories/blob/main/{rel}) `{category}`"
        for _, title, category, rel in notes[:NOTE_COUNT]
    ]


def recent_repos() -> list[str]:
    url = f"https://api.github.com/users/{USER}/repos?type=owner&sort=pushed&per_page=100"
    request = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json"})
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(request) as response:
        repos = json.load(response)

    lines = []
    for repo in repos:
        if repo["private"] or repo["fork"] or repo["archived"]:
            continue
        if repo["name"].lower() in EXCLUDED_REPOS:
            continue
        line = f"- [{repo['name']}]({repo['html_url']})"
        if repo.get("description"):
            line += f" — {repo['description']}"
        lines.append(line)
        if len(lines) == REPO_COUNT:
            break
    return lines


def replace_section(text: str, name: str, lines: list[str]) -> str:
    start, end = f"<!-- {name}:start -->", f"<!-- {name}:end -->"
    pattern = re.compile(re.escape(start) + r".*?" + re.escape(end), re.S)
    if not pattern.search(text):
        sys.exit(f"README에 {start} / {end} 표시가 없습니다.")
    body = "\n".join(lines)
    return pattern.sub(lambda _: f"{start}\n{body}\n{end}", text)


def main() -> None:
    text = README.read_text(encoding="utf-8")
    text = replace_section(text, "notes", recent_notes())
    text = replace_section(text, "repos", recent_repos())
    README.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
