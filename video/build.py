import json
from pathlib import Path
R = Path(__file__).resolve().parent
d = json.loads((R.parent/"data"/"case_results.json").read_text())
keep = {k: d[k] for k in ["pnl","bridge","whale_curve","initiatives"]}
keep["energy"] = {k: d["energy"][k] for k in ["anomaly_start","alert_week_p3"]}
keep["energy"]["series"] = {"P3": d["energy"]["series"]["P3"]}
src = (R/"animation_src.html").read_text(encoding="utf-8")
(R/"animation.html").write_text(src.replace("/*__DATA__*/", json.dumps(keep, separators=(",",":"))), encoding="utf-8")
print("ok")
