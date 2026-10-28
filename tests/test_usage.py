import unittest

from heritage_rag_safety.usage import (
    ModelUsageObservation,
    UsageBudget,
    aggregate_usage,
    check_usage_budget,
)


def observation(**updates):
    values = {
        "adapter_name": "demo-adapter",
        "outcome": "OK",
        "input_units": 10,
        "output_units": 5,
        "total_units": 15,
        "duration_ms": 20,
        "billed_cost_micros": 25,
        "currency": "EUR",
    }
    values.update(updates)
    return ModelUsageObservation(**values)


class UsageTests(unittest.TestCase):
    def test_budget_limits_are_enforced(self):
        self.assertTrue(check_usage_budget(observation(), UsageBudget(max_total_units=15)).allowed)
        self.assertEqual(
            "TOTAL_UNITS_EXCEEDED",
            check_usage_budget(observation(), UsageBudget(max_total_units=14)).code,
        )

    def test_monetary_limit_fails_closed_without_provider_cost(self):
        decision = check_usage_budget(
            observation(billed_cost_micros=None, currency=None),
            UsageBudget(max_billed_cost_micros=100, currency="EUR"),
        )
        self.assertEqual("COST_UNAVAILABLE", decision.code)

    def test_aggregate_does_not_retain_adapter_names_or_payloads(self):
        aggregate = aggregate_usage([observation(), observation(outcome="TIMEOUT", input_units=1, output_units=0, total_units=1)])
        self.assertEqual(2, aggregate.call_count)
        self.assertEqual(1, aggregate.successful_call_count)
        self.assertEqual(16, aggregate.total_units)
        self.assertEqual({"EUR": 50}, aggregate.billed_cost_micros_by_currency)


if __name__ == "__main__":
    unittest.main()
