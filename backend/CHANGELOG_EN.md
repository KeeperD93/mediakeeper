# Changelog

<!--
[Unreleased] section: accumulate small changes here over time.
When ready to ship, rename `[Unreleased]` to `[x.y.z] - YYYY-MM-DD`
and update APP_VERSION in backend/api/changelog.py.
This section intentionally has no date so it is not shown to users.
-->

## [Unreleased]

### Added
- Scheduler — Emby index scan (recently-added + full), interval configurable.
- Portal — configurable default portal language (admin settings).
- Portal — setting to authorise adult-content requests (off by default).
- Requests — paged navigation with a per-page count selector (10/25/50/100).
- Issues (admin) — ticket queue now paginated (10/25/50/100).
- Portal users (admin) — paginated list (10/25/50/100).
- News (admin) — "Load more" button beyond the 20 most recent.
- Portal users (admin) — user audit log: "Load more" beyond 100 entries.
- Portal users (admin) — user drawer: "Load more" on activity, trophies (XP) and security.
- Portal — configurable donation link for your users (admin settings).
- Dashboard — MediaKeeper support heart in the top bar (Ko-fi, star).

### Changed
- Dashboard — 30 upcoming releases shown (was 20).

### Fixed
- Dashboard — History tabs (Notifications, Duplicates): "Load more" button.
- Dashboard — activity feed: plugin updates now shown in your language.
- Dashboard — avatar and rank ring correct right after login (no refresh needed).
- Requests (admin) — "On behalf of" now defaults to your account.
- Statistics — libraries: real Emby name instead of a sub-folder (auto-repair).
- Issues (admin) — status filter fixed (no longer crashes or is ignored).
- Notifications — saving a Discord webhook no longer fails.
- Notifications — Discord test message follows the configured default language.
- Stats — Users and merge: profile photo (custom or Emby) now shown.
- Stats — active-users hover: names shown instead of raw identifiers.
- Media library — track details no longer fail on a corrupted file.
- Media Manager — undoing a batch rename no longer stops halfway (retry kept).
- Media Manager — rename history labels follow the app language.
- Media Manager — accessible dialogs: keyboard focus, Esc, screen-reader announcement.
- Media Manager — keyboard tabbing skips hidden dialogs and buttons.
- Media Manager — files now line up with their generated names.
- Media Manager — breadcrumb collapses an overflowing path, clearer separators.
- Media Manager — dialog animations disabled when reduced motion is on.
- Dashboard — "Upcoming releases" now shown in your language.
- Dashboard — activity feed (logins, playback) now shown in your language.
- Media library — TMDB detail pages now shown in your language (English fallback).
- Watchlist — series, episodes and synopsis now shown in your language.
- Watchlist — calendar movies now shown in your language.
- Watchlist — calendar month and day names follow the app language.
- Watchlist — followed media (Suivi tab) shown in your language.
- Notifications — toasts (module + now playing) now shown in your language.
- Discord notifications — language follows the portal default.
- TMDB links — open the page in the app language (watchlist, upcoming).
- Dates now follow the app language (instead of the browser).
- Custom avatars now shown in admin topbar, user list and sessions.
- Portal — Discover page: bigger back button, no sticky hover or sideways scroll.

## [1.0.0-rc.4] - 2026-05-30

### Added
- Onboarding wizard — Portal module added to welcome and tour steps.

### Changed
- Dashboard — "Requests" cards renamed to "User Portal".
- Admin UI — refreshed dark theme with stronger text contrast for legibility.
- Avatars — level-colored ring (bronze → legendary) on every surface, matching the leaderboard.
- Buttons — MediaKeeper palette applied (violet, brick red, forest green) without affecting charts.
- Appearance — accent picker temporarily removed (MK palette locked).
- Scheduler — UI reorganised by category with compact single-line rows.
- Startup — boot log: `COOKIE_SECURE=` renamed `COOKIE_HTTPS_FLAG=` (env var unchanged).
- CSRF cookie — allowlist validation on polls (hardening).
- Dashboard — card titles unified on the muted text shade.
- Sidebar — clicking a module opens its sub-menu without leaving the current page.

### Fixed
- Dashboard — upcoming-episodes strip is scrollable by hand under reduced-motion (was frozen and clipped).
- Admin — user audit log shows readable action labels (some actions showed the raw key).
- Admin — user XP history shows readable action labels (admin grant, surprise, trophy).
- Portal — events ticker honours reduced-motion (static instead of scrolling).
- Portal — "Available" badge no longer flickers on freshly added Emby items.
- Image proxy — poster tiles no longer hit 429 when a page renders many at once.
- Portal browsing — availability and request-status checks no longer 429 under heavy scrolling.
- Stats — sessions and 24h actives now show photo + tier ring (leaderboard parity).
- Stats — avatar silhouette now correctly centred inside the tier ring.
- Emby avatars — photo updates reflect within ~5 min (was a 7-day browser cache).
- Login — brute-force tracking now ignores username casing variants.
- Auth schemas now reject unknown JSON keys (defence in depth).
- Events — accepting an invitation no longer triggers a self-collision conflict warning.
- Scheduler — task labels are now translated (FR/EN parity).
- Security — generic, stable error codes across media manager, tools and TMDB.
- Security — media paths validated and contained at every sink (manager, library scans, providers).
- Security — sanitisers made linear-time (ReDoS hardening).
- Image proxy and webhooks — hardened against SSRF and DNS rebinding.
- CSRF cookie — rotation at auth boundaries (session fixation fix).

## [1.0.0-rc.3] - 2026-05-22

### Fixed
- Login flow — onboarding wizard no longer hides the forced password change.
- Onboarding — folders step starts empty (no hard-coded English labels).
- Onboarding — media folders are now optional (configurable later via Settings).

## [1.0.0-rc.2] - 2026-05-22

### Added
- Admin password recovery — `scripts/reset_admin` CLI helper + operations doc.

### Changed
- Startup — cookie security warning now points at the `COOKIE_SECURE=false` LAN escape hatch.

### Fixed
- Login crash on fresh installs — missing `user_profiles.selected_title` migration.
- Login — readable error on validation failure (no more `[object Object]`).

## [1.0.0-rc.1] - 2026-05-21

### Added
- Portal admin — "Reset display name" button (re-arms picker overlay).
- Portal: new "PosterCard" cover component, i18n/tokens compliant (integration prep).
- Settings — new Network section with image cache and DNS cache toggles
- Settings → Scheduler — Cache section (hit/miss stats + Clear button)
- Dashboard — reorder cards on mobile via "Customize" title list
- Settings → Portal — event capacity bounds (admin min/max, step of 5).

### Changed
- Duplicates — streamlined action bar (Detections, Last detection)
- Health — 3 posters per row on mobile, close button repositioned
- Health — back-to-top hidden on Config tab, Analyze button icon unified
- Requests — admin: "Settings" tab moved to first position (default on open)
- Dashboard — default widget layout revised (8 widgets)
- Dashboard — "Streams" card removed (info kept in the top ribbon)
- Dashboard — top ribbon condensed on mobile (3 stats + Services full-width)
- Dashboard — plays/alerts counters removed from activity feed
- Notifications — dropdown full-width on mobile
- Health — toggles redesigned (accent ON slide, harmonized pill)
- Statistics — filter pills unified (accent style)
- Stats: Users and Activity tables readable on mobile (horizontal scroll)
- Series tracking — toolbar redesigned (search, filters, export)
- Notifications — "Enable" checkbox replaced with slide toggle
- Notifications — selects and inputs harmonized (custom chevron)
- Tabs — compacted interface on mobile
- Footer — TMDB credits compacted
- Footer — attribution banner removed (credits kept on About page).
- Avatar menu — accent color picker removed (moved to Settings → Appearance).
- Watchlist — "Restore" button realigned (unified radius)
- Statistics — records stacked vertically on mobile
- Watchlist Missing tab: new "Last scan" label, button renamed "Analyze"
- Watchlist: lighter TMDB attribution, Suivi posters aligned with portal (mobile)
- Dashboard — "Live now" avatars aligned with Users (unified silhouette, hover tooltip)
- Dashboard — mobile stats compacted (34 px icons, 3xs labels, lg values)
- Dashboard — mobile "Customize" trigger moved to the topbar (near bell)
- Topbar — subtitle hidden on mobile, title vertically centred in the band
- Topbar avatar — aligned with user-list cards (photo + silhouette fallback)

### Fixed
- Portal: /availability rate limit raised to 120/min, frontend coalescing, 429 toast dedupe
- Duplicates — tab navigation stabilized (Ignored → History/Rules)
- Duplicates — faster first access, view kept in cache
- Duplicates — "Restore" button realigned on movie rows (Ignored tab)
- Health — config save restored (confirmation toast)
- Expired admin session: silent re-login on Requests, clear notice elsewhere
- Login — username accepted regardless of letter case
- Settings — Cleanup requests and GDPR purge task labels restored (scheduler)
- Portal — mobile poster grids unified across lists (3 cols, 2:3 ratio)
- Dashboard — hero "Play on Emby" deep-link fixed (HTTPS + serverId)

## [0.9.9] - 2026-05-14

### Added
- Admin news — create, edit, delete and schedule entries (start/end dates)
- Customizable Requests maintenance mode
- Requests — configurable auto-cleanup of available requests after N days
- Requests — all-time total under each counter (pending, approved, rejected, available)
- Requests / Users — premium full-width revamp (search, filters, table/card view, bulk actions)
- Users — 7-tab drawer (identity, access, security, activity, trophies, notes, audit)
- Users — roles and granular permissions (chat, requests, problems, lists, offline XP)
- Users — access window (start/end) with 1/3/6/12-month extend shortcuts
- Users — disable the streaming account from the admin (active sessions logged out)
- Users — selective import overlay and manual creation of local-only accounts
- Users — reversible soft-delete, audit log, private admin notes, tags
- Users — per-user GDPR export (JSON) and targeted admin → user notification
- Users — online indicator, < 7 d expiry badge, "never logged in" filter
- Users — automatic deactivation on expiry (sessions killed, dedicated audit)
- About page (stack, licenses) and partner credits under Settings
- Page not found — proper accessible 404 with back-to-dashboard link
- Accessibility — keyboard "Skip to main content" link
- Accessibility — focus traps on 20 modals/overlays (Escape restores focus)
- Accessibility — keyboard alternative for rearranging dashboard widgets
- Accessibility — toasts announced to screen readers (aria-live region)
- Accessibility — decorative animations respect prefers-reduced-motion
- Media Manager — lasso selection in lists (Escape cancels)
- Media Manager — wider clickable gutters so the lasso starts off-row
- Media Manager — TMDB search: optional "Year" field to disambiguate remakes
- Watchlist — audio language tags (FR, EN, JP…) on available episodes
- Backups — SQL dump and encryption key embedded by default
- Backups — refuse to start when the path is missing in production
- Backups — operator restore runbook and API-side warning
- Backups — ZIP signature check and entry whitelist (zip-bomb guard)
- Incident runbook with documented recovery procedures
- Automatic webhook alerts on critical incidents (health, DB, scheduler, dump)
- Strict proxy trust, security headers (CSP/HSTS) and secure cookies
- Revocable sessions, strict token scopes and secured WebSocket
- XSS hardening — URL scheme filtering, tighter HTML sanitization
- API hardening — rate limiting, origin checks, authorization enforcement
- CSP — dedicated violation report endpoint with rate-limited logging
- API — configuration payloads reject unknown fields
- Notifications — HMAC signature header on outbound webhooks
- Notifications — single retry on rate-limit errors (capped at 5 s)
- Notifications — structured log on image-host failure (status + snippet, no secrets)
- Logs — global redaction filter (passwords, tokens, JWTs, webhooks)
- Login — success entries log the user identifier
- API — global error handler strips query strings
- Privacy (GDPR) — admin section (toggle, FR/EN editors, pending accounts list)
- Privacy (GDPR) — user tab (policy, ZIP export, delayed deletion, grace-period banner)
- Privacy (GDPR) — preset settings shipped (off by default), delayed deletion cancellable
- Users — "pending deletion" filter
- Scheduler — daily purge of pending accounts (opt-in)
- Database — chat anonymised when an account is removed (instead of erased)
- Startup — warn when the public origin is unset in reverse-proxy mode
- Persistent banner when the at-rest encryption key is ephemeral
- Tests — automatic detection of third-party hosts missing from the security policy
- Deployment — per-stack reverse-proxy guides
- Project documentation refreshed (README, security, architecture, contributing, attributions)
- UX — clear message when the server throttles requests
- Notification settings — explicit confirmation required before clearing every destination
- CSP — allow embedded video loader while keeping cookie-less playback

### Changed
- Requests (admin) — cleaner header, slide toggles, single-locale privacy editor
- Portal admin — Tickets and Lists sub-tabs retired (actions moved to the portal surface)
- Admin lists — moderation moved to the portal Lists page (Admin tab)
- Frontend deps — compile/runtime alignment of locales

### Fixed
- Migrations — atomic commit of the startup sequence (no more silent rollback)
- Migrations — switched the affected schemas to native SQL (fixes a silent async no-op)
- Migrations — version column auto-widened for long migrations
- Migrations — Alembic head chaining resolved
- Startup — achievement validation: unreachable locale files no longer fail the seed
- Statistics — poster hover popup closes after clicking through to activity history
- Edit user — clearing a field (first/last name, email) now persists as a removal
- Edit user — form stays in sync after save
- Trophies — XP history shows the unlocked trophy name
- Trophies — Ultimate Marathoner threshold raised to 24 h in one session (was 12 h)
- Notifications — context-aware "series / full season / episodes" detection, template and synopsis applied
- Notifications — titles rendered as clickable links (instead of raw text)
- Admin notifications — long messages wrap onto multiple lines
- Reconnect overlay — logo always visible during a redeploy, automatic sign-out if the app was updated
- Dashboard — Activity widget: labels wrap on narrow widths
- Dashboard — Reset/Done buttons compact on desktop, touch target preserved on mobile
- Dashboard — Portal Activity widget: numbers centered, no more overflow
- Dashboard — Customize toolbar: buttons aligned right, Reset turned red, single-line label
- Leaderboard — rank movement arrow no longer overlaps the username (clean truncation on long names)
- Leaderboard — custom avatars honoured across all lists, initial fallback if the image fails to load
- Portal — smaller poster thumbnails on mobile, tap anywhere opens details (action buttons hidden on touch)
- Portal — availability dot unified (canonical cache wins)
- Portal — "Play" CTA removed from hero banners (hero stays informational)
- Portal — hero video sticks to the topbar at every width
- Portal — fix 500 when the portal sends a TMDB id as text
- Scheduler — "Run now" on obsolete tasks no longer errors
- Follow-up / Missing — duplicate series appear only once
- User deletion — community content anonymised instead of cascade-deleted
- PWA — portal URLs aligned, system name unified, maskable icon fixed
- PWA — Android icons opaque on every variant
- Privacy — English tab label was rendered as a raw key (translation restored)
- Privacy — clean error message when the export exceeds the size cap
- Database — missing foreign-key constraints added on event and XP tables
- Login — GitHub icon restored with the correct link, text version line dropped
- Build — LF line endings enforced on scripts, CRLF auto-fixed at container build
- UX — credits padding tightened, deduplicated login GitHub link, container mention dropped
- Users — local admin account flagged as "Local" instead of an external source
- Users — admin last-login stamped on every sign-in
- Users — stats banner refreshed immediately after deactivation
- Users — drawer no longer closes on outside click (close button only)
- Users — access end shown in hours/minutes when less than 24 h remain
- Users — Status column coloured green/red depending on account state
- Users — access start defaults to the account creation date
- Users — Audit tab translated and summarised in plain text
- Users — Trophies tab: translated names, aligned icons without animation, rarity badge + XP
- Users — calendar picker icon visible on date fields
- Users — "Force logout" button clarified as not affecting the streaming account
- XP — inactive accounts earn XP when the admin enables "offline XP"
- XP — post-session grant no longer crashes when an ORM session expires
- XP — watched duration clamped to item runtime (long pauses no longer push past 85 %)
- XP — trailers and non-Movie/Episode types no longer grant XP
- XP — action table cleaned of zombie entries (covered by the achievement system)
- Sessions — real watched duration used (clamped), no more fake 24 h+ sessions after a restart
- Sessions — end stamped at the last sighting (not at the moment of detection)
- Admin debug — "Recheck all achievements" button to backfill history
- Admin debug — "Reset a trophy for everyone" button (drops UA + refunds XP)
- Profile — monthly ranking shows the 15 rows without inner scroll
- Duplicates — Ignored tab now compact rows grouped by series with a "Restore all" header button
- Security — dropped `unsafe-eval` from CSP (precompiled locales)
- Stats — Top 20 and genre stats count sessions with the same rules

## [0.9.8] - 2026-04-28

### Removed
- Alternate themes removed — only the dark theme remains, return in v1.0

### Added
- Tickets — full overhaul: anchor to a library title (season/episode for shows) or off-library, premium conversation, status/source/issue filters
- Tickets — admin alert on creation, auto-close after 7 days of inactivity
- Media Manager — move: suggested folder matching the source parent at top of list ("Suggested" / "~Suggested" badges)
- Media Manager — move: "Create a folder here" card with inline input (Enter creates + selects)
- Media Manager — "copy" button on each generated new name
- Dashboard — new "Requests — upcoming events" card (next 5 scheduled portal events)
- Mobile dashboard — automatic vertical stack on phones
- Dashboard — two Requests cards (actions / activity, 24h/7d toggle)
- "Lists" tab in the Demandes admin (moderate public lists)
- Admin-only Requests management page: backdrops, weekly stats, filters, sort, quick actions
- Backdrop added to requests (TMDB at create time, auto-backfill)
- Admin password change from Settings → General
- Security tab (Settings): login history, manual IP/user block
- Auto-block after 5 failed attempts, alert after 3
- Sensitive keys (Emby, TMDB, OpenSubtitles…) encrypted at rest
- App-style mobile navigation bar (bottom bar + iPhone notch)
- Polished mobile experience (touch targets, hover gated on touch)
- Admin on mobile: larger touch targets, drawer + notch, tables in card mode
- Media Manager — "Words to ignore" tab: editable list of tags stripped before TMDB search

### Changed
- Sidebar — "Requests" section renamed to "Requests module"
- Sidebar — sub-tabs exposed directly under each module (no more in-page tab bars), auto-expand
- Requests module configuration accessible from the sidebar (below Users)
- Demandes — horizontal scrollers: left/right arrows on desktop, native swipe on touch
- Media Manager — move overlay redesigned (960×640 modal, breadcrumb, auto-suggestion, recents accordion)
- Media Manager — "Organize folders" overlay redesigned (matches the move modal style)
- Media Manager — "Rename folder" overlay redesigned (same style)
- Sidebar — "Media" category renamed to "Modules"
- Filters unified across every module (pill style, accent glow on active)
- Settings → Appearance: "Neon glow intensity" slider (0 % to 200 %)
- Login page: browser auto-fill disabled
- Admin URLs standardized (old bookmarks must be re-created)
- Notifications: opening the bell marks all as read ("Mark all" button removed)
- Sidebar — numeric pill next to Notifications removed
- Subtitles — Library: filter bar split into 3 groups
- Subtitles — OpenSubtitles quota moved to the page header, visible from every tab
- Backend error messages now translated client-side (no more raw English)
- Admin "delete request" fully removes the row (immediate resubmission)
- Retry badge (x2, x3…) switched to red to match the "Rejected" tag
- User profile popup (Statistics): compact layout, full name on hover
- Discord notifications: episodes grouped by season as soon as 2+ are added

### Fixed
- Discord notifications — recent additions: item refreshed from Emby just before sending (held back while overview/year missing)
- Media Manager — sanitisation: "/" and "\" replaced by a space (no more glued words)
- Media Manager — move: search field cleared on folder/category change
- Media Manager — move: folder cards' HTML structure fixed (nested buttons)
- Media Manager — TMDB search: breadcrumb re-runs search on the parent folder
- Media Manager — TMDB search: multi-selection runs only when all share the same cleaned title
- Media Manager — rename: list resyncs with the NAS automatically (no more "source not found")
- Media Manager — move conflict / rename errors modal: labels localized
- Media Manager — rename: titles ending with "…" or "..." no longer rejected
- Media Manager — lasso: correct selection after scrolling
- Media Manager — Add season: episodes linked to checked files, source extension preserved
- Media Manager — renamed file keeps its row in the list
- Dashboard — Recent activity: titles and labels no longer follow the accent colour
- Mobile dashboard — header: title no longer truncated by dots and avatars
- Watchlist mobile — Timeline: titles no longer truncated (2-line wrap if needed)
- Watchlist mobile — Calendar: square cells with number + event-count pill
- Watchlist mobile — Ignored: name, tags and "Restore" button stacked vertically
- Watchlist — Ignored: tooltip on hover over truncated series name
- Statistics mobile — Users & Activity: title/filters/search stacked
- Statistics mobile — User profile: popup fits viewport and scrolls, sticky header
- Statistics mobile — Charts: toggles full-width, no longer truncated
- Browser tab titles fixed across the Demandes module
- Dashboard — "Requests — action" card no longer truncated with the Manage button
- Newly-added title availability reflected within 1 minute (no reload)
- Monthly ranking: no more 401 error when the admin isn't signed into the viewer
- Statistics: labels and durations (Record, Streak, Top, Peak, "X ago") follow the active language
- Media Manager: "Custom" word stripped from TMDB auto-detection
- Discord notifications: cover art displayed, TMDB link on episode notifications, default texts in French
- Discord notifications: configured delay interpreted in seconds (no more ×60)
- Subtitles mobile — Search: dropdowns and buttons stacked
- Notifications mobile — Templates: list, editor, Discord preview stacked
- Onboarding mobile: steps rail scrollable, panels resized, touch targets widened
- Demandes — mobile home: "Top 20 of the month" title no longer nibbled by the hero
- Demandes — mobile home: hero shortened (52 vh) to lift carousels higher
- Demandes — mobile top nav: logo + icons on a single row
- Demandes — mobile top nav: top gradient softened to let the hero show through
- Demandes — mobile hero: trailer sound toggled by tapping the hero (mute button removed)
- Demandes — desktop hero: title, synopsis and buttons pulled closer to the bottom
- Demandes — hero: trailer crossfade veil now full-screen
- Demandes — mobile hero: action buttons shrunk to fit a 400 px row
- Demandes — mobile hero: trailer edge-to-edge (ellipse mask removed)
- Demandes — top bar: calendar and bell aligned 100 % on the style of the other icons

## [0.9.7] - 2026-04-17

### Added
- New "Based on your preferences" carousel driven by a genre picker in Edit my profile
- Enriched profile cards: longest marathon, movies vs series, time of day, record month
- 11 extra genres mapped (History, Western, War, etc.)
- 4 Mythic trophies and 7 "Masters" meta-trophies with unique avatar effects
- 6 trophy rarity levels, with animated effects on the rarest ones
- Trophies overlay: search, "With reward" filter and pin up to 5 achievements on your profile
- Equipped title selector in Edit my profile
- Built-in folder browser in the onboarding wizard
- Monthly request quota shown as toast, admin accounts unlimited

### Changed
- Demandes profile revamped: new section order and recommendation carousels
- Monthly leaderboard extended to the top 15 with rank-change arrows
- Dashboard: Top users widget replaced by the monthly XP leaderboard
- Dashboard cards with colored icons (plays, duration, storage, duplicates)
- Secret trophies now also shown in their natural category
- Voting on requests removed: a requested title stays unique
- Sensitive backoffice actions better guarded against double-clicks
- Tickets: shortcut in the avatar menu and notification when an admin replies

### Fixed
- Strict filtering of plays without poster or TMDB match
- "Watched" detection now sourced from Emby instead of the local table
- Episodes grouped under their parent series in "Continue watching"
- Genre recommendations use OR operator for more results
- "Make a request" dialog redesigned with partial availability handling
- "Most rewatched" counter stabilized against corrupt sessions
- Emby public URL kept when the tool is toggled on or off
- "Requested" tag shown instantly after submission
- Episode names: English fallback when TMDB returns a placeholder
- "Hide adult content" and "equipped title" fields now actually saved
- Episodes ignored by admin honored in the request dialog
- "Request" button on detail page opens the request dialog

## [0.9.6] - 2026-04-14

### Added
- Achievement system: 150+ trophies across ~20 families + 29 secret trophies to unlock
- Level system (max 50) based on XP
- Year badges on seasonal trophies (Christmas, Halloween, New Year…)
- Reward titles displayed in the sidebar and leaderboard
- Full-screen overlay dedicated to trophies, with categories and per-achievement details
- Enriched profile statistics: member-since date, rank, genres, favorite day, most rewatched movies and series

### Fixed
- Total watch time displayed as 0h
- Some secret trophies did not unlock

## [0.9.5] - 2026-04-13

### Added
- Redesigned Demandes profile page with a new layout
- 7-tier visual rank system (Bronze → Legendary) with progressive visual effects
- Horizontal genre cards, favorite-day mini chart, "Most rewatched" section
- Trophy section with visual grid and progress bar toward the next achievement
- Monthly leaderboard based on XP with tier-colored avatars and player titles
- "Member since X months" block in the sidebar

### Changed
- Leaderboard now ranks by XP earned this month instead of play count

## [0.9.4] - 2026-04-05

### Added
- Complete Subtitles module redesign with integrated manager
- Library browser with responsive poster grid (supports 21:9 ultrawide)
- Detailed overlay for movies and series: subtitles, audio tracks, search and download
- Automatic episode grouping by series
- Delete audio and subtitle tracks directly from the interface
- Search and download via OpenSubtitles with quality scoring
- Language profiles for subtitles
- Persistent download history
- Season × Episode matrix view for series
- Batch download with progress tracking
- Automatic subtitle download for new media
- Full audit mode (missing, forced, image-only, encoding)
- SRT desync detection and manual shift correction
- Automatic subtitle encoding fix
- Side-by-side subtitle comparator
- Library stream search with mass deletion
- Extended support to 28 languages (Arabic, Chinese, Korean, Japanese, Hindi, etc.)

### Changed
- Full internationalization: all interface text is now translated
- Dates and times now display in the browser's locale

### Fixed
- "Top audio languages" shown instead of "Audio language" in now playing
- Image (PGS) subtitles are now counted in language pills
- Movie overlay works again
- "Missing" filter is faster
- Statistics tab no longer loads in an infinite loop

## [0.9.3] - 2026-04-02

### Added
- Dynamic categories in Media Manager with built-in folder browser
- Lasso (rectangular) selection in the file list
- Context menu (right-click) on files, folders and generated names
- Keyboard navigation with Backspace to go up in the folder hierarchy
- File extension filtering in the Media Health module with clickable chips
- File extraction can now be undone from the history

### Changed
- Media Manager configuration window is more compact
- Media Manager tabs use the full available width with horizontal scrolling
- Automatic file name cleaning now also strips `[...]`, `(...)` tags and `10BITS` / `8BITS`
- Dashboard upcoming releases show episodes up to 2 days old with a dedicated badge

### Fixed
- Media Health filters stayed hidden when no results matched
- Duplicate-rules dropdown was unreadable in light mode
- Tracked movies and series did not appear in the calendar
- 2-hour timezone offset corrected
- Scheduled tasks now start at midnight for intervals ≥ 1h

## [0.9.2] - 2026-03-31

### Added
- Bulk delete for activities in Statistics / Activity

### Changed
- "Top by genre" radar chart is larger for better readability
- CSV / JSON export buttons in Watchlist / Missing are larger and more visible

### Fixed
- Dashboard "Duplicates" card showed wrong count by including ignored duplicates
- User profile popup in Statistics opened behind the sidebar
- Content exclusions were not applied to user statistics
- Exclusions dropdown was unreadable in light mode
- Tracked movies and series did not appear in the Watchlist calendar

## [0.9.1] - 2026-03-29

### Added
- New changelog system with "What's new?" popup and dedicated page accessible from the sidebar
- Discord notifications available in French and English, with automatic adaptation to the selected language
- New Media Health module with Dashboard widget (overall score, obsolete codecs, resolution, missing subtitles)
- New Subtitles module: search and download via OpenSubtitles
- Custom day count in statistics charts

### Changed
- Dates and times now display in your browser's local timezone
- Statistics and Notifications pages are fully translated
- Version number in the sidebar is dynamic and clickable
- History browsing is more reliable (no more duplicates or missing items)

### Fixed
- Upcoming releases show right after startup
- Watchlist counter appears immediately in the sidebar
- Discord notification tests send the correct message type
- Cover images no longer disappear after the first Discord test
- Notification preview no longer shows two overlapping messages
- Activity chart respects the selected number of days

## [0.9.0] - 2026-03-15

### Added
- Full backup and restore of the configuration
- Download, restore or delete backups from Settings
- Scheduled automatic backups via the task scheduler

### Changed
- Redesigned first-time setup wizard

## [0.8.0] - 2026-03-01

### Added
- Task scheduler: manage automated tasks from Settings
- First-time setup wizard to guide new users

## [0.7.0] - 2026-02-15

### Added
- 11 visual themes (Dark, AMOLED, Nord, Sakura, Cinema, and more)
- Advanced customization: adjustable border radius, custom wallpaper with opacity and blur
- New Settings interface organized in tabs

## [0.6.0] - 2026-02-10

### Added
- Interface available in French and English
- Language selector in the top bar
- Automatic browser language detection

## [0.5.0] - 2026-02-01

### Added
- Complete new interface: Dashboard, Statistics, Duplicates, Logs, Watchlist, Notifications, Settings
- Now Playing carousel on the Dashboard
- Real-time statistics ribbon
- 6 customizable Dashboard widgets
