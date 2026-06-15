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
- Posters — movie or series duration shown on hover everywhere.
- Posters — TMDB rating (gold star) shown on hover.
- Posters — title, release date and rating shown under the poster on mobile.
- Preferences — "Default" language option that follows the portal default.
- Issues — paged navigation with a per-page count selector (10/25/50/100).
- Lists — "Load more" button to reach beyond the first 50 items.
- Lists — Public tab: "Load more" beyond the first 50 lists.
- Notifications — "Load more" button to see older notifications.
- Support — header heart opening the server's donation link (when configured).

### Changed
- Notifications — those older than 6 months are removed automatically.
- Media detail — TMDB rating colour unified to gold.
- Avatars — legendary ring (level 50): animated rainbow on every surface.
- Preferences — the "hide adult content" setting moved here, under the genres.
- Home — Popular and Top-rated rows now sourced from Discover.
- What's new — recent additions stay until your next visit.
- Notifications — marked read when the panel closes (highlight kept while open).
- Forms — fields with sharper corners, distinct from rounded filters.

### Fixed
- Event invites — private profiles and admins can no longer be invited.
- Notifications — keyboard navigation (Esc to close) and no duplicates on load.
- Notifications — unread highlight now follows your theme accent colour.
- Continue watching — shows only your own in-progress titles.
- Requests — refused (not allowed through) when the adult check can't reach TMDB.
- Lists — collaborator history shows pseudonyms, never raw Emby logins.
- Posters — an upcoming title's duration appears once TMDB publishes it.
- Posters — no more shift leaving a dark gap below the artwork.
- Home — featured banner shows "Pending" for an already-requested title.
- Requests — one-click movie requests now show success or refusal.
- Maintenance mode — the portal is now fully locked (holding page only).
- Surprise — the drawn pick's title and synopsis follow your language.
- Home — carousel titles and synopsis follow your language.
- Settings — your rank colours applied on open (no flash).
- Cinema room — Start button centred on screen, Emby launch made reliable.
- Cinema room — trailer resumes when returning from the Emby tab.
- Cinema room — intro countdown synced with the main countdown.
- Cinema room — no more looping requests after leaving the room.
- Requests — titles follow your language.
- Media detail — TMDB link opens in the app language.
- Dates now shown in your language (instead of the browser).
- Discover — lists (trending, popular, …) now shown in your language.
- Changelog — versions with no entries are hidden (no more blank cards).
- Custom avatars now shown in list contributors and the user picker.
- "Already requested" badges now load on large lists.
- What's new — full XP bar at max level (no level 51).
- What's new — a same-day addition stays visible even after dismissing the overlay.
- Recommended for you — the home row now fills to 20 distinct titles.
- Adult content — hiding it now applies to every list, search and recommendations.
- Requests — adult titles can only be requested if the administrator allows it.
- Notifications — admin messages and list updates now show a readable label.
- Movie night — private event: capacity follows the guests (picker hidden).
- Network errors — clear message shown instead of a misleading empty list.

## [1.0.0-rc.4] - 2026-05-30

### Changed
- Avatars — level-coloured ring (bronze → legendary) everywhere.
- Cinema room — seats use the leaderboard avatar style.

### Fixed
- Events ticker — readable (static) when reduced-motion is on.
- Availability badge — no longer flickers when the index is catching up.
- Home posters — first-paint burst no longer breaks tile rendering.
- Browsing — availability and request badges keep loading during fast scrolling.

## [1.0.0-rc.3] - 2026-05-22

## [1.0.0-rc.2] - 2026-05-22

## [1.0.0-rc.1] - 2026-05-21

### Added
- Cinema room — dedicated mobile view (3-column avatar grid).
- Cinema room — per-participant progress, "Late" tag.
- Cinema room — realtime presence (seats freed on disconnect).
- Cinema room — live playback timer for every event.
- Movie nights — per-event capacity picked at creation (5/10/15/20).

### Changed
- Footer — attribution banner removed (credits kept on the Credits page).
- Unified poster visuals across all surfaces (PEGI removed from detail hero)
- Home: unified list rhythm (airier titles, tighter posters).
- Subtitles — library: 3 covers per row on mobile
- Detail page — mobile densification (more info on small screens)
- Detail page — "Available on Emby" banner removed (redundant info)
- Detail page — premium sidebar (icons, status dot, capitalised labels).
- Discover — grid tightened on mobile (auto-fit + clamp)
- Person page — responsive hero (photo + title adapted to mobile)
- Mobile posters: actions removed, tap opens the detail page
- Mobile home: hero descriptions hidden to declutter
- Home — hero strip: image slideshow (10 s, crossfade between items).
- What's new — overlay shown once per day (Close button is enough)
- Lists — 3 posters per row on mobile, tighter spacing
- Cinema room — dynamic seats centred, "Full" badge.
- Cinema room — seats show avatar + pseudo, marathon panel relocated.
- Cinema room — "Launch" button always clickable, intro synchronised.

### Fixed
- Movie nights: past events locked (room closed, accept blocked, "Ended" pill).
- Display name picker: modal re-arms each login, overlays hidden until saved.
- Home: removed the burst of "Too many attempts" notifications on load
- Posters: restored white outline and Top 3 medals (gold/silver/bronze).
- Posters: duration shown on hover (TMDB cache for Top 20).
- Posters: tooltip dates restored on all diagonal ribbons.
- Posters: fixed stuck panel after clicking "Requested" status.
- Posters: "New" pulse animation now smooth (GPU-friendly).
- Detail page: status ribbon and availability chip aligned with portal.
- Posters: bookmark button tooltip renamed to "Add to a list".
- Emby hero: smaller title on mobile to free the trailer view.
- Emby hero: mobile posters at natural height (no dead space below).
- Mobile nav: "My profile" moved up to second position.
- Requests — clear error message when a request fails (quota, duplicate, blacklist)
- Mobile posters: availability badge repositioned to avoid overlap
- Person page — request status badge visible again on filmography
- Search — live TMDB rework with 5-minute cache (posters always fresh)
- Detail page — language and country localised in the UI language.
- Detail page — original language now read from TMDB (not first audio).
- Home — hero trailers: official + recent prioritised (better French dub).
- Home — manual hero slide jump now resets the 10 s timer.
- Home — hero trailers: on-demand playback only, no background auto-play.
- Preferences — save bar stays visible after changing language or genres.
- Preferences — overviews, recommendations and trailers reload in the new language.
- Settings — sticky tabs: blur removed where it bled over cards.
- Cinema room — fits any screen size with no vertical scroll.
- Cinema room — URL blocked for non-invitees, audio cut after intro.

## [0.3.0] - 2026-05-14

### Added
- Public profile pages — card, bio, genres and trophies reachable from the leaderboard
- "View my public profile" button to preview exactly what others see
- Profile — anonymous "User 1234" alias until a pseudo is picked
- Custom username — mandatory pick on first sign-in, live availability check, editable every 6 months
- Reserved usernames ("admin", "administrator", "root")
- Custom avatar upload — bring your own image (5 MB max), fall back to the default at any time
- Live preview of equipped titles and avatar cosmetics before saving
- Premium Settings page redesigned as a 5-tab layout (identity, appearance, preferences, visibility, account)
- Settings — Account tab shows the account expiry date (or "No limit")
- Login — dedicated Portal sign-in page
- Login — streak indicator and direct link for the password
- Cinema room — marathon: live progress, next film gated until everyone reaches 85 %
- Search — instant suggestions, recent searches, keyboard navigation and Ctrl/Cmd+K shortcut
- Tickets — pinpoint the exact movie, series, season or episode when reporting (or off-library topic)
- Tickets — detail page redesigned: visual preview, avatars, admin badge, clear status
- Tickets — automatic close after 7 days of inactivity, admin alert on creation, filters by status/source/type
- Help Center wired into the avatar menu — 15 articles grouped by categories, search, full-screen reader
- Admins can edit the help inline — rich-text editor, auto-save, drafts, 30-day restore trash
- Chat — unread counter persists across sessions, history loaded on open, realtime connection kept alive
- Chat — report button animates then locks after submission
- Notifications — admins and moderators see flagged chat messages
- Notifications — admins can now push a targeted message into the bell
- Monthly leaderboard — every user listed, local and deactivated accounts excluded
- XP and trophies start accumulating as soon as an administrator activates the account
- Achievements — 14 new unlockable trophies (social plays, marathons, classics, surprises)
- List achievements — two new tiered families (Curator, Librarian) with 5 tiers each
- Credits — new partners page reachable from the footer
- Legal attribution notice added to the footer
- Page not found — proper accessible 404 with back-to-portal link
- Accessibility — keyboard "Skip to main content" link

### Changed
- Leaderboard — premium showcase revamp: monthly champion hero, live stats bar, top 100, enriched podium
- Leaderboard — #1 avatar no longer rotates, static gold ring
- Media cards — diagonal "Available" ribbon removed (the green dot is enough)
- Avatars — inner fill matches the page background, silhouette more prominent, icon replaces the letter
- TMDB credit — compact single-line footer, reduced padding
- Notifications — icons aligned with the rest of the UI in lieu of emojis
- Home and profile — tighter spacing on mobile
- Cinema room — back-to-back trailers with black fade, Info button on the active trailer
- Cinema room — poster shown on the screen after the countdown
- Requests — available requests can be automatically cleaned up after a delay (admin-configurable)
- Lists — anonymized pseudos on owner and contributors of a list detail
- Settings — active tab synced with the URL (deep links and refresh)
- What's new today — monthly Top 3 aligned on the dashboard's Ranking widget, your position appended as a 4th row off the podium
- Tickets — slimmer filter row (status pills, type + sort selects); Source filter retired
- Tickets — "My tickets" shortcut removed from the avatar menu (duplicate of the Issues tab)
- URLs standardized (old bookmarks must be re-created)
- Top bar — settings cog removed (configuration handled from the admin)
- Top bar — Dashboard button now an icon-only home button to the right of notifications
- Top bar — tabs slightly offset from the logo
- Notifications — opening the bell marks every notification as read ("Mark all read" button removed)
- Sub-page tabs aligned to the same glass style as the rest of the app
- Mobile bottom nav — active tab highlight wraps both icon and label, "Lists" tab added
- Mobile top bar streamlined — Dashboard, Lists, Calendar and Admin moved into the avatar menu
- Mobile profile — identity card tightened (narrower width, slimmer padding and avatar)
- Profile — rotating halos and breathing glow around the card removed
- Trophies — breathing glow removed from cards (coloured halo kept static)
- All trophies overlay — leftover row animations stripped
- Trophies — reward XP lowered to smooth progression (already-earned XP adjusted accordingly)

### Fixed
- Home — backdrop image is shown when the trailer can't start (instead of a black hero)
- Home — trailers: cinematic fade-to-black between two clips, next trailer prefetched
- Home — tap the trailer to toggle sound (mute button removed)
- "Recently added" hero — opaque full-bleed trailer, transitions aligned with the main hero, gradients blended with the topbar
- "Recently added" hero — "More info" button icon now visible (broken render fixed)
- "Recently added" hero — end of a trailer now rotates to the next item instead of looping
- Mobile — top bar always opaque, "MediaKeeper" name now shown next to the logo
- Mobile — tighter home gap, bell dropdown no longer clipped, TMDB credit wraps cleanly
- Mobile — request, launch, re-request and add-to-list buttons always visible on poster cards
- Mobile — All trophies overlay: compact cards by default, tap to expand details
- Mobile — profile trophy grid capped at 2 rows per page to stay smooth
- Mobile — "divine crown" avatar effect and legendary profile optimized
- What's new today — avatars and posters fill their circle on mobile, overlay size reduced on large screens
- What's new today — overlay scrollbar restyled (accent gradient, no more white slab)
- Report-a-problem modal — media dropdown closes when clicking elsewhere
- Public profile — photoless avatar now shows the silhouette icon
- Public profile — XP bar shows the next-level threshold (instead of the current one)
- Private profile — dedicated landing instead of a generic error from the leaderboard
- Trophy toast — no longer re-fires on every refresh
- Surprise Me — intermittent 500 on rapid successive clicks fixed
- Search — result posters now display correctly
- Carousels — "See more" card shares the same rounded corners as adjacent posters
- Media detail page — always scrolls to the top on open
- Username-choice modal — no more bottom-left text leak during the enter transition
- Requests — auto-switch to "Available" and bell notification as soon as the media is on the library
- Top of the month — series count once per viewer (no longer inflated by episode count)
- Top genres — each series counts once per genre
- Top of the month and genres — plays only counted from 85 % of the runtime
- Achievements — instant unlock on chat, requests, tickets, avatar, events
- Achievements — global progression percentage reflects only attainable trophies
- Dashboard — shortcut hidden for moderators without backoffice access
- Availability pill — fully-stocked series no longer flagged "partially available" after a re-import
- Help articles — edits no longer revert mid-typing
- Chat — default room auto-created, conversation usable from first open
- Browser tab titles fixed across the Requests module pages
- Changelog page — background matches the rest of the module
- Bell and calendar popups — repositioned right under the icon on wide screens
- Top bar — calendar button and mobile search button share the same corner radius as the other icons
- Admin requests list — acting on a row no longer jumps back to the top
- Event creation — clicking outside no longer closes the window, search limited to library titles
- Upcoming-event ticker — transparent background, lighter text, flush below the top bar
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
