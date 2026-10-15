# Qualified direct local HTTP/WS policy v1

Assignment: `DJC-CORE-HYBRID-LOCAL-HTTP-WS-FIX-V1-20261015`.
Base: `62c8156db376c679eb636a7c8ff4d088276632e9`; same existing Core writer.
Owner requirement and forwarding approval were verified from the actual human
messages in the existing Apple task (reply01a1412e-7d38-74f2-ad25-96641ab78b9e).
This contract precedes runtime changes. It defines qualification, not an
advertisement that this implementation or installed LAN acceptance has passed.

## Scope and trust boundary

Direct internal HTTP and WS are supported targets. External access retains
HTTPS/WSS and normal server identity validation. No TLS proxy, certificate,
firewall, router, Docker networking, HA service or global trust change belongs
to this Core repair. Ordinary device pairing, installation identity, Profile,
source authorization, operation identities/receipts, revocation, expiry and
no-store fences remain mandatory on either route. No second dispatcher or
planner, HA credential issuer, insecure cross-origin fallback or blind retry.

All four hybrid HTTP routes and the paired action WebSocket use one ingress
policy before credentials or request bodies are read. Existing legacy routes
and the separate Broadcast audience are unchanged.

## Local admission: every condition is required

1. The actual socket peer comes from `request.transport` peername, independently
   of the forwarded middleware's `request.remote`. Missing/invalid peers fail.
2. A direct loopback peer is local. Otherwise the peer must be an RFC1918 IPv4
   or IPv6 ULA/link-local address on an enabled HA interface's actual subnet,
   using HA's existing public network adapter helper and configured prefix.
   Being merely private or arriving through a bridge is insufficient.
3. The request origin must equal an existing qualified internal HA origin,
   including HTTP scheme and port. Use HA's supported internal URL selection
   restricted to this request, with external/cloud URLs excluded. Never derive
   trust from Host alone or accept arbitrary user-supplied URLs.
4. Plaintext containing Forwarded, X-Forwarded-*, X-Real-IP, Via or known cloud
   forwarding headers is rejected. A trusted proxy's rewritten remote address
   cannot turn a proxied request into a direct local request.
5. If Origin is present, it must be a single exact same internal origin. Null,
   opaque, credentials, paths, queries, fragments, foreign origins and different
   ports are rejected. Native requests may omit Origin; pairing still applies.

IPv4-mapped IPv6 is normalized before network comparison. Public/reserved peer
addresses, mismatched private subnets and unknown network configuration fail
closed. HTTPS preserves the existing HA trusted-proxy/TLS and same-Origin path;
this policy does not accept new proxy headers or install new trusted proxies.
No sensitive headers, raw tokens, user content or full requests enter evidence.

## Docker and deployment qualification

An ingress that erases source identity cannot qualify merely by allowing its
NAT gateway. Current HA-dev has no configured internal URL and Docker presents
connections as192.168.65.1 to the container interface172.18.0.2. This is not proof
of a direct LAN client. Such a route remains unqualified until actual ingress
preserves the required peer/configuration evidence. This repair must not silently
add a gateway exemption or report a physical LAN PASS from loopback tests.
Deployment topology changes, if needed, retain their own actual authorization.

## Compatible capability and context

Keep top-level hybrid `requires_authenticated_tls:true` as the conservative
legacy client instruction. Add a versioned `transport_security` policy:
`policy_version:1`, `external:"authenticated_tls"`,
`local_plaintext:"qualified_direct_only"`,
`peer_policy:"enabled_interface_subnet_or_loopback"`,
`internal_origin_required:true`, `forwarded_plaintext:"forbidden"`.
This describes a condition, never permission to release a secret to an address.

After ordinary owner authentication, HTTP context and WS auth_ok additionally
return that policy plus `mode:"authenticated_tls"` or
`mode:"qualified_direct_http"`. Only the latter may report
`requires_authenticated_tls:false` for this already qualified request.
Installation ID, operation epoch, lifetime and operation/read sets are unchanged.
A client must first qualify its own configured/paired local route; capabilities
or an unauthenticated response alone cannot create trust. Old consumers continue
to require TLS. Updated Apple consumers map qualified HTTP to WS, HTTPS to WSS,
retain installation-ID checks and never downgrade an external route.

## Acceptance and evidence boundaries

Prove real owner pairing, HTTP context, WS auth, read, operation/status and
reconnect on a direct qualified local route, alongside existing TLS qualification.
Provider I/O may be a fixture; ingress, pairing, dispatch and journals may not.
Negative cases include public peers with forged internal Host/Origin, other
private subnets, missing peer/config, Docker gateway, forwarding/cloud headers,
null/foreign/malformed/multiple Origin, missing/invalid paired credentials,
revocation and installation mismatch. All routes share the same rejection.
An unqualified HTTP request retains426 transport_security_required; an invalid
Origin retains403 origin_not_allowed. No redirect or HTTP mutation retry.

Before delivery run existing hybrid journal/service, owner security and relevant
regressions; independently review exact code and privacy/experience claims.
Native LAN/cellular/LAN behavior belongs to the existing Apple writer. Isolated
Core, installed Core, physical Apple and joint acceptance remain separate.
No Swift/receiver writes or source publication occurs from this design alone.
