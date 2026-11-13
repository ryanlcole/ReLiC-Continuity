# ReLiC IS browser entrance — review-stage public shell

This is a static, client-only demonstrator for the owner's proposed browser-first entrance to ReLiC Infrastructure System. It lives separately from the existing private Grimoire M1 local pilot and does not replace or connect to that project.

## Flow

1. Browser BIOS: reports only browser-exposed facts; enumerates relevant available site capabilities and consent preferences. No permission prompts fire on load.
2. Save / Save & Continue / Cancel / Exit / Fullscreen buttons; preferences (booleans only) use localStorage when available. Unsupported APIs are shown unavailable, not faked. A webpage cannot press F11 or override platform permissions.
3. Connection panel: navigator.onLine, Network Information API hints when provided, navigation timing and a short animation-frame sample. The user may explicitly run three same-origin HEAD requests. This is not a scientifically validated connectivity or stability audit.
4. Binary bridge: a RION-DEMO-v1 data structure with known, sign, selected, source and verified fields is serialized to UTF-8 and represented as binary bits. This is an illustration written in ordinary JavaScript: it is not a verified production Rion, physics computation, or RuneCore engine.
5. ReLiC surface: original full-viewport inline SVG image and a single conversational section. Consent-gated, temporary session-only prompts collect an alias, device label and factor preference. They do not collect biometric samples, passwords, legal identity, or serial numbers.
6. No actual identity verification or role authorization. STATUS, HELP, INFRASTRUCTURE, and CANCEL are local deterministic demo commands; all other commands refuse execution.

## Preview locally

Serve the folder via any static server:

    python3 -m http.server 8012 --directory docs/portal

Then open http://127.0.0.1:8012/ on the SAME computer. Opening local files is possible but HTTP is recommended for more reliable API behavior.

## GitHub Pages deployment

Review and merge the feature PR first. In the ReLiC-Continuity repository, visit Settings → Pages → Build and deployment → Deploy from a branch, choose main and /docs, and save. After GitHub confirms the deployment, the intended public URL is:

https://ryanlcole.github.io/ReLiC-Continuity/portal/

Do not claim the link is live until GitHub Pages is enabled and the URL is independently opened. Published GitHub Pages are public websites. Keep sensitive records and real authentication off the static site.

## Security and scope

- No AWS, external fonts, third-party analytics, remote scripts, API requests to other origins, or automatic use of mic, camera, geolocation, or biometrics.
- Preferences contain only site feature choices. Identity profile stays in in-memory JavaScript and is discarded on a page reload or return to BIOS.
- The static portal cannot provide production identity proof, hardware attestation, persistent permission grants, a secured verifier, a ReLiC MCP ledger, or integration with the old private project database.
- HTTPS from Pages is required for many permissioned APIs but does not by itself provide authorization or verified presence.
- Network hints and API availability can be misleading. Unknown remains unknown.
- Do not claim any ReLiC history receipt from this branch or any automated CI test.
- Release gates: tests, owner review, hosting choice, manual iOS/desktop interaction test, and security review before any authenticated system is introduced.

## Provenance and separation

The archived Rion / Predict standalone source describes Rion and RuneCore as hypotheses or experimental code rather than a deployed full engine. The public ReLiC Continuity repository is an independent community reference implementation, not the private original service. This portal follows those boundaries.

Existing M1: ryanlcole/Grimoire PR #2, relic_is_m1/, independent localhost-only synthetic job example. Neither code nor data is modified here.
