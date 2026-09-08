# 13 - Documentation Plan

Product documentation contract, updated 2026-09-08. DOC IDs are preserved.
The original rebuild consolidation proposal is superseded by audience navigation
first, followed by selective consolidation with compatibility checks.

| ID | Authoritative location | Purpose and status |
|---|---|---|
| DOC-01 | `README.md` | Product benefits, supported target, readiness, and entry points; implemented. Sanitized product imagery remains a follow-up. |
| DOC-02 | `specs/` | Stable requirements and acceptance IDs; STATUS distinguishes implemented, partial, and planned. |
| DOC-03 | `docs/ARCHITECTURE.md`, `docs/architecture/README.md` | Current component/AWS map and design navigation; future package boundaries must be labeled. |
| DOC-04 | `SECURITY.md` | Security boundaries, limitations, and reporting. |
| DOC-05 | `docs/getting-started/README.md` | Installation sequence linking established setup and deployment guides; fresh-SD rehearsal still pending. |
| DOC-06 | `specs/08-data-requirements.md` | Data contract; a comprehensive developer schema guide remains future work. |
| DOC-07 | `docs/administration/README.md` | Navigation to operational runbooks, storage recovery, and activity confirmations. |
| DOC-08 | `docs/MORSE_LEARNING_BEST_PRACTICES.md`, `specs/04-functional-requirements.md` | Pedagogy and behavioral requirements; a consolidated curriculum reference remains future work. |
| DOC-09 | `docs/BILL_OF_MATERIALS.md`, `docs/SETUP_AND_CONFIGURE_PI.md` | Hardware options and wiring; retain working paths and case worksheet. |
| DOC-10 | `CONTRIBUTING.md` | Tested CI environment, mock-GPIO test command, spec-first change process, and data privacy. Do not claim tools not configured in CI. |
| DOC-11 | `docs/history/README.md`, `docs/PROJECT_PLAN.md` | Navigation to dated evidence; original requirements labeled historical. Daily log remains active, not a competing roadmap. |
| DOC-12 | `CHANGELOG.md`, `docs/product/RELEASES.md` | User-facing changes and future release policy. Not currently an updater-consumed release-notes source. |
| DOC-13 | `docs/MESSAGING.md` | Messaging guide; architecture index links the separate cloud contract. |

## Ownership and Compatibility

- Current priorities live only in `docs/product/ROADMAP.md`.
- Audience indexes link existing guides rather than copying their instructions.
- Student handout HTML and PDF remain available; removing the printable PDF is
  not part of this transition. Rebuild it when the source changes.
- Preserve installer-consumed asset paths under `docs/assets/`.
- Before moving a guide, check links in Markdown, HTML, scripts, and tests;
  preserve a forwarding page where outside links may depend on the old path.
- Use fictional students, network names, and station identifiers in new examples.
  Review existing imagery before featuring it in public product material.
- Product changes update requirements first, then implementation status, guides,
  and changelog. Daily logs hold detailed evidence, not the product contract.

## Verification

Check relative document links after navigation changes and before releases.
Distinguish documentation-only changes from device releases: updating guides
does not authorize a station restart or imply remote installation succeeded.
