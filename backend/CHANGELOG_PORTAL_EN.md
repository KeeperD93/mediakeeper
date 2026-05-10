# Portal Changelog

<!--
Changelog for users of the Portal viewer (public surface).
Do not mention strictly admin / backoffice changes here — those go in
CHANGELOG_EN.md. A change that touches both surfaces must appear in both
files.

[Unreleased] section: accumulate viewer-visible changes here over time.
When ready to ship, rename `[Unreleased]` to `[x.y.z] - YYYY-MM-DD`
and update PORTAL_VERSION in backend/api/portal_changelog.py.
This section intentionally has no date so it is not shown to users.
-->

## [Unreleased]

### Added
- Search — instant suggestions, recent searches, keyboard navigation and Ctrl/Cmd+K shortcut
- Accessibility — keyboard "Skip to main content" link
- Page not found — proper accessible 404 page with back-to-portal link (no more silent redirect)
- Login — dedicated Portal sign-in page (adapted title and subtitle)
- "Bathroom Break" achievement — unlockable (5 pauses of 2 to 5 minutes)
- "Pilot" and "The Latecomer" achievements — unlockable
- "Ultimate All-Nighter", "No Life" and "The King" achievements — unlockable
- "The Loner" and "In Sync" achievements — unlockable
- "Time Traveler", "The Classic" and "The Purist" achievements — unlockable
- "Lucky" achievements — unlock by using the Surprise Me button (4 tiers)
- Credits — new page (TMDB, OpenSubtitles, Emby, Imgur, YouTube) reachable from the footer
- Settings — Account tab shows the account expiry date (or "No limit")
- Notifications — admins and moderators see flagged chat messages in the bell
- Chat — report button animates then locks after submission (cannot re-report)
- Tickets — pinpoint the exact movie, series, season or episode when reporting an issue (or an off-library topic), with direct library search
- Tickets — detail page and conversation fully redesigned: visual media preview, avatars, admin badge, clear status, polished mobile experience
- Tickets — automatic close after 7 days of inactivity, admin alert on every new ticket, filters by status, source and issue type
- Settings page redesigned as a premium 5-tab layout: identity, appearance, preferences, visibility, account
- Custom avatar upload: bring your own image, it overrides the Emby one (5 MB max, fall back to Emby at any time)
- MediaKeeper username: mandatory pick on first sign-in, live availability check, auto-suggestions when taken, editable once every 6 months
- Public profile pages: click a name in the leaderboard to see their card, bio, genres and unlocked trophies
- "View my public profile" button to preview exactly what others see
- Live preview of equipped titles and avatar cosmetics before saving
- Login streak indicator and direct link to Emby for password changes
- XP and trophies start accumulating as soon as an administrator activates the account, even before the user has signed in to the portal
- Reserved usernames: "admin", "administrator" and "root" cannot be used
- Monthly leaderboard — every Emby user listed (admins and moderators included), local and deactivated accounts excluded
- Help Center wired into the avatar menu: 15 articles grouped by categories, live search, full-screen reader
- Admins can edit the help inline: rich-text editor, auto-save, drafts, and a trash with 30-day restore window
- Chat — unread counter persists across sessions (badge on the collapsed + button and on the expanded chat icon), full history loaded on open, realtime connection kept alive for the whole portal session
- Notifications — admins can now push a targeted message that lands in the bell
- Legal attribution notice added to the footer
- List achievements — two new tiered families (Curator, Librarian) with 5 tiers each

### Changed
- Settings — active tab synced with the URL (deep links and refresh)
- What's new today — monthly Top 3 aligned on the dashboard's Ranking widget (identical look, your own position appended as a 4th row when off the podium)
- Tickets — filters reorganised into labelled groups (status, source, issue) using the Demandes pill style
- URLs standardized (old bookmarks must be re-created)
- Top bar: settings cog removed — configuration is now handled from MediaKeeper
- Top bar: "Dashboard" button now an icon-only home button repositioned to the right of notifications
- Top bar: tabs slightly offset from the MediaKeeper logo
- Notifications: opening the bell now marks every notification as read automatically ("Mark all read" button removed)
- Sub-page tabs (media detail, person, lists, admin) aligned to the same glass style used across the app
- Mobile bottom nav: active tab highlight now wraps both icon and label (no longer limited to the icon)
- Mobile bottom nav: "Lists" tab added (direct access, next to Home)
- Mobile top bar streamlined: Dashboard, Lists, Calendar and Admin moved into the avatar menu — only search, notifications and avatar stay in the bar
- Mobile profile: identity card tightened (narrower width, slimmer padding and avatar) to free up space
- Profile: rotating halos and breathing glow around the card removed (cleaner look across all screens)
- Trophies: breathing glow removed from cards (coloured halo kept static)
- All trophies overlay: leftover animations stripped from rows (progress shine, master crown bob, xmas badge twinkle)
- Trophies: reward XP lowered to smooth progression (already-earned XP adjusted accordingly)

### Fixed
- Requests — auto-switch to "Available" and bell notification as soon as the media lands on Emby
- Top of the month — series count once per viewer (no longer inflated by episode count)
- Top genres — each series counts once per genre (no longer overweighted by episode count)
- Top of the month and genres — plays only counted from 85 % of the runtime
- Achievements — instant unlock on chat, requests, tickets, avatar, events (no more wait for the next login)
- Achievements — global progression percentage now reflects only attainable trophies
- Dashboard — shortcut hidden for moderators without backoffice access (no more click that bounces back)
- Availability pill — fully-stocked series no longer flagged "partially available" after an Emby re-import (index duplicates merged, orphans auto-purged on next scan)
- What's new today — overlay scrollbar restyled (accent gradient + subtle track, no more white slab)
- Public profile: XP bar showed the current-level threshold instead of the next (e.g. "1500/1500" instead of "1574/2100")
- Help articles — edits no longer revert mid-typing
- Chat — default room auto-created, conversation usable from first open
- What's new today — overlay size reduced on large screens (more compact panel, lighter hero)
- All trophies overlay (mobile): cards compact by default (icon, name, rarity, description, progress), tap to expand for details (stars, XP, date, rewards, pin button)
- Mobile profile: trophy grid capped at 2 rows per page to stay smooth when many effects are unlocked
- Profile: "divine crown" avatar effect optimized to stay smooth on phones
- Legendary profile (level 50): card lightened on mobile (fewer stars and embers) to stay smooth
- Browser tab titles fixed across the Demandes module pages
- Changelog page: background now matches the rest of the Demandes module (no more untinted strip)
- Bell and calendar popups: repositioned right under the icon on wide screens
- Top bar: calendar button and compact (mobile) search button now share the same corner radius as the other icons
- Admin requests list: acting on a row no longer jumps back to the top
- Event creation: clicking outside the window no longer closes it (only the X and Cancel close)
- Event creation: media search now only suggests titles actually present in the library
- Upcoming-event ticker: transparent background, lighter text, sits flush below the top bar
- Home hero trailer: cinematic fade-to-black between trailers — no backdrop flash in between, next trailer is prefetched while the current one plays
- Mobile: request, launch, re-request and add-to-list buttons now always visible on poster cards (no hover needed)
- Mobile: "Recently added on Emby" hero now displayed, opaque full-bleed trailer with a dark gradient under the info and buttons
- Mobile: "Recently added on Emby" hero — tap the trailer to toggle sound, mute button removed (matches the main hero behaviour)
- "Recently added on Emby" hero: backdrop image kept during trailer swaps (no more transparent flash)
- "Recently added on Emby" hero: trailer transitions aligned with the main hero (black fade in before swap, hidden buffering, black fade out into next trailer, 4 s safety net)
- "Recently added on Emby" hero: top and bottom gradients aligned on the page background colour to blend the seams with the topbar and the poster row below, hero block taller to compensate for the dimmed area
- "Recently added on Emby" hero: "More info" button icon now visible (broken render fixed)
- "Recently added on Emby" hero: with sound on, the end of a trailer now rotates to the next item instead of looping the same one
- Mobile: home hero trailer stays opaque during transitions (no more transparency flash exposing the page background between two trailers)
- Mobile: top bar always opaque (no more variable transparency on scroll, and no more transparency while a trailer is playing)
- Mobile: "MediaKeeper" name now shown next to the logo in the top bar
- Brand renamed "MediaKeeper" (capital K) across the UI

## [0.2.0] - 2026-04-20

### Added
- "Today's digest" overlay: daily recap of the Demandes module with recent library additions, upcoming events, monthly ranking, request quota, open tickets, closest achievement and current viewing streak
- Avatar menu: new "Today's digest" entry to reopen the recap on demand
- Admin requests: rejection reason prompt when denying a request, shown on hover of the "Rejected" tag on user posters
- Personal playlists: create a list, make it private / public / collaborative, add movies and series, export as JSON or CSV, copy a public list, expanded panel with items, contributors and history
- New "Lists" button in the top bar, right of the heart icon
- Premium visual overhaul of the Requests, Lists and Issues pages: edge-to-edge rows with the media backdrop, animated status bar, requester avatar, numbering, type filters (movies / series), one-click approve / reject / delete actions as icons
- Clicking the poster on a request row opens the media detail
- Copy-title button revealed on row hover
- Posters: "Add to a list" button on hover, flush to the right edge
- Media detail page: inline YouTube trailer in the hero (no more lightbox), new "From the director", "Starring" and "In the same franchise" carousels
- New Person (filmography filterable by director / acting) and Franchise pages, reachable from a media's credits

### Changed
- Posters: state tags now rendered as diagonal sashes with a recalibrated palette (bronze, slate, indigo, emerald, rust)
- Home: faster load, each row appears the moment it is ready instead of waiting for the slowest one
- "More like this" tab: "Similar titles" section removed (poor relevance on recent releases), recommendations expanded to 20 titles
- When an admin deletes a request, the user can immediately submit it again
- Full redesign of the media detail page: edge-to-edge hero with poster, studio logos, score and popularity, age certification, tabs Overview / Cast / Extras & reviews / More like this
- Enriched detail page: keywords, streaming providers (FR), key crew (writing, music, cinematography, editing, production), expanded cast (20 roles), user reviews, extras (trailers, teasers, featurettes, behind the scenes), TMDB / IMDb / official site links, dedicated saga banner
- "Rejected" tag switched to red for clearer contrast with the "Requested" tag
- Avatar menu: "What's new" entry renamed "Changelog"

### Fixed
- Profile: "My lists" section now populated (was silently empty due to an error)
- List CSV export: title, year and added-at columns, file named after the list
- Media detail: trailer picked in the order user language → English → original language, no longer missing on foreign titles
- Media detail: synopsis falls back to English when no translation exists for the user's language, instead of showing "No synopsis available"
- List items: poster, title and year now visible (no longer just the TMDB id)
- List history: the title of the added or removed media now shown between quotes
- Diagonal state tag ("Rejected x3", "In progress"…): content now centred in the sash, no longer clipped by the poster edge
- Home: diagonal "Rejected" and "Approved" sashes now display their label again (they were rendering empty)
- "Rejected xN" sash: label re-centred when the x2/x3 retry counter is present
- Home posters: rejected requests now surface the "Rejected" tag and the "Re-request" button (instead of silently reverting to the neutral "Request" default)
- Detail page carousels (Cast, Recommendations, From the director, …) now properly left-aligned
- Media detail tab bar: no longer pinned to the top when scrolling
- Profile: the "Resubmit" button on a rejected request now opens the request overlay and flips to "Requested" once the resubmission goes through
- Media detail: "Add to list" button now opens an overlay with existing lists (no longer jumps to the lists page)
- Profile: "Your genres" card is denser in Full HD — inner tiles (favourite day, marathon, ratio…) now display in columns instead of stacking vertically, matching the height of the "Trophies" card
- Carousel alignment: title and first poster now share the exact same left edge on every row
- "More like this" tab: carousels now span full width, matching the home page
- "More like this" tab cards: availability dot, "Play" button and tags (new, watched…) now shown the same way as on the home page
- Saga block on the media detail page: same interactive cards (dot, play, request, tags) as on the home page
- Media detail: "Approved / Rejected / Requested / Available" statuses now render as a tag on the poster (below the age rating) instead of a disabled button
- Media detail: technical status ("Returning Series", "Post Production"…) translated to the active UI language

## [0.1.0] - 2026-04-18

### Added
- Dedicated "What's new" popup for the Demandes viewer, separate from the admin one
- "Resubmit" button on refused requests + x2/x3 badge showing the number of submissions

### Changed
- Backend error messages now translated client-side instead of shown raw

### Fixed
- Request status refreshed instantly after admin action across pages
- Availability of newly-added titles reflected within 1 minute without reload
- Monthly quota and XP protected against loss under rapid clicking
- Profile screen, "Top year" and "Upcoming" strips load faster
- Profile page no longer overflows horizontally on mobile when stats are fully populated
