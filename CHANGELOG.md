# Changelog

User-facing changes from the product-documentation transition onward.
Earlier development history is in the [project log](docs/PROJECT_PLAN.md).
These dated entries are not numbered release tags.

## 2026-09-08

### Improved

- Application organized into a domain-based `morsepi/` package; station launch
  commands and data locations remain compatible. Browser asset URLs are unchanged.

- More reliable progress, settings, and message saving, with coordination
  between practice and synchronization to preserve new attempts.
- Damaged JSON is preserved for recovery instead of silently becoming empty
  progress; incomplete attempt records stop further appends.
- Browser request protection and restart-persistent admin PIN lockout.
- Product-oriented README, audience documentation guides, roadmap, contribution
  guidance, and a policy for future numbered pilot releases.

### Verification and Limits

- Security/storage code passed 317 automated tests and GitHub CI; Pappy
  installed release revision `6e64aed`. Remote installations are pending receipts.
- Individual-file durability is improved; full multi-file recovery and remaining
  maintenance scripts still require hardening. See [spec status](specs/STATUS.md).
- Documentation-only changes do not require restarting stations.
