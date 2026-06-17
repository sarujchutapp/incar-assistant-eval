"""Statistics for the objective quadrant — pure functions, no external deps.

Wilson score intervals for proportions (valid near 0/1, where the normal
approximation misbehaves) and McNemar's test for paired model comparison. There
is deliberately **no** Elo / Bradley-Terry here: ranking models on the objective
quadrant would discard the per-case ground truth (benchmark_spec.md §5.1).
Bradley-Terry for the chat quadrant lives elsewhere (slice 7).
"""

import math
from dataclasses import dataclass

Z_95 = 1.959963984540054  # standard normal quantile for a 95% interval


def wilson_interval(k: int, n: int, z: float = Z_95) -> tuple[float, float]:
    """Wilson score interval for k successes out of n."""
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    z2 = z * z
    denom = 1.0 + z2 / n
    center = (p + z2 / (2 * n)) / denom
    half = (z / denom) * math.sqrt(p * (1 - p) / n + z2 / (4 * n * n))
    return (max(0.0, center - half), min(1.0, center + half))


@dataclass(frozen=True)
class McNemarResult:
    statistic: float
    p_value: float
    b: int  # discordant pairs: model right, baseline wrong
    c: int  # discordant pairs: baseline right, model wrong


def mcnemar(b: int, c: int) -> McNemarResult:
    """McNemar's test (continuity-corrected) on the discordant pair counts.

    p-value from the chi-square_1 survival function: P(X>x) = erfc(sqrt(x/2)).
    """
    n = b + c
    if n == 0:
        return McNemarResult(statistic=0.0, p_value=1.0, b=b, c=c)
    statistic = (abs(b - c) - 1) ** 2 / n
    p_value = math.erfc(math.sqrt(statistic / 2))
    return McNemarResult(statistic=statistic, p_value=p_value, b=b, c=c)
