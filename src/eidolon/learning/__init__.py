# SPDX-License-Identifier: Apache-2.0
"""Eidolon learning subsystem.

REC-008: contextual bandit over prompt-phrasing arms, scored by the
deterministic regression suite. Stdlib-only. No neural bandit. No real
inference in tests.

Public surface intentionally small:
- bandit.ThompsonBandit
- arms.ArmRegistry / register_arm
- rewards.RegressionReward
- replay.ReplayBuffer / append / iter_records
- schemas.EpisodeRecord (schema=1, frozen)

The bandit NEVER modifies SOUL.md, skill code, or ~/.hermes/config.yaml.
Any such mutation is a bug.
"""
