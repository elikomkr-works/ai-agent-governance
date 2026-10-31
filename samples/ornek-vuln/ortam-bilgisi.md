# Customer intake answers — sample order "musteri-portal"

Sample input for the `vuln-triage` skill. This is the customer's own written answer to the
intake questions (`tools/intake.py vuln-triage standard`), kept verbatim: it is the only
source for asset identity, exposure and existing mitigations. Everything not written here is
unknown, and a finding that depends on it stays `[DOĞRULANMAMIŞ]`.

## Assets in the scanner export

| Address in the export | What it is | Reachable from the internet | Notes from us |
|---|---|---|---|
| 192.0.2.21 | `web01`, public order portal (nginx in front, Apache behind it) | yes, ports 80 and 443 only | Port 8080 and 8443 are bound to localhost and only reachable through the nginx reverse proxy. The scanner reached them because it ran inside the DMZ. |
| 192.0.2.22 | `web02`, staging copy of the portal | no, DMZ only, VPN access for 3 developers | Not in production use. Same image as web01, patched later. |
| 10.10.4.15 | `app01`, internal Java application server (Tomcat) | no | Only web01 may connect to it, on port 8080. |

## Existing mitigations we have already applied

- The nginx reverse proxy in front of web01 strips the `${` character sequence from request
  headers and from the user-agent since December 2021 (WAF rule, we can send the rule text).
- TLS 1.0 is still enabled on 192.0.2.21:443 because one customer integration needs it. We
  know about it; a replacement is planned for Q1 2027.
- The Apache `/server-status` page on web02 is only reachable from the DMZ.
- `svc_scan` is a read-only scan account; it exists only on app01, which is why only that host
  has authenticated results.

## Our own domains

`musteri.example`, `intranet.musteri.example`, `portal.musteri.example`

## The dependency export

`package.json`, `package-lock.json` and the `npm audit --json` output come from the
`musteri-portal` repository, branch `main`, commit of 2026-10-19. It is the code running on
web01 behind the reverse proxy.

What we know about how it is used:

- `ejs` renders the order confirmation page. The template files are in our repository; no
  user-supplied string is ever passed as a template name or as template source.
- `jsonwebtoken` verifies session tokens. We use HS256 with a single static secret; we do not
  accept a key type or an algorithm from the token itself and we do not use a JWKS endpoint.
- `moment` is used in two places to format a date for display. `moment.locale()` is never
  called with a value that comes from a request.
- `lodash` is used throughout the request-handling code, including `_.merge` on parsed JSON
  request bodies.
- `webpack`, `jest` and `nodemon` run on the build machine and on developer laptops only. They
  are not installed on web01; the deployed artifact is the build output.
- `axios` calls one external payment provider API over HTTPS. We do not follow redirects to
  other hosts and we do not set a `Proxy-Authorization` header.

## Package bought

Standard: up to 5 findings may be sent for CVE/advisory enrichment.

## Did anything happen?

No. No alert, no incident, no suspicious behaviour that we know of. The scan was run because
our insurer asked for it.
