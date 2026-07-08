"""REC-005: provider-agnostic inference router."""

from __future__ import annotations

import unittest

from tests.unit._tmphomes import IsolatedHome


class RouterTests(IsolatedHome):
    def test_empty_cache_returns_no_match_and_emits_degraded(self) -> None:
        from eidolon.inference import InferenceRouter
        from eidolon.inference.tiers import TIER_A, MIN_CAPABILITIES

        router = InferenceRouter.from_dict({})
        result = router.resolve(tier=TIER_A, requires=MIN_CAPABILITIES)
        self.assertIsNone(result)

        # A degraded event must have been logged.
        from eidolon.util import events
        recs = list(events.read())
        self.assertTrue(
            any(r["kind"] == "inference.degraded" for r in recs),
            f"expected inference.degraded event; got: {recs}",
        )

    def test_matching_tier_a_provider_resolves(self) -> None:
        from eidolon.inference import InferenceRouter
        from eidolon.inference.tiers import TIER_A, MIN_CAPABILITIES

        router = InferenceRouter.from_dict({
            "provider-alpha": {
                "tier": "A",
                "capabilities": ["json_mode"],
                "context_window": 16000,
            }
        })
        match = router.resolve(tier=TIER_A, requires=MIN_CAPABILITIES)
        self.assertIsNotNone(match)
        self.assertEqual(match.provider, "provider-alpha")
        self.assertEqual(match.tier, "A")

    def test_provider_without_required_capability_is_skipped(self) -> None:
        from eidolon.inference import InferenceRouter
        from eidolon.inference.tiers import TIER_A, MIN_CAPABILITIES

        router = InferenceRouter.from_dict({
            "no-json": {
                "tier": "A",
                "capabilities": [],  # no json_mode
                "context_window": 32000,
            }
        })
        self.assertIsNone(router.resolve(tier=TIER_A, requires=MIN_CAPABILITIES))

    def test_lower_tier_provider_is_not_used_for_higher_request(self) -> None:
        from eidolon.inference import InferenceRouter

        router = InferenceRouter.from_dict({
            "small": {"tier": "A", "capabilities": ["json_mode"], "context_window": 32000}
        })
        # Requesting Tier C -> the small provider must not satisfy it.
        self.assertIsNone(router.resolve(tier="C", requires=["json_mode"]))

    def test_router_prefers_exact_tier_over_over_provisioning(self) -> None:
        from eidolon.inference import InferenceRouter

        router = InferenceRouter.from_dict({
            "cheap": {"tier": "A", "capabilities": ["json_mode"], "context_window": 16000},
            "big":   {"tier": "C", "capabilities": ["json_mode", "tool_use"], "context_window": 128000},
        })
        match = router.resolve(tier="A", requires=["json_mode"])
        self.assertIsNotNone(match)
        self.assertEqual(match.provider, "cheap")

    def test_router_reads_hermes_home_cache(self) -> None:
        from eidolon.inference import InferenceRouter

        self.write_hermes_cache({
            "host-configured": {
                "tier": "B",
                "capabilities": ["json_mode"],
                "context_window": 32000,
            }
        })
        router = InferenceRouter.from_hermes()
        match = router.resolve(tier="B", requires=["json_mode"])
        self.assertIsNotNone(match)
        self.assertEqual(match.provider, "host-configured")

    def test_missing_cache_file_yields_empty_router_not_crash(self) -> None:
        """The `custom:ds4` lesson: never crash on absent config."""
        from eidolon.inference import InferenceRouter

        # No cache file written; HERMES_HOME exists but cache does not.
        router = InferenceRouter.from_hermes()
        self.assertEqual(list(router.providers()), [])
        self.assertIsNone(router.resolve(tier="A", requires=["json_mode"]))

    def test_corrupt_cache_raises_router_error(self) -> None:
        from eidolon.inference import InferenceRouter, RouterError

        (self.hermes_home / "provider_models_cache.json").write_text(
            "not-json{{{", encoding="utf-8"
        )
        with self.assertRaises(RouterError):
            InferenceRouter.from_hermes()


if __name__ == "__main__":
    unittest.main()
