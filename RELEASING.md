# Releasing Eidolon

## Versioning

Eidolon uses semantic versioning (`vMAJOR.MINOR.PATCH`) for its own releases.

Note: this is **different** from the host Hermes Agent, which uses **CalVer**
(`vYYYY.M.D[.patch]`). Eidolon's `hermes_version` doctor check treats Hermes
versions as dates, not SemVer — see `src/eidolon/checks/hermes_version.py`.

## Tags → DOIs

Zenodo minting is enabled for this repository. To keep the DOI history
meaningful, the tagging convention is:

| Tag pattern                       | Zenodo action              |
| --------------------------------- | -------------------------- |
| `v1.2.3`                          | Mints a new DOI            |
| `v1.2.3-rc1`, `v1.2.3-beta1`, etc | **Do NOT publish** on Zenodo |
| `v1.2.3-dev*`                     | Never tagged; dev only     |

The Zenodo GitHub integration triggers on any tag by default. To skip a
prerelease, in the Zenodo UI: "Upload" → find the pending draft → discard it
before hitting Publish. Only stable `vX.Y.Z` tags should be published.

## Packaging pipeline (REC-007)

`eidolon-hermes` publishes to TestPyPI on every `main` push and to real PyPI
on every stable `v*` tag. Publishing uses **PyPI Trusted Publishing** (OIDC);
no API tokens are stored in the repository or in secrets.

| Trigger                | Target       | Environment  | Approval           |
| ---------------------- | ------------ | ------------ | ------------------ |
| push to `main`         | TestPyPI     | `pypi-test`  | none (auto)        |
| tag `vX.Y.Z` (stable)  | PyPI         | `pypi-prod`  | GitHub env review  |
| tag `vX.Y.Z-rc*`, etc  | (build only) | —            | never uploads      |

Workflow: `.github/workflows/release.yml`. The `publish-pypi` job's `if:`
filter skips any tag containing `-` (rc, beta, dev), so prereleases never
reach real PyPI even if the environment gate is approved by mistake.

## Release checklist

1. Bump `src/eidolon/_version.py` to the target version (drop `-dev0` suffix).
2. Update `CHANGELOG.md` (create if missing) with the release notes.
3. Commit and merge to `main` — wait for `release.yml` to publish to TestPyPI
   successfully. Verify at https://test.pypi.org/project/eidolon-hermes/.
4. `git tag -s vX.Y.Z -m "Eidolon vX.Y.Z"` (signed tags preferred).
5. `git push origin vX.Y.Z`.
6. GitHub Actions pauses at the `pypi-prod` environment gate. **Manually
   approve** the deployment in the Actions UI. Real PyPI upload proceeds.
7. Wait for GitHub Release to auto-publish (or draft one manually via `gh release create`).
8. Verify Zenodo picked up the release → DOI appears in the Zenodo dashboard.
9. Add DOI badge to `README.md` if this is the first stable release.
10. Bump `src/eidolon/_version.py` to next `-dev0` on `main`.

## Prerelease workflow

For `-rc*`, `-beta*`, `-alpha*` tags:

1. Same steps 1–5 as above with the suffixed version.
2. In Zenodo UI, **discard the pending draft** before publishing.
3. GitHub Release should be marked as "pre-release".

## Metadata drift

`.zenodo.json` at the repo root is the source of truth for Zenodo metadata.
Update it when authors, keywords, or descriptions need to change. Zenodo reads
it fresh at each tag, so no manual UI edits are needed for content-only
changes.
