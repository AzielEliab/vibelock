"""The Worker homepage is a product UI, not a downloads shell."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKER = ROOT / "workers" / "download-tracker"
HOMEPAGE = (WORKER / "src" / "homepage.js").read_text(encoding="utf-8")
INDEX = (WORKER / "src" / "index.js").read_text(encoding="utf-8")
README = (WORKER / "README.md").read_text(encoding="utf-8")
ROOT_README = (ROOT / "README.md").read_text(encoding="utf-8")


def test_title_is_product_not_downloads_shell() -> None:
    assert "VibeLock — Aziel Eliab" in HOMEPAGE
    assert "VibeLock downloads" not in HOMEPAGE
    assert '<title>${TITLE}</title>' in HOMEPAGE or "VibeLock — Aziel Eliab" in HOMEPAGE


def test_seo_and_cite_surface() -> None:
    assert 'name="description"' in HOMEPAGE
    assert 'rel="canonical"' in HOMEPAGE
    assert "og:title" in HOMEPAGE
    assert "og:description" in HOMEPAGE
    assert "SoftwareApplication" in HOMEPAGE
    assert 'name="robots"' in HOMEPAGE
    assert "index,follow" in HOMEPAGE
    assert "How to cite" in HOMEPAGE
    assert "Aziel Eliab" in HOMEPAGE
    assert "cite.json" in HOMEPAGE
    assert "function citeDoc" in HOMEPAGE
    assert "zenodo" not in HOMEPAGE.lower()


def test_identity_aziel_eliab_only() -> None:
    forbidden = ("Jane Doe", "John Doe", "Alice Johnson", "Bob Smith")
    blob = HOMEPAGE + INDEX
    for name in forbidden:
        assert name not in blob
    assert blob.lower().count("aziel eliad") == 0
    assert "Aziel Eliab" in HOMEPAGE


def test_interactive_workspace_calls_real_op() -> None:
    assert 'id="workspace"' in HOMEPAGE
    assert "/v1/analyze" in HOMEPAGE
    assert 'id="notes"' in HOMEPAGE
    assert 'id="f-rms"' in HOMEPAGE
    assert 'id="v-block"' in HOMEPAGE
    assert 'id="analyze-btn"' in HOMEPAGE
    assert "Sample tone" in HOMEPAGE
    assert "Sample deepfake" in HOMEPAGE
    assert 'id="score"' in HOMEPAGE
    assert 'id="verdict"' in HOMEPAGE
    assert "reason_codes" in HOMEPAGE
    assert "not a lie detector" in HOMEPAGE.lower()
    assert "courtroom" in HOMEPAGE.lower()


def test_download_install_sigil_kept() -> None:
    assert "/download?asset=" in HOMEPAGE
    assert "One-click install" in HOMEPAGE
    assert "install.sh" in HOMEPAGE
    assert 'src="/sigil.png"' in HOMEPAGE
    assert (WORKER / "public" / "sigil.png").is_file()
    assert "github.com/AzielEliab/vibelock" in HOMEPAGE


def test_readme_names_full_worker_ui() -> None:
    assert "full product UI" in README or "complete product UI" in ROOT_README
    assert "VibeLock — Aziel Eliab" in README or "VibeLock — Aziel Eliab" in ROOT_README
    assert "npx wrangler deploy" in README


def test_worker_serves_cite_and_homepage_module() -> None:
    assert "renderHomepage" in INDEX
    assert "/cite.json" in INDEX
    assert "/llms.txt" in INDEX
    assert "/robots.txt" in INDEX
    assert "incrementUses" in INDEX
