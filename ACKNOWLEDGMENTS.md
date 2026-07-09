# Acknowledgments

<!-- SPDX-License-Identifier: Apache-2.0 -->

Eidolon is an independent, clean-room implementation. The following
published works informed its design. No source code, assets, test data,
prompts, schemas, or model weights from any of these works were copied.

## Research Influences

### Compact Structured Experience Representations

> Wang, R., Ren, Z., & Zhang, Y. (2026). *EvoMap: Structured Experience
> Representations for Lifelong Agent Learning*. arXiv:2604.15097.

Insight applied: compact, structured episode records (not verbose raw
content) survive session boundaries and warm-start bandit posteriors
without ballooning storage. This informed the `EpisodeRecord` schema and
the `hydrate_bandit` replay mechanism.

### Thompson Sampling for Online Arm Selection

> Thompson, W. R. (1933). On the likelihood that one unknown probability
> exceeds another in view of the evidence of two samples.
> *Biometrika*, 25(3/4), 285–294.

Insight applied: Beta-Bernoulli Thompson sampling provides
computationally cheap, provably convergent arm selection with no
hyperparameter tuning. This is the algorithm behind `ThompsonBandit`.

### Hermes Agent Infrastructure

Eidolon is designed to integrate with the
[Hermes Agent](https://github.com/NousResearch/hermes-function-calling)
ecosystem. Eidolon adds a self-improvement layer; it does not modify or
redistribute Hermes source code.

## How to Add an Attribution

If you extend Eidolon and draw on published work, add an entry here:

```markdown
### Short Title

> Author(s). (Year). *Title*. Venue. DOI or arXiv ID.

Insight applied: one sentence describing what informed your design.
```

Keep entries factual. Never include personal contact information,
private hostnames, operator-specific configuration, or unreleased
pre-prints without author consent.
