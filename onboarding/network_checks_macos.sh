#!/usr/bin/env bash
# Read-only DJConnect macOS development-host network and firewall assessment.
set -euo pipefail

readonly DEFAULT_REPORT="$HOME/Library/Application Support/DJConnect/network-checks/network-assessment-$(date -u '+%Y%m%dT%H%M%SZ').md"
REPORT_FILE="$DEFAULT_REPORT"
NO_COLOR=0

usage() {
  cat <<EOF
Usage: $(basename "$0") [--report-file FILE] [--no-report-file] [--no-color] [--help]

Read-only assessment of DJConnect development-host network posture. It checks
known outbound dependencies, listening services, Docker-published ports and
macOS Application Firewall/PF visibility. It never changes firewall rules,
services, credentials or network configuration.
EOF
}
while [[ $# -gt 0 ]]; do case "$1" in
  --report-file) REPORT_FILE="${2:?}"; shift 2 ;;
  --no-report-file) REPORT_FILE='none'; shift ;;
  --no-color) NO_COLOR=1; shift ;;
  --help|-h) usage; exit 0 ;;
  *) printf 'ERROR Unknown option: %s\n' "$1" >&2; exit 1 ;;
esac; done
[[ "$(uname -s)" == Darwin ]] || { printf 'ERROR This assessment runs only on macOS.\n' >&2; exit 1; }

emit() { printf '%s\n' "$*"; }
recommendations=()
add_recommendation() { recommendations+=("$1"); }
report=''
append() { report+="$1"$'\n'; }

append '# DJConnect macOS Network and Firewall Assessment'
append ''
append "- Generated (UTC): $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
append '- Scope: known DJConnect development dependencies and local listeners; not a system-wide traffic capture.'
append '- Mode: read-only; no service or firewall mutation was performed.'
append ''
append '## Outbound dependency checks'
append ''
append '| Dependency | Endpoint | Result |'
append '| --- | --- | --- |'
endpoints=(
  'GitHub|https://api.github.com'
  'GitHub Actions|https://github.com'
  'Docker Hub|https://registry-1.docker.io/v2/'
  'GitHub Container Registry|https://ghcr.io/v2/'
  'Homebrew|https://formulae.brew.sh'
  'PyPI|https://pypi.org'
  'npm registry|https://registry.npmjs.org'
  'Apple software updates|https://swscan.apple.com'
  'Cloudflare API|https://api.cloudflare.com/client/v4'
  'ngrok API|https://api.ngrok.com'
)
for item in "${endpoints[@]}"; do
  name="${item%%|*}"; url="${item#*|}"
  if curl --silent --show-error --location --output /dev/null --connect-timeout 5 --max-time 12 "$url"; then
    append "| $name | $url | reachable |"
  else
    append "| $name | $url | blocked or unavailable |"
    add_recommendation "Allow outbound DNS and HTTPS (TCP/443) to $name when that capability is required."
  fi
done

append ''
append '## Local services and exposed ports'
append ''
append '| Process | Address | Port | Exposure | Recommendation |'
append '| --- | --- | --- | --- | --- |'
listeners="$(lsof -nP -iTCP -sTCP:LISTEN 2>/dev/null || true)"
while IFS= read -r line; do
  [[ "$line" == COMMAND* || -z "$line" ]] && continue
  process="$(awk '{print $1}' <<<"$line")"; endpoint="$(awk '{print $(NF - 1)}' <<<"$line")"
  address="${endpoint%:*}"; port="${endpoint##*:}"; exposure='loopback'
  case "$address" in
    127.*|localhost|::1|'[::1]') exposure='loopback' ;;
    *) exposure='network' ;;
  esac
  recommendation='Keep least-privilege binding; document owner and need.'
  if [[ "$exposure" == network ]]; then recommendation='Confirm this network exposure is required; restrict inbound access with macOS firewall/router rules.'; add_recommendation "Review network-exposed listener $process on port $port."; fi
  append "| $process | $address | $port | $exposure | $recommendation |"
done <<<"$listeners"

append ''
append '## Active TCP sessions'
append ''
append 'This is an endpoint-only snapshot. It deliberately excludes request content, headers, credentials and payloads.'
append ''
append '| Process | Connection | Assessment |'
append '| --- | --- | --- |'
connections="$(lsof -nP -iTCP -sTCP:ESTABLISHED 2>/dev/null | awk 'NR > 1 {for (i = 1; i <= NF; i++) if ($i ~ /->/) {print $1 "|" $i; break}}' || true)"
if [[ -n "$connections" ]]; then
  while IFS='|' read -r process connection; do
    append "| $process | $connection | Review unexpected remote endpoints; retain only required development, relay and tunnel sessions. |"
  done <<<"$connections"
else
  append '| none visible or insufficient permission | n/a | Rerun from an account permitted to inspect local processes if a complete local snapshot is required. |'
fi

append ''
append '## Firewall posture'
append ''
firewall="$(/usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate 2>&1 || true)"
stealth="$(/usr/libexec/ApplicationFirewall/socketfilterfw --getstealthmode 2>&1 || true)"
pf="$(sudo -n pfctl -s info 2>/dev/null | awk -F': ' '/Status:/{print $2; exit}' || true)"
append "- macOS Application Firewall: ${firewall:-unavailable}"
append "- macOS stealth mode: ${stealth:-unavailable}"
append "- PF status: ${pf:-unverified (sudo required)}"
if ! grep -qi 'enabled' <<<"$firewall"; then add_recommendation 'Enable the macOS Application Firewall unless an approved managed firewall provides equivalent inbound protection.'; fi
if ! grep -qi 'enabled' <<<"$stealth"; then add_recommendation 'Consider enabling macOS stealth mode for a portable development host.'; fi
[[ -n "$pf" ]] || add_recommendation 'Run the assessment after sudo authentication to verify PF status, or document the managed firewall boundary.'

append ''
append '## Docker-published ports'
append ''
append '| Container | Published ports | Recommendation |'
append '| --- | --- | --- |'
if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
  while IFS='|' read -r name ports; do
    [[ -z "$name" ]] && continue
    append "| $name | ${ports:-none} | Bind local development services to loopback where supported; expose externally only through approved tunnel/reverse-proxy controls. |"
  done < <(docker ps --format '{{.Names}}|{{.Ports}}')
else
  append '| Docker unavailable | unverified | Start Docker Desktop to assess published local service ports. |'
  add_recommendation 'Start Docker Desktop and rerun this assessment to inspect Home Assistant test-environment exposure.'
fi

append ''
append '## Recommendations'
append ''
if (( ${#recommendations[@]} == 0 )); then
  append '- No conditional recommendation was triggered. Continue to document any intentional network-exposed service.'
else
  for recommendation in "${recommendations[@]}"; do append "- $recommendation"; done
fi

emit "$report"
if [[ "$REPORT_FILE" != none ]]; then
  umask 077; mkdir -p "$(dirname "$REPORT_FILE")"; printf '%s' "$report" >"$REPORT_FILE"; chmod 600 "$REPORT_FILE"; emit "Report written: $REPORT_FILE"
fi
