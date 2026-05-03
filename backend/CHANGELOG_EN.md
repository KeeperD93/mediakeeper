# Changelog

<!--
[Unreleased] section: accumulate small changes here over time.
When ready to ship, rename `[Unreleased]` to `[x.y.z] - YYYY-MM-DD`
and update APP_VERSION in backend/api/changelog.py.
This section intentionally has no date so it is not shown to users.
-->

## [Unreleased]

### Added
- Tightened credits page UX and added GitHub link on the login page
- About — admin page (stack, licenses, FFmpeg LGPL) and notes under TMDB / OpenSubtitles in Settings
- Requests — top-bar stat cards now show the all-time total under each counter (pending, approved, rejected, available)
- Requests / Users — premium full-width revamp (search, filters, table/card view, bulk actions)
- Users — 7-tab drawer (identity, access, security, activity, trophies, notes, audit)
- Users — Activity cards revamp (contextual icons, tinted gauges) and permissions as blue toggles
- Users — roles + granular permissions (chat, requests, problems, lists, offline XP)
- Users — access window (start/end) with 1/3/6/12-month extend shortcuts
- Users — disable the streaming account from MK (active sessions logged out)
- Users — selective import overlay and manual creation of local-only accounts
- Users — reversible soft-delete, full audit log, private admin notes, tags
- Users — per-user GDPR export (JSON) and targeted admin → user notification
- Users — online indicator, < 7 d expiry badge, "never logged in" filter
- Users — automatic deactivation on expiry (Emby + MediaKeeper, sessions killed, dedicated audit)
- Project documentation (README, SECURITY, ARCHITECTURE, CONTRIBUTING, attributions)
- Backups — SQL dump and encryption key embedded by default
- Backups — refuse to start when BACKUP_PATH is missing in production (safety)
- Backups — operator restore runbook + explicit API restore warning
- Incident runbook with documented recovery procedures
- Automatic webhook alerts on critical incidents (health, DB, scheduler, dump)
- Security updates (JWT, cryptography, multipart, frontend build)
- Strict proxy trust, security headers (CSP/HSTS) and secure cookies
- Revocable sessions, strict token scopes and secured WebSocket
- XSS hardening — URL scheme filtering, tighter HTML sanitization
- CSP — allow YouTube loader and keep iframe in privacy mode
- API hardening — rate limiting, origin checks, authorization enforcement
- CSP — dedicated violation report endpoint with rate-limited logging
- Deployment — per-stack reverse-proxy guides (LAN, DSM, NPM, Caddy, Traefik)
- UX — clear message when the server throttles requests

### Fixed
- UX: credits padding, deduplicated login GitHub link, dropped container mention
- Fix Discord notification titles rendered as raw text instead of links
- Portal — fix 500 when the portal sends a tmdb_id as text
- Users — local admin account flagged as "Local" instead of an Emby source
- Users — admin last-login stamped on every MK sign-in
- Users — stats banner refreshed immediately after deactivation/changes
- Users — drawer no longer closes on outside click (close button only)
- Users — access end shown in hours/minutes when less than 24h remain
- Users — Status column now coloured green/red depending on account state
- Users — access start defaults to the account creation date
- Users — Audit tab translated and summarised in plain text (role, identity, window, permissions)
- Users — Trophies tab: real Lucide icons without the animation effects
- Users — calendar picker icon visible on date fields (white)
- Users — "Force logout" button clarified as MediaKeeper-only (Emby untouched)
- XP — inactive accounts now earn XP when the admin enables "offline XP"
- Users — Trophies tab now shows translated names (Cinephile, Globe-Trotter…) instead of raw keys
- XP — post-session grant no longer crashes with MissingGreenlet (ORM sessions need expire_on_commit=False on collector + scheduler)
- XP — watched duration clamped to item runtime (long pauses can no longer push past the 85% threshold artificially)
- XP — trailers, MusicVideo, LiveTV and other non-Movie/Episode types no longer grant XP
- XP — action table cleaned of zombie entries (complete_series, request_approved, event_*, streak_*) actually covered by the achievement system
- Admin debug — "Recheck all achievements" endpoint: backfills trophies for users who haven't played since the fix
- Achievements — Ultimate Marathoner threshold raised to 24h in one session (was 12h)
- Leaderboard — custom avatars now honoured in user lists (leaderboard, ranking, daily digest, requests), initial fallback if the image fails to load
- Emby sessions — real watched duration used (clamped to wall/position/runtime), no more fake 24h+ sessions after a collector restart
- Emby sessions — session end stamped at the last Emby ping (``last_seen_at``), not at the moment the collector spots it as stale
- Admin debug — "Reset a trophy for everyone" button (drops UA + refunds XP) to scrub a wrongly-awarded trophy
- Users — Trophies tab: rarity badge (Common → Mythic) + earned XP shown under each unlocked trophy
- Profile — monthly ranking shows the 15 rows without inner scroll (card grows to fit)
- Migrations — fixed 029 → 030 chaining (two Alembic heads resolved)

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
