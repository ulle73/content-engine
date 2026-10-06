"""Read-only access to repo skills (skills/<name>/SKILL.md)."""

from pathlib import Path

SKILLS_DIR = Path(__file__).resolve().parents[2] / "skills"


def available() -> list[dict]:
    out = []
    for path in sorted(SKILLS_DIR.glob("*/SKILL.md")):
        description = ""
        for line in path.read_text(encoding="utf-8").splitlines()[1:10]:
            if line.startswith("description:"):
                description = line.split(":", 1)[1].strip()
                break
        out.append({"name": path.parent.name, "description": description})
    return out


def read(name: str) -> str:
    names = {item["name"] for item in available()}
    if name not in names:
        raise ValueError(f"Okänd skill '{name}'. Finns: {', '.join(sorted(names))}")
    return (SKILLS_DIR / name / "SKILL.md").read_text(encoding="utf-8")
