import json
from dataclasses import dataclass
from pathlib import Path


MAX_HIGHSCORES = 10
HIGHSCORES_FILE = Path(__file__).resolve().parents[2] / "highscores.json"


@dataclass(frozen=True)
class Highscore:
    name: str
    score: int


def load_highscores() -> list[Highscore]:
    if not HIGHSCORES_FILE.exists():
        return []

    try:
        data = json.loads(HIGHSCORES_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []

    highscores = []
    for item in data:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "Player")).strip() or "Player"
        try:
            score = int(item.get("score", 0))
        except (TypeError, ValueError):
            continue
        highscores.append(Highscore(name=name, score=score))

    return sorted(highscores, key=lambda highscore: highscore.score, reverse=True)[:MAX_HIGHSCORES]


def is_highscore(score: int) -> bool:
    highscores = load_highscores()
    return len(highscores) < MAX_HIGHSCORES or score > highscores[-1].score


def save_highscore(name: str, score: int) -> list[Highscore]:
    clean_name = name.strip() or "Player"
    highscores = load_highscores()
    highscores.append(Highscore(name=clean_name[:24], score=score))
    highscores = sorted(highscores, key=lambda highscore: highscore.score, reverse=True)[:MAX_HIGHSCORES]

    HIGHSCORES_FILE.write_text(
        json.dumps([highscore.__dict__ for highscore in highscores], indent=2) + "\n",
        encoding="utf-8",
    )
    return highscores
