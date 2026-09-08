from app.schemas.project import ProjectCreate


def estimate_credits(data: ProjectCreate) -> int:
    base = 5
    duration_units = max(1, round(data.duration_seconds / 10))
    multiplier = {"economy": 2, "balanced": 4, "premium": 8}.get(data.quality.lower(), 4)
    return base + duration_units * multiplier
