#!/usr/bin/env python3
"""Generate compose/nfg.yml (the NxtGenIT edition) from compose/standard.yml.

Run from the repository root after every upstream sync:

    python3 compose/nfg/generate.py

The NFG edition is the STANDARD edition without anything that serves a UI or
sends data elsewhere, and without SNMP:

- kibana, nginx, map_redis, map_web, map_data, spiderfoot: web UI, not needed;
  events leave the host through the NxtFireGuard threat feed aggregator, which
  reads Elasticsearch over the docker network tpotce_nginx_local.
- ewsposter: submits events to the Telekom community backend.
- conpot_IEC104: its template bundles an SNMP agent; our hoster does not allow
  SNMP. (The other conpot templates have no SNMP.)

Elasticsearch and T-Pot's own Logstash stay: Logstash parses the honeypot log
files into logstash-* (adding type, t-pot_hostname, geoip, ...), which is the
format the collector's /t-pot endpoint expects.

Text-based on purpose (no YAML round trip), so upstream comments and
formatting survive and the diff against standard.yml stays readable.
"""
import re
import sys
from pathlib import Path

DROP_SERVICES = {
    "kibana", "nginx", "map_redis", "map_web", "map_data", "spiderfoot",
    "ewsposter", "conpot_IEC104",
}
DROP_NETWORKS = {"ewsposter_local", "spiderfoot_local", "conpot_local_IEC104"}

root = Path(__file__).resolve().parents[2]
src = (root / "compose" / "standard.yml").read_text().splitlines(keepends=True)

out, section, skipping, pending = [], None, False, []
for line in src:
    if re.match(r"^[a-z]", line):  # top-level key
        section = line.split(":")[0]
        skipping = False
    m = re.match(r"^  ([A-Za-z0-9_]+):\s*$", line)
    if section == "networks" and m:
        if m.group(1) in DROP_NETWORKS:
            continue
    if section == "services":
        if m:
            skipping = m.group(1) in DROP_SERVICES
            if skipping:
                pending = []  # drop the block's own header comment
        if line.startswith("#") or line.strip() == "":
            # comments/blank lines belong to the next block; hold them back
            if not skipping or line.startswith("#"):
                pending.append(line)
            continue
        if skipping:
            continue
        out.extend(pending)
        pending = []
    out.append(line)
out.extend(pending)

text = "".join(out).replace("# T-Pot: STANDARD", "# T-Pot: NFG (generated from standard.yml by compose/nfg/generate.py, do not edit)", 1)

# Guards: nothing dropped may still be referenced, and no SNMP port published.
for name in DROP_SERVICES:
    if re.search(rf"^\s+{name}:\s*$", text, re.M) or re.search(rf"^\s+-\s+{name}\s*$", text, re.M):
        sys.exit(f"{name} is still referenced in nfg.yml")
if re.search(r'^\s+-\s+"[^"#]*:16[12](/udp)?"', text, re.M):
    sys.exit("nfg.yml publishes an SNMP port (161/162)")
if "nginx_local" not in text:
    sys.exit("nginx_local network missing: the aggregator joins tpotce_nginx_local")

(root / "compose" / "nfg.yml").write_text(text)
print("wrote compose/nfg.yml")
