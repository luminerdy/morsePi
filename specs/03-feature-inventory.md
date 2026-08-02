# 03 — Feature Inventory

Tiers: **MVP** (Phase 1–3), **V1** (Phase 4), **V2** (Phase 5–6). See
[12-rebuild-roadmap.md](12-rebuild-roadmap.md) for phases.

| ID | Feature | Tier | Legacy source reviewed through `7818254` |
|---|---|---|---|
| F-01 | Text↔Morse conversion (A–Z, 0–9, `. , ? !`) | MVP | `morse.py` |
| F-02 | Telegraph key input + live decode | MVP | `app.py` key handlers |
| F-03 | Speaker + LED Morse playback, Farnsworth timing | MVP | `app.py` audio/LED helpers |
| F-04 | Timing settings (char WPM, effective WPM, tone Hz) | MVP | `/timing-settings` |
| F-05 | Send practice (key the shown letter) | MVP | `/practice` mode=send |
| F-06 | Listen practice (identify played letter) | MVP | mode=listen |
| F-07 | Per-letter progress tracking + progress page | MVP | `practice_progress.py`, `/progress` |
| F-08 | Local backup + rotation | MVP | `scripts/backup_data.py` |
| F-09 | Read, Echo, Learn practice modes | V1 | modes read/echo/learn |
| F-10 | Letter-unlock curriculum with burn-in gates | V1 | `letter_unlock_steps`, learning state |
| F-11 | Multi-student profiles + guest (disposable) profile | V1 | `student_profiles.py` |
| F-12 | Touchscreen flow (`/touch/*`) with idle timeout | V1 | touch templates |
| F-13 | Daily Mission + celebration | V1 | daily summary routes |
| F-14 | Adaptive slowdown for struggling listeners | V1 | `get_practice_timing` |
| F-15 | Word practice (unlocked after S, O) | V2 | words routes |
| F-16 | Badges, coach recommendations, effort tracking | V2 | summaries in `app.py` |
| F-17 | Signal Sprint bonus round | V2 | `/bonus/*` |
| F-18 | Admin: student reset, session recovery | V2 | `/students`, `/admin/sessions` |
| F-19 | S3 backup/status sync | V2 | `backup_data.py --s3-uri` |
| F-20 | Unattended auto-update (release branch + health check) | V2 | `scripts/update_station.sh` |
| F-21 | Rhythm timing analysis + admin trends view | V2 | `practice_attempts.timing_summary`, `/admin/rhythm` (added `674fdd8`) |
| F-22 | Dependency preflight check | MVP | `scripts/check_dependencies.py` (added `7818254`; rebuild moves this to app startup per TR-008) |
| F-23 | Touch System page for Wi-Fi status, on-screen keyboard launch, app update, Wi-Fi restart, and kiosk escape | V1 | `/touch/system` |
| F-24 | Kid-friendly family messages: touch/keyer composition, letter-by-letter review, inbox, and guided decoding | V2 | `message_store.py`, `/touch/messages/*`, touch message templates (Phase 7A local delivery) |
| F-25 | Durable student-addressed message delivery across stations, with S3 storage and optional AWS IoT arrival notices | V2 | Planned Phase 7B |

Notes:

- F-18's *student reset* portion ships earlier than session recovery if V1
  multi-student deployment needs it; both remain PIN-gated (SEC-002).
- No feature above is being dropped — the tiers only order the rebuild.
- F-24 is implemented for students available on the same station. F-25 remains
  the Phase 7B boundary for durable delivery between homes.
