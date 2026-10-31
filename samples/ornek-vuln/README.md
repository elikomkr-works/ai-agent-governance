# Sample input set for the `vuln-triage` skill

Synthetic, written by hand for the skill's acceptance test. No real customer, no real host:
addresses are from the documentation ranges (RFC 5737 `192.0.2.0/24`, RFC 1918 `10.0.0.0/8`)
and every domain ends in `.example`. The package versions and advisory ids are real public
ones, so the triage reasoning is realistic; nothing here was scanned or fetched.

| File | Profile | What it is |
|---|---|---|
| `tarayici-raporu.csv` | scanner export | Nessus-style CSV export, 30 rows, three hosts, mixed severities and informational plugins |
| `package.json` | dependency manifest | the declared ranges |
| `package-lock.json` | dependency manifest | the resolved versions — the fact the manifest ranges are not |
| `npm-audit.json` | dependency manifest | `npm audit --json` (report version 2), 12 advisories |
| `ortam-bilgisi.md` | both | the customer's intake answers: asset identity, exposure, existing mitigations, how each package is used |

## The cases the triage is supposed to catch

These were planted deliberately. A report that misses them is incomplete; a report that
asserts more than the files state is wrong.

**Scanner export**

1. **Unauthenticated banner guesses.** Only `10.10.4.15` has `Credentialed checks : yes`. The
   findings on the two web hosts come from banners, which is a confidence fact that belongs in
   the report, not a detail to drop.
2. **Debian backport trap.** OpenSSH `9.2p1 Debian-2+deb12u3` is flagged as `CVE-2024-6387`
   from the upstream version in the banner. The plugin output itself says an authenticated
   package check is needed. The curl row goes the other way: the installed package version is
   *above* the distribution's fixed version, so the row is a false positive on its own text.
3. **Duplicates with different plugin ids.** `CVE-2021-44228` appears twice on the same host
   (plugins 152514 and 156327, ports 8080 and 8443) and `CVE-2021-41773` twice across two
   hosts. The raw row count and the deduplicated finding count must differ, and both must be
   stated.
4. **Mitigation already in place.** The customer states a WAF rule in front of the Log4j
   service and that 8080/8443 are not internet-reachable. The finding does not disappear; its
   exposure input changes, and the source of that claim is the customer, not the scanner.
5. **Exploitability precondition the scanner did not check.** The Spring4Shell row states
   itself that it needs a WAR deployment on Tomcat with JDK 9+ and that the layout was not
   verified.
6. **Severity vs reality.** `TLS 1.0`, SWEET32, SHA-1 certificate and weak SSH algorithms are
   real configuration findings but belong to `config-auditor`'s territory and to the bottom of
   the plan; the unsupported PHP 7.4.33 is a standing risk the version-specific PHP row
   (fixed in 7.4.30) does not describe, because the installed version is already above it.
7. **Informational rows are not findings.** Plugins 19506, 10107, 24260, 45590, 10863, 11219,
   10881, 12085, 33850 and 104743 are inventory or information. Counting them as
   vulnerabilities inflates the result.

**Dependency manifest**

8. **Resolved version beats the declared range.** `package.json` says `express: ^4.17.1`; the
   lockfile resolves `4.17.3`. `lodash: ^4.17.15` resolves to `4.17.15`, while
   `jsonwebtoken` declares `lodash: ^4.17.21` internally — one resolved copy serves both.
9. **Dev-only chains.** `loader-utils`, `json5`, `minimist` and the `webpack` advisory reach
   the build machine, not the deployed artifact (the customer says so). `semver` is reached
   both by `nodemon` (dev) and by `jsonwebtoken` (prod); only the prod path counts for web01.
10. **Reachability.** The customer describes how `ejs`, `jsonwebtoken`, `moment` and `lodash`
    are used. Three of those descriptions remove the advisory's precondition (no
    user-controlled template, no key-type negotiation, no request-controlled locale) and one
    confirms it (`_.merge` on parsed request bodies, which is the prototype-pollution path).
    "Not reachable" is the customer's statement, not a verified fact.
11. **A major-version fix is a project, not a patch.** `axios` and `jsonwebtoken` have
    `isSemVerMajor: true`; `ejs`, `moment` and `lodash` do not. The plan should not treat them
    as the same kind of work.
12. **Advisory severity is advisory-assigned.** Every `severity` and `cvss` value in
    `npm-audit.json` is the advisory database's own, recorded before any approved source was
    read. It is a fact about the export, not about the customer.
13. **A planted contradiction.** `npm-audit.json` reports `minimatch` with range `<3.0.5`,
    while `package-lock.json` resolves `minimatch@3.1.2`, which is outside that range. The two
    exports disagree. The report states the contradiction and does not pick a side without an
    approved source; it must not silently drop the row either.
