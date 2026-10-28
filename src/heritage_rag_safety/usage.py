"""Provider-neutral, privacy-minimized model-usage accounting."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable


USAGE_OBSERVABILITY_VERSION = 1
_SAFE_ADAPTER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_CURRENCY_RE = re.compile(r"^[A-Z]{3}$")
_SAFE_OUTCOMES = frozenset({"OK", "TIMEOUT", "TRANSPORT_ERROR", "PROVIDER_ERROR", "REJECTED", "DEGRADED"})
MAX_USAGE_UNITS = 100_000_000
MAX_DURATION_MS = 3_600_000
MAX_COST_MICROS = 10**15


@dataclass(frozen=True)
class ModelUsageObservation:
    """A quantitative observation that deliberately has no prompt or identity."""

    adapter_name: str
    outcome: str
    input_units: int
    output_units: int
    total_units: int
    duration_ms: int
    billed_cost_micros: int | None = None
    currency: str | None = None


@dataclass(frozen=True)
class UsageBudget:
    """A limit for provider-reported usage; this package never guesses prices."""

    max_input_units: int | None = None
    max_output_units: int | None = None
    max_total_units: int | None = None
    max_billed_cost_micros: int | None = None
    currency: str | None = None


@dataclass(frozen=True)
class UsageBudgetDecision:
    allowed: bool
    code: str


@dataclass(frozen=True)
class UsageAggregate:
    version: int
    call_count: int
    successful_call_count: int
    failed_call_count: int
    input_units: int
    output_units: int
    total_units: int
    duration_ms: int
    billed_cost_micros_by_currency: dict[str, int]
    billed_cost_observation_count: int
    billed_cost_complete: bool


def _bounded_int(value: object, *, field: str, maximum: int, allow_none: bool = False) -> int | None:
    if value is None and allow_none:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{field} must be an integer.")
    if value < 0 or value > maximum:
        raise ValueError(f"{field} is outside the safe range.")
    return value


def _currency(value: object, *, allow_none: bool = False) -> str | None:
    if value is None and allow_none:
        return None
    if not isinstance(value, str) or not _CURRENCY_RE.fullmatch(value):
        raise ValueError("currency must be a three-letter uppercase code.")
    return value


def _validate_observation(observation: ModelUsageObservation) -> ModelUsageObservation:
    if not isinstance(observation, ModelUsageObservation):
        raise TypeError("Expected a ModelUsageObservation.")
    if not isinstance(observation.adapter_name, str) or not _SAFE_ADAPTER_RE.fullmatch(observation.adapter_name):
        raise ValueError("adapter_name is not safe or canonical.")
    if observation.outcome not in _SAFE_OUTCOMES:
        raise ValueError("outcome is not in the allowed set.")
    input_units = _bounded_int(observation.input_units, field="input_units", maximum=MAX_USAGE_UNITS)
    output_units = _bounded_int(observation.output_units, field="output_units", maximum=MAX_USAGE_UNITS)
    total_units = _bounded_int(observation.total_units, field="total_units", maximum=MAX_USAGE_UNITS)
    duration_ms = _bounded_int(observation.duration_ms, field="duration_ms", maximum=MAX_DURATION_MS)
    assert input_units is not None and output_units is not None and total_units is not None and duration_ms is not None
    if input_units + output_units != total_units:
        raise ValueError("total_units must exactly equal input_units plus output_units.")
    cost = _bounded_int(
        observation.billed_cost_micros,
        field="billed_cost_micros",
        maximum=MAX_COST_MICROS,
        allow_none=True,
    )
    currency = _currency(observation.currency, allow_none=True)
    if (cost is None) != (currency is None):
        raise ValueError("Reported cost and currency must either both exist or both be absent.")
    return ModelUsageObservation(
        adapter_name=observation.adapter_name,
        outcome=observation.outcome,
        input_units=input_units,
        output_units=output_units,
        total_units=total_units,
        duration_ms=duration_ms,
        billed_cost_micros=cost,
        currency=currency,
    )


def _validate_budget(budget: UsageBudget) -> UsageBudget:
    if not isinstance(budget, UsageBudget):
        raise TypeError("Expected a UsageBudget.")
    max_input = _bounded_int(budget.max_input_units, field="max_input_units", maximum=MAX_USAGE_UNITS, allow_none=True)
    max_output = _bounded_int(budget.max_output_units, field="max_output_units", maximum=MAX_USAGE_UNITS, allow_none=True)
    max_total = _bounded_int(budget.max_total_units, field="max_total_units", maximum=MAX_USAGE_UNITS, allow_none=True)
    max_cost = _bounded_int(budget.max_billed_cost_micros, field="max_billed_cost_micros", maximum=MAX_COST_MICROS, allow_none=True)
    currency = _currency(budget.currency, allow_none=True)
    if max_input is None and max_output is None and max_total is None and max_cost is None:
        raise ValueError("At least one usage limit is required.")
    if (max_cost is None) != (currency is None):
        raise ValueError("A monetary limit requires an explicit currency, and vice versa.")
    return UsageBudget(
        max_input_units=max_input,
        max_output_units=max_output,
        max_total_units=max_total,
        max_billed_cost_micros=max_cost,
        currency=currency,
    )


def check_usage_budget(observation: ModelUsageObservation, budget: UsageBudget) -> UsageBudgetDecision:
    """Compare reported consumption with a budget and fail closed on missing cost."""
    usage = _validate_observation(observation)
    limits = _validate_budget(budget)
    if limits.max_input_units is not None and usage.input_units > limits.max_input_units:
        return UsageBudgetDecision(False, "INPUT_UNITS_EXCEEDED")
    if limits.max_output_units is not None and usage.output_units > limits.max_output_units:
        return UsageBudgetDecision(False, "OUTPUT_UNITS_EXCEEDED")
    if limits.max_total_units is not None and usage.total_units > limits.max_total_units:
        return UsageBudgetDecision(False, "TOTAL_UNITS_EXCEEDED")
    if limits.max_billed_cost_micros is not None:
        if usage.billed_cost_micros is None or usage.currency is None:
            return UsageBudgetDecision(False, "COST_UNAVAILABLE")
        if usage.currency != limits.currency:
            return UsageBudgetDecision(False, "CURRENCY_MISMATCH")
        if usage.billed_cost_micros > limits.max_billed_cost_micros:
            return UsageBudgetDecision(False, "BILLED_COST_EXCEEDED")
    return UsageBudgetDecision(True, "OK")


def aggregate_usage(observations: Iterable[ModelUsageObservation]) -> UsageAggregate:
    """Aggregate only metrics; never retain content, prompts, or identities."""
    call_count = successful = input_units = output_units = total_units = duration_ms = billed_count = 0
    costs: dict[str, int] = {}
    for raw in observations:
        item = _validate_observation(raw)
        call_count += 1
        successful += int(item.outcome == "OK")
        input_units += item.input_units
        output_units += item.output_units
        total_units += item.total_units
        duration_ms += item.duration_ms
        if item.billed_cost_micros is not None and item.currency is not None:
            billed_count += 1
            costs[item.currency] = costs.get(item.currency, 0) + item.billed_cost_micros
    return UsageAggregate(
        version=USAGE_OBSERVABILITY_VERSION,
        call_count=call_count,
        successful_call_count=successful,
        failed_call_count=call_count - successful,
        input_units=input_units,
        output_units=output_units,
        total_units=total_units,
        duration_ms=duration_ms,
        billed_cost_micros_by_currency=dict(sorted(costs.items())),
        billed_cost_observation_count=billed_count,
        billed_cost_complete=bool(call_count and billed_count == call_count),
    )
