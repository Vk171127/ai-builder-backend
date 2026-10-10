"""Policy mapping from risk to action."""

from app.models.signal import Stage


def map_risk_to_stage(risk_x100: int) -> Stage:
    if risk_x100 >= 80:
        return Stage.block
    if risk_x100 >= 40:
        return Stage.warn
    return Stage.observe
