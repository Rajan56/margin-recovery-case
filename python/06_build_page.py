"""
06_build_page.py
----------------
Builds the single self-contained index.html (for GitHub Pages) from
site/template.html + site/app.js + data/case_results.json + the agent draft.

Run:  python 06_build_page.py <github-username>
"""
import json
from pathlib import Path

import sys
GH_USER = sys.argv[1] if len(sys.argv) > 1 else "YOUR-USERNAME"
REPO_URL = f"https://github.com/{GH_USER}/margin-recovery-case"
LINKEDIN_URL = "https://www.linkedin.com/in/rajan-kumar-v-k-0a541799/"

ROOT = Path(__file__).resolve().parent.parent
tpl = (ROOT / "site" / "template.html").read_text(encoding="utf-8")
app = (ROOT / "site" / "app.js").read_text(encoding="utf-8")
data = json.loads((ROOT / "data" / "case_results.json").read_text())
draft = (ROOT / "docs" / "variance_commentary_draft.md").read_text(encoding="utf-8")

html = (tpl.replace("/*__DATA__*/", json.dumps(data, separators=(",", ":")))
           .replace("/*__DRAFT__*/", json.dumps(draft))
           .replace("/*__APP__*/", app)
           .replace("__REPO_URL__", REPO_URL)
           .replace("__LINKEDIN_URL__", LINKEDIN_URL))
(ROOT / "index.html").write_text(html, encoding="utf-8")
print(f"index.html written ({len(html)/1024:.0f} KB)")
