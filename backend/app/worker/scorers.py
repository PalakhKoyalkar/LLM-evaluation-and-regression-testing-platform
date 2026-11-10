from app.models import Score


def _normalize(text: str) -> str:
    return " ".join(text.strip().lower().split())


def exact_match(output: str, expected: str | None) -> Score | None:
    if expected is None:
        return None
    return Score(scorer="exact_match", value=1.0 if _normalize(output) == _normalize(expected) else 0.0)
