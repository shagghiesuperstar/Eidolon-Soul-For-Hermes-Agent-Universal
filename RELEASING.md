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

## Release checklist

1. Bump `src/eidolon/_version.py` to the target version (drop `-dev0` suffix).
2. Update `CHANGELOG.md` (create if missing) with the release notes.
3. `git tag -s vX.Y.Z -m "Eidolon vX.Y.Z"` (signed tags preferred).
4. `git push origin vX.Y.Z`.
5. Wait for GitHub Release to auto-publish (or draft one manually via `gh release create`).
6. Verify Zenodo picked up the release → DOI appears in the Zenodo dashboard.
7. Add DOI badge to `README.md` if this is the first stable release.
8. Bump `src/eidolon/_version.py` to next `-dev0` on `main`.

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
