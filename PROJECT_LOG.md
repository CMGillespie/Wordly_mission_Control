# Wordly Mission Control — Project Log

**Timestamp:** September 2, 2026
**Author context:** Built by Chris Gillespie (Sales Engineer, Wordly Inc.) with Claude (Cowork), field-tested live at a show.

---

## What This Is

Mission Control is a single-page web dashboard that gives one live, browser-based view of every session on a Wordly account — replacing the manual Wordly portal workflow of clicking into sessions one at a time. It runs on any device with a browser, phone included, and was purpose-built for the operational reality of managing dozens of simultaneous Wordly sessions during a live multi-room event (conferences, trade shows).

**Core problem it solves:** the Wordly portal is a one-at-a-time interface. Ending a session, splitting a transcript, or just checking whether a room is still live means navigating into that specific session's page. At scale — 40+ concurrent sessions, rooms 10 minutes apart on foot, several transcript splits needed simultaneously at the top of every hour — that interface does not scale operationally. Mission Control condenses all of that into one list with bulk actions and live status.

## What It Does

- Pulls every session on the account into a single searchable, filterable table (title, session ID, or label/custom field).
- Shows live status at a glance: LIVE (green), ENDED (grey), CREATED/never-started (red, hidden by default).
- Filter by Active or Inactive with a single click on the count boxes (no separate checkbox).
- One-click Attend / Present links per session.
- **Bulk Split Transcript and Bulk End Session**: arm the action, checkboxes appear on live sessions, select as many as needed, fire once — replacing the "click into each session individually" workflow that doesn't scale past a handful of rooms.
- **Drop alerting**: if a session that was live silently disappears (not ended intentionally through this tool — e.g., dropped connection, ended in the portal by someone else, room AV failure) it raises an in-page banner, an audio beep, and a browser notification. Built specifically because a room can drop and, if no one is watching that exact session, it can go unnoticed for the length of a 10-minute walk across a venue.
- Approximate "Ended [time]" stamps on sessions, observed client-side (accurate to the ~30-second sync interval, not authoritative — see Known Limitations).

## How It Works (Architecture)

**Stack:** Python (Flask) backend serving a single self-contained HTML page with vanilla JS + Tailwind (CDN) for the frontend. No build step, no frontend framework, no database — it is a live pass-through view of Wordly's own state, not a system of record.

**Two separate Wordly integration surfaces, used for different purposes:**

1. **REST API (v1.11.0)** — `GET /sessions`, authenticated via `x-wordly-api-key` header — used purely for *discovery* (what sessions exist, their state, title, passcode, labels). Two production gotchas discovered and worked around:
   - The endpoint paginates at a default of 10 results/page. The backend now loops pages (`limit=100` each) using the response's `total` field until everything is collected — the original build only ever requested page 1, which is why sessions silently went missing from the list at scale.
   - The Swagger docs say to send an `x-wordly-api-version` header; doing so causes auth failures. It must be omitted (confirmed by Wordly's own CTO, documented as a platform-wide gotcha).

2. **WSS Endpoint Services** — used for *control actions* (End Session, Split Transcript). No API key involved here at all — auth is session ID + passcode only, sent in a `connect` message. Both actions use a lightweight "bystander" connection: connect, send one control message, done — no audio is ever streamed. Two things worth flagging for the platform conversation:
   - **End Session** (`{"type":"disconnect","end":true}`) was already documented behavior.
   - **Split Transcript** (`{"type":"split"}`) was *not* in the reference documentation available at build time — it was discovered by reverse-engineering a Chrome extension Wordly built internally (`wordly-chrome-capture`) and then **confirmed working via direct live testing** against a real session before being wired into the app. It works from the same lightweight bystander connection as End Session, without needing to be the actual audio-presenting client — an important, previously-undocumented fact about how Endpoint Services authorizes control commands.

**Auth / key handling:** No credentials are stored server-side, in a file, or in the deployed container at all. The Wordly API key is entered by the user directly in the browser (a blocking "enter your key" gate on first load, or a small popover afterward) and held in the browser's `localStorage`, sent as a header on each request to our own backend, which relays it to Wordly. It self-clears at midnight (checked on page load/focus, not just a timer, since backgrounded mobile tabs don't reliably fire JS timers overnight) and on manual logout. (Storage was switched from `sessionStorage` to `localStorage` after field testing showed iOS Safari/Chrome aggressively clear `sessionStorage` on tab backgrounding — a real reliability problem during live use.)

**Bulk action UX pattern:** click Split or End once to "arm" that action (auto-filters to active sessions, checkboxes appear on eligible rows); select targets; click the same button again to fire, gated by a lightweight "type asdf to confirm" prompt (a fat-finger guard, explicitly not a security control). Only one action can be armed at a time.

**Drop detection:** the frontend diffs the set of active session IDs between each 30-second poll. Any session that drops out of that set *without* having been ended through this app's own End button is treated as an unexpected drop and alerted on. Sessions the user intentionally ends through the app are tracked separately so they never generate a false alarm.

## Where It Runs, and Why

- **Hosting:** Google Cloud Run (project `support-467322`, region `us-central1`), chosen because Chris already had GCP infrastructure and Cloud Build credentials in place for other internal tools — no new platform dependency introduced.
- **Deployment:** containerized via a Dockerfile (Python 3.11-slim + gunicorn), built and deployed directly from source with `gcloud run deploy --source .` (Cloud Build handles the image build server-side — no local Docker required).
- **Source control:** GitHub, `CMGillespie/Wordly_mission_Control`, single-branch (`master`). The whole application currently lives in one file (`app_v3.py`) plus `Dockerfile`, `requirements.txt`, and `Procfile`.
- **Access:** deployed with `--allow-unauthenticated` — the service is publicly reachable by anyone with the URL. The only access control is knowledge of the URL plus possession of a valid Wordly API key. This was an accepted tradeoff for a small internal team's use during a live show, not a decision suitable for a broader/public rollout as-is (see below).

## Known Limitations (relevant to broader platform planning)

- **No authentication layer** beyond the URL + Wordly API key. Fine for "me + a few trusted teammates"; not fine at any larger scale or external-facing use without adding a real auth gate.
- **No persistence layer.** It is a live mirror of Wordly's own session state — nothing is stored, no history, no analytics. Anything beyond "what's happening right now" would need a database added.
- **Single API key per browser**, entered manually — no multi-account/multi-tenant concept, no SSO, no per-user permissions.
- **End-timestamps are approximate**, observed by this app's own polling loop (~30s resolution), not pulled from Wordly's authoritative record (that data exists but only via the separate `/transcripts` endpoint, and only when a session's transcript-access setting isn't "none").
- **Split Transcript depends on an undocumented Endpoint Services command** confirmed via direct testing rather than official documentation — if Wordly changes that behavior, this app's Split feature would need to be revalidated.
- **Cloud Run's free-tier-style instance sleeps after inactivity** — first load after idle time can take 30-60 seconds to wake up.
- **Built and iterated rapidly** as a tactical field tool (this session, plus live show feedback), not yet hardened with automated tests, CI, or a formal release process.

## Why It's Relevant to the Broader Platform Play

This project is a working proof that Wordly's platform can be operated as a *fleet*, not a set of individual sessions — real-time discovery across every session on an account, bulk control actions that don't officially exist in the documented API surface, and live operational alerting, all built on top of Wordly's existing REST + WSS primitives without needing anything new from Wordly's side. That's the architectural pattern worth carrying into the broader platform conversation: a control-plane layer over Wordly's session primitives, independent of the portal, that could be extended toward multi-tenant, persistent, and properly access-controlled as the scope grows.
