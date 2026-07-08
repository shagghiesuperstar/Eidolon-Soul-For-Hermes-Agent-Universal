# Citing Eidolon

If Eidolon supports your academic work, please cite it. The canonical machine-
readable citation lives in [`CITATION.cff`](../CITATION.cff) at the repo root
and GitHub renders it as the "Cite this repository" widget on the project page.

## BibTeX

```bibtex
@software{eidolon_hermes,
  author  = {Shag (Pixel Rainbow)},
  title   = {Eidolon: Self-Improvement Soul for Hermes Agent},
  year    = {OPERATOR_INPUT_REQUIRED_ON_RELEASE_TAG},
  version = {OPERATOR_INPUT_REQUIRED_ON_RELEASE_TAG},
  license = {Apache-2.0},
  url     = {https://github.com/shagghiesuperstar/Eidolon-Soul-For-Hermes-Agent-Universal},
  doi     = {OPERATOR_INPUT_REQUIRED_AFTER_FIRST_ZENODO_MINT}
}
```

## APA-style plain-text

> Shag (Pixel Rainbow). *Eidolon: Self-Improvement Soul for Hermes Agent*
> (version OPERATOR_INPUT_REQUIRED_ON_RELEASE_TAG) [Software]. Apache-2.0.
> https://github.com/shagghiesuperstar/Eidolon-Soul-For-Hermes-Agent-Universal

## Placeholder policy

Three fields are placeholders until the first stable release and Zenodo mint:

| Field           | Populated by |
|-----------------|--------------|
| `version`       | Release workflow (`release.yml`) on stable `v*` tag push. |
| `date-released` | Release workflow, same tag push. |
| `doi`           | Operator, once, after the first Zenodo mint. See `RELEASING.md`. |

The placeholders are intentionally noisy strings so a grep like
`grep OPERATOR_INPUT_REQUIRED CITATION.cff` cleanly reports what still needs
attention.

## Validating the CFF locally

```bash
pip install --user cffconvert
cffconvert -i CITATION.cff --validate
# Expected: "Valid CITATION.cff (schema 1.2.0)."
```

Refs: `master_EIDOLON_roadmap(F5).md` § REC-015.
