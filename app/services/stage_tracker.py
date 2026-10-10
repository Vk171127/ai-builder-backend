"""Stage tracker stub with HMM-style belief updates."""

from app.models.signal import Stage


def next_stage(current: Stage, risk_x100: int) -> Stage:
    if risk_x100 >= 80:
        return Stage.block
    if risk_x100 >= 40:
        return Stage.warn
    return current
