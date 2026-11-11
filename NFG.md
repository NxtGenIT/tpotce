# NxtGenIT fork of T-Pot

This fork tracks [telekom-security/tpotce](https://github.com/telekom-security/tpotce).
Our changes live on the `nfg` branch; `master` mirrors upstream. The honeypot
hosts are deployed from a pinned commit of `nfg` by the private Terraform repo
`NxtGenIT/nxtfireguard-tpot-honeypot`.

## What differs from upstream

1. **No SNMP, in any edition.** Our hoster (Hetzner) does not allow SNMP
   services. The `161:161/udp` (Conpot IEC104) and `161:161` (qeeqbox
   honeypots) port mappings are removed from every compose file. The Hetzner
   Cloud firewall in the Terraform repo additionally never opens 161/162 (tcp
   and udp), which also keeps honeytrap's catch-all from answering there.
   The images are still upstream's (`ghcr.io/telekom-security`), so their
   Dockerfiles and baked-in configs are unchanged; only what is published and
   started is different.
2. **NFG edition, `compose/nfg.yml`.** The STANDARD edition without a web UI
   and without data sharing:

   | Dropped | Why |
   |---|---|
   | kibana, nginx, map_redis, map_web, map_data, spiderfoot | UI, not needed |
   | ewsposter | sends events to the Telekom community backend |
   | conpot_IEC104 | its template bundles an SNMP agent |

   Elasticsearch and T-Pot's Logstash stay. Logstash parses the honeypot logs
   in `~/tpotce/data/*/log` into `logstash-*`, adding `type`,
   `t-pot_hostname`, geoip and so on. The NxtFireGuard threat feed aggregator
   starts its own `nfg-logstash` on the docker network `tpotce_nginx_local`,
   reads `logstash-*` from `http://elasticsearch:9200` and posts each event to
   the collector's `/t-pot` endpoint, which needs exactly those fields. The raw
   log files alone would not work.

   `compose/nfg.yml` is generated: never edit it by hand, run
   `python3 compose/nfg/generate.py` instead (it also fails if a dropped
   service is still referenced or an SNMP port is published).

## Installing the NFG edition

The Terraform repo's cloud-init does this; by hand it is:

```bash
git clone https://github.com/NxtGenIT/tpotce ~/tpotce
git -C ~/tpotce checkout <commit of nfg>
~/tpotce/install.sh -s -t s            # sensor: needs no web user
cp ~/tpotce/compose/nfg.yml ~/tpotce/docker-compose.yml
sed -i 's/^TPOT_TYPE=.*/TPOT_TYPE=NFG/' ~/tpotce/.env
sudo reboot
```

`TPOT_TYPE=NFG` is deliberate. tpotinit only checks `HIVE` and `SENSOR`:
`HIVE` needs a web user and waits for Kibana forever on first start, and
`SENSOR` needs a hive address. Logstash writes to the local Elasticsearch for
every type except `SENSOR`.

For the aggregator, use
`ELASTICSEARCH_TARGETS='[{"url":"http://elasticsearch:9200","user":"tpot","pass":"unused"}]'`.
T-Pot's Elasticsearch has security disabled, but the aggregator skips a target
with an empty user.

## Syncing upstream

```bash
git fetch upstream
git checkout master && git merge --ff-only upstream/master && git push
git checkout nfg && git merge master
# re-check that no new 161/162 mapping came in, then regenerate:
grep -rnE '"16[12]:16[12]' docker-compose.yml compose/ docker/*/docker-compose.yml | grep -v '#'
python3 compose/nfg/generate.py
git commit -am "chore: sync upstream, regenerate nfg edition" && git push
```

Then bump `tpot_ref` in the Terraform repo (recreates the hosts).
