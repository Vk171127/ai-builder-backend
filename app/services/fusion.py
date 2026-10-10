"""Risk fusion logic."""


def fuse_scores(rules_x100: int, classifier_x100: int, anomaly_x100: int) -> int:
    weighted = (rules_x100 * 4 + classifier_x100 * 4 + anomaly_x100 * 2) // 10
    return max(0, min(100, weighted))
