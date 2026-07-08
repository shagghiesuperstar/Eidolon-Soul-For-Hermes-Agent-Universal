# typed: false
# frozen_string_literal: true

# Homebrew formula for eidolon-hermes (REC-012).
#
# This is the canonical formula. It lives in this repo for review; the tap
# repo `eidolon-hermes/homebrew-eidolon` mirrors this file at
# `Formula/eidolon.rb` on every release (see .github/workflows/release.yml).
#
# On first stable release the release workflow MUST replace:
#   1. `url` — set to the actual PyPI sdist URL:
#      https://files.pythonhosted.org/packages/source/e/eidolon-hermes/eidolon_hermes-<VERSION>.tar.gz
#   2. `sha256` — sha256 of that sdist (drop the PLACEHOLDER value).
#   3. `version` — remove the `version` line once `url` resolves to a real
#      PyPI artifact (Homebrew infers version from the URL).
#
# Until then this formula is inert: `brew install` fails loudly on the
# placeholder sha256 mismatch. See docs/install-brew.md and OPERATOR.md.
class Eidolon < Formula
  include Language::Python::Virtualenv

  desc "Self-improvement layer for Hermes Agent — installs loud, degrades loud"
  homepage "https://github.com/shagghiesuperstar/Eidolon-Soul-For-Hermes-Agent-Universal"
  # PLACEHOLDER: replaced by release workflow on first stable v* tag.
  url "https://github.com/shagghiesuperstar/Eidolon-Soul-For-Hermes-Agent-Universal/releases/download/v0.0.0/eidolon_hermes-0.0.0.tar.gz"
  sha256 "PLACEHOLDER_ON_FIRST_RELEASE_0000000000000000000000000000000000"
  license "Apache-2.0"
  version "0.0.0"

  depends_on "python@3.11"

  # eidolon-hermes has zero runtime Python dependencies (stdlib-first policy
  # enforced by pyproject.toml). No `resource` blocks needed.

  def install
    virtualenv_install_with_resources
  end

  test do
    # Smoke test: entry point works and reports a version.
    output = shell_output("#{bin}/eidolon --version")
    assert_match(/^eidolon \d+\.\d+\.\d+/, output)

    # Doctor command exits non-negative on a fresh install.
    system bin/"eidolon", "doctor", "--json"
  end
end
