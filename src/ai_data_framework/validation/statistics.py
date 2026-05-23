"""Testes estatísticos para validação de hipóteses.

Implementa os requisitos de Validation_rules.md:
- p-value < 0.05 para significância estatística
- Testes qui-quadrado, t-test, correlação de Pearson
- Consistência temporal (múltiplos períodos)
"""

from __future__ import annotations

from typing import Any


def pearson_correlation_pvalue(x: list[float], y: list[float]) -> tuple[float, float]:
    """Calcula correlação de Pearson e p-value.

    Returns:
        (r, p_value): coeficiente de correlação e p-value bilateral
    """
    import math

    n = len(x)
    if n < 3:
        return 0.0, 1.0

    mean_x = sum(x) / n
    mean_y = sum(y) / n

    dx = [xi - mean_x for xi in x]
    dy = [yi - mean_y for yi in y]

    num = sum(dx[i] * dy[i] for i in range(n))
    den_x = math.sqrt(sum(v**2 for v in dx))
    den_y = math.sqrt(sum(v**2 for v in dy))

    if den_x == 0 or den_y == 0:
        return 0.0, 1.0

    r = num / (den_x * den_y)

    # Fisher's z-transformation for p-value
    # z = 0.5 * ln((1+r)/(1-r))
    if abs(r) >= 1.0:
        return r, 0.0

    z = 0.5 * math.log((1 + r) / (1 - r))
    se = 1.0 / math.sqrt(n - 3)
    z_obs = abs(z) / se

    # Approximate p-value from normal distribution (two-tailed)
    p_value = 2 * (1 - _normal_cdf(z_obs))

    return r, p_value


def _normal_cdf(z: float) -> float:
    """Aproxima CDF da normal padrão."""
    import math

    if z < 0:
        return 1 - _normal_cdf(-z)

    t = 1 / (1 + 0.2316414 * z)
    poly = t * (0.319381530 + t * (-0.356563782 + t * (1.781477937 + t * (-1.821855978 + t * 1.330274429))))
    return 1 - (1 / math.sqrt(2 * math.pi)) * math.exp(-z * z / 2) * poly


def chi_square_test(
    observed: list[int],
    expected: list[float],
) -> tuple[float, float]:
    """Teste qui-quadrado.

    Returns:
        (chi2, p_value)
    """
    if len(observed) != len(expected):
        raise ValueError("observed e expected devem ter mesmo tamanho")

    chi2 = sum((o - e) ** 2 / e for o, e in zip(observed, expected) if e > 0)

    df = len(observed) - 1
    if df <= 0:
        return chi2, 1.0

    p_value = _chi_square_pvalue(chi2, df)
    return chi2, p_value


def _chi_square_pvalue(chi2: float, df: int) -> float:
    """Aproxima p-value para qui-quadrado via aproximação de Wilson-Hilferty."""
    import math

    if df <= 0 or chi2 <= 0:
        return 1.0

    # Use normal approximation for large df
    if df > 100:
        z = (chi2 ** (1/3) - (df - 1) ** (1/3)) / (math.sqrt(2 / 9) * (df - 1) ** (1/3))
        return 2 * (1 - _normal_cdf(abs(z)))

    # For smaller df, approximate via incomplete gamma
    # Simplified approximation
    return 1.0 - _regularized_gamma_lower(min(chi2, 1000) / 2, df / 2)


def _regularized_gamma_lower(x: float, a: float) -> float:
    """Aproximação da gama regularizada inferior P(a,x)."""
    import math

    if x <= 0:
        return 0.0

    if a <= 0:
        return 1.0

    gl = math.lgamma(a)
    s = 0.0
    term = 1.0 / a
    partial = term

    for n in range(1, 200):
        term *= x / (a + n)
        partial += term
        if abs(term) < 1e-10 * abs(partial):
            break

    result = math.exp(-x + a * math.log(x) - gl) * partial
    return min(1.0, max(0.0, result))


def t_test_two_sample(
    sample1: list[float],
    sample2: list[float],
) -> tuple[float, float]:
    """Two-sample t-test (Welch's t-test).

    Returns:
        (t_statistic, p_value)
    """
    import math

    n1, n2 = len(sample1), len(sample2)
    if n1 < 2 or n2 < 2:
        return 0.0, 1.0

    mean1 = sum(sample1) / n1
    mean2 = sum(sample2) / n2

    var1 = sum((x - mean1) ** 2 for x in sample1) / (n1 - 1)
    var2 = sum((x - mean2) ** 2 for x in sample2) / (n2 - 1)

    if var1 == 0 and var2 == 0:
        return 0.0, 1.0

    se = math.sqrt(var1 / n1 + var2 / n2)
    if se == 0:
        return 0.0, 1.0

    t = (mean1 - mean2) / se

    # Welch-Satterthwaite degrees of freedom
    num = (var1 / n1 + var2 / n2) ** 2
    den = (var1 / n1) ** 2 / (n1 - 1) + (var2 / n2) ** 2 / (n2 - 1)
    df = num / den if den > 0 else 1

    # Approximate p-value from t-distribution
    p_value = 2 * (1 - _t_cdf(abs(t), df))

    return t, p_value


def _t_cdf(t: float, df: int) -> float:
    """Aproxima CDF da distribuição t de Student."""
    import math

    if df <= 0:
        return 0.5

    x = df / (df + t * t)
    return 1 - 0.5 * _regularized_gamma_lower(df / 2, df / 2) * (1 - x) ** (df / 2) * (1 + t * t / df) ** (-df / 2)


def check_temporal_consistency(
    values: list[float],
    periods: list[str],
    min_periods: int = 2,
) -> tuple[bool, float, str]:
    """Verifica consistência temporal.

    Args:
        values: valores por período
        periods: nomes dos períodos
        min_periods: mínimo de períodos para confirmar

    Returns:
        (is_consistent, confidence, explanation)
    """
    if len(values) < min_periods or len(periods) != len(values):
        return False, 0.0, f"Menos de {min_periods} períodos disponíveis"

    # Check direction consistency across periods
    directions: list[int] = []
    for i in range(1, len(values)):
        if values[i] > values[i - 1]:
            directions.append(1)
        elif values[i] < values[i - 1]:
            directions.append(-1)
        else:
            directions.append(0)

    if not directions:
        return False, 0.0, "Sem variação entre períodos"

    # All same direction = consistent
    consistent_periods = sum(1 for d in directions if d != 0)
    if consistent_periods == len(directions):
        return True, 0.9, f"Padrão consistente em {len(periods)} períodos"

    # If some are consistent, partial confidence
    confidence = consistent_periods / len(directions)
    if confidence >= 0.6:
        return True, confidence, f"Padrão parcialmente consistente ({consistent_periods}/{len(directions)} períodos)"
    else:
        return False, confidence, f"Padrão inconsistente ({consistent_periods}/{len(directions)} períodos)"


def is_significant(
    p_value: float,
    threshold: float = 0.05,
) -> bool:
    """Verifica se p-value indica significância estatística."""
    return p_value < threshold


def effect_size_delta(
    baseline: float,
    observed: float,
    threshold_pct: float = 0.05,
) -> tuple[bool, float]:
    """Verifica se delta supera threshold percentual.

    Returns:
        (is_significant, delta_pct)
    """
    if baseline == 0:
        return False, 0.0

    delta_pct = abs(observed - baseline) / abs(baseline)
    return delta_pct > threshold_pct, delta_pct


def check_cross_segment_consistency(
    values_by_segment: dict[str, list[float]],
    direction: str = "increasing",
) -> tuple[bool, float, str]:
    """Verifica se o padrão se mantém consistente entre segmentos.

    Args:
        values_by_segment: dict mapping segment name -> list of values in that segment
        direction: 'increasing', 'decreasing', or 'any' (neutral check)

    Returns:
        (is_consistent, confidence, explanation)
    """
    if len(values_by_segment) < 2:
        return False, 0.0, "Menos de 2 segmentos — impossível comparar consistência"

    # Compute aggregate metric per segment (mean of values)
    segment_means: dict[str, float] = {}
    for seg, vals in values_by_segment.items():
        if vals:
            segment_means[seg] = sum(vals) / len(vals)
        else:
            segment_means[seg] = 0.0

    sorted_segments = sorted(segment_means.keys())
    means_sorted = [segment_means[s] for s in sorted_segments]

    # Check direction consistency
    if direction == "increasing":
        consistent = all(means_sorted[i] <= means_sorted[i + 1] for i in range(len(means_sorted) - 1))
    elif direction == "decreasing":
        consistent = all(means_sorted[i] >= means_sorted[i + 1] for i in range(len(means_sorted) - 1))
    else:
        # 'any' — just check there is variance (not all equal)
        consistent = any(means_sorted[i] != means_sorted[0] for i in range(1, len(means_sorted)))

    if not consistent:
        return False, 0.0, f"Padrão inconsistente entre segmentos: {segment_means}"

    # Compute coefficient of variation across segment means
    all_means = list(segment_means.values())
    overall_mean = sum(all_means) / len(all_means)
    if overall_mean == 0:
        return True, 1.0, f"Padrão consistente mas mean=0 (precaução)"

    cv = (sum((m - overall_mean) ** 2 for m in all_means) / len(all_means)) ** 0.5 / abs(overall_mean)

    # High CV (>0.5) indicates segments behave very differently regardless of direction
    if cv > 0.5:
        return False, 1.0, f"Inconsistência cross-segment: CV={cv:.2f} — padrão não se mantém entre segmentos {segment_means}"

    confidence = max(0.0, 1.0 - cv)
    return True, confidence, f"Padrão consistente em {len(values_by_segment)} segmentos (CV={cv:.2f})"