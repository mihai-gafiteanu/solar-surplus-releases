# Security Policy

This is the public face of solar-surplus: the release artifacts a
Raspberry Pi installs, and the documentation site served from this
repo's root. The source repo is private — this is where the things you
can download live, and this is where to report.

The system itself is one household's Pi: evcc charging a car from PV
surplus, InfluxDB and Grafana for the history, a nightly maintenance
window, and a small LAN listener behind the wall board's two buttons.
The documentation site tells the whole story.

## Supported versions

The latest published release, and only it. Published release assets
are never retro-patched — a security fix rides the next release like
any other change, and an installed Pi on the nightly window picks it
up within a day. The install ladder verifies the deb's sha256 before
installing and stops on a mismatch, and CI refuses to publish a tag
that disagrees with the source tree's own RELEASE constant.

## The trust model, stated so reports can aim at it

- Every service door is a LAN door; nothing is deliberately published
  to the internet.
- The listener's bearer token guards against stray LAN requests, not
  against people: the dashboard carries it by design, readable by
  anyone who can open the board. The listener's sudoers user is
  granted exactly two commands — start the maintenance window, write
  the log's clear marker — held character for character by the
  release's own selftest.
- Grafana renders the board's own HTML buttons with sanitization off
  (`GF_PANELS_DISABLE_SANITIZE_HTML`), the documented trade of a
  single-admin board.

A report that breaks one of those lines — the token letting a stranger
do more than the two commands, the listener answering beyond its
guards, an update installing without its sha256 proving out — or
anything in the published artifacts or this site that could hurt the
people who download them, is exactly what this file is for. A report
that restates a documented trade will be read, and answered with the
paragraph above.

## Reporting a vulnerability

Use **Report a vulnerability** on this repository's
[Security tab](https://github.com/mihai-gafiteanu/solar-surplus-releases/security/advisories/new)
— the report is private to you and the maintainer. Please do not put
vulnerability details in public issues.

One person maintains this. Expect an acknowledgement within a few
days; a confirmed fix ships as the next release, versioned and
verified like every other.
