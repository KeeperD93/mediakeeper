"""Help Center seed — English translation of every starter article, by slug.

``help_content`` attaches each one to its French entry as ``"en"``; a test
keeps both sets of slugs identical."""

HELP_EN: dict[str, dict[str, str]] = {
    "les-notifications": {
        "title": "Notifications — what are they for?",
        "body_html": """
<p>Notifications keep you up to date with everything that concerns you on the portal, without refreshing it.</p>
<p><strong>What notifies you:</strong></p>
<ul>
  <li>One of your requests changes status (approved, in progress, available, rejected).</li>
  <li>The content you requested is <strong>now available</strong> on Emby.</li>
  <li>Someone <strong>replies</strong> to one of your tickets or comments.</li>
  <li>You unlock a <strong>trophy</strong>.</li>
  <li>You reach a new <strong>level tier</strong>.</li>
  <li>You are <strong>invited to an event</strong> (watch party, seasonal event).</li>
  <li>One of your <strong>collaborative lists</strong> changes.</li>
</ul>
<p>You can turn off each category on its own in <strong>Settings → Preferences → Notifications</strong>. Critical notifications (account security) always stay on.</p>
""".strip(),
    },
    "regarder-du-contenu-surprise": {
        "title": "Watch something at random (Surprise button)",
        "body_html": """
<p>At the bottom right of the screen, the <strong>Surprise button</strong> (dice icon) picks <strong>a movie or an episode</strong> for you at random, among content that is:</p>
<ul>
  <li>Available on Emby.</li>
  <li><strong>Not watched yet</strong> by you.</li>
  <li>In line with your <strong>favorite genres</strong>.</li>
  <li>Rated well by the community.</li>
</ul>
<p>Spin again as many times as you like; each click suggests a new title. If nothing tempts you, just close the window.</p>
<p>It is the perfect tool when you spend 20 minutes browsing the library without starting anything.</p>
""".strip(),
    },
    "comment-creer-un-ticket-de-probleme": {
        "title": "How do I open an issue ticket?",
        "body_html": """
<p>If something does not work (playback crashing, missing subtitles, a stuck request, a strange feature), you can open a <strong>ticket</strong> for the administrators to handle.</p>
<ol>
  <li>Open the avatar menu (top right) → <strong>My tickets</strong>.</li>
  <li>Click <strong>“New ticket”</strong>.</li>
  <li>Pick a <strong>category</strong>: playback, request, account, other.</li>
  <li>Give it a <strong>short title</strong> (e.g. “No sound on episode 3 of XYZ”).</li>
  <li>Describe the problem with <strong>as much detail as possible</strong>: which device, which browser or Emby app, when it happens, any error message shown.</li>
  <li>You can attach a screenshot if it helps.</li>
  <li>Submit. The administrator is notified right away.</li>
</ol>
<p>You can follow the status of your tickets and add messages to them from <strong>My tickets</strong>. A reply from the admin sends you a notification.</p>
""".strip(),
    },
    "le-calendrier-et-les-evenements": {
        "title": "The calendar and creating events",
        "body_html": """
<p><strong>Events</strong> are viewing sessions between members: a movie, a series or several titles in a row (a marathon), at a set date and time.</p>
<p><strong>Finding the calendar:</strong> tap the calendar icon in the top bar. On a phone, open your avatar menu, then <strong>“Calendar”</strong>. The <strong>“Upcoming events”</strong> list shows the ones you are invited to, the ones you created and every public event.</p>
<p><strong>Replying:</strong> tap an event to open it, then <strong>“Accept”</strong> or <strong>“Decline”</strong>. Once you are in, you can <strong>“Unsubscribe”</strong>. A public event with no seats left shows <em>“Full”</em>.</p>
<p><strong>Creating an event:</strong></p>
<ol>
  <li>Tap the round <strong>“+”</strong> button at the bottom right, then the <strong>“Create event”</strong> icon.</li>
  <li>Choose <strong>Private</strong> (by invitation) or <strong>Public</strong> (open to everyone).</li>
  <li>Give it a <strong>title</strong>, search for one or more <strong>movies or series</strong> already available, then pick the <strong>date</strong> and <strong>time</strong>.</li>
  <li>For a private event, add your <strong>guests</strong>: only members with a public profile can be invited. For a public event, choose the <strong>number of seats</strong>. You can add a <strong>comment</strong>.</li>
  <li>Tap <strong>“Create”</strong>.</li>
</ol>
<p><strong>When the time comes:</strong> 15 minutes before the start, the <strong>“Enter the room”</strong> button shows for the people taking part. The room opens in a new tab: you find the other participants there, the button to start the movie and the <strong>“Room chat”</strong>.</p>
<p><strong>Cancelling:</strong> if you created the event, open it and tap <strong>“Cancel event”</strong>.</p>
<p><strong>Notifications</strong> (the bell): you are told when someone invites you, when a guest replies to your event, when an event you joined is cancelled, or if the organizer removes you. A public event is announced to every member.</p>
<p>Taking part gives no extra XP (the movie you watch counts as usual). Creating events moves the <strong>“Organizer”</strong> trophies forward.</p>
""".strip(),
    },
    "comment-gagner-de-l-xp": {
        "title": "How do I earn XP?",
        "body_html": """
<p><strong>XP</strong> (experience points) raises your <strong>level</strong>, up to level 50. Your XP bar and your level are on <strong>“My profile”</strong>.</p>
<p><strong>What earns XP:</strong></p>
<ul>
  <li><strong>+10 XP</strong> per movie watched on Emby through at least 85% of its length.</li>
  <li><strong>+3 XP</strong> per episode watched through at least 85% of its length.</li>
  <li><strong>+2 XP</strong> when you sign in to the portal, once a day.</li>
  <li><strong>+5 XP</strong> per new request, up to 25 XP a day.</li>
  <li><strong>Trophies</strong>: each one gives its XP only once, when you unlock it. The amount shows in <strong>“See all trophies”</strong>, on <strong>“My profile”</strong>.</li>
</ul>
<p>Watching the same movie or episode again within 24 hours gives nothing more. Other actions (creating an event or a public list, writing in the chat…) give no XP directly, but they move some trophies forward.</p>
<p><strong>Bonus periods:</strong> the administrator can start a period during which the XP you earn is multiplied.</p>
""".strip(),
    },
    "les-paliers-et-grades": {
        "title": "Tiers and ranks",
        "body_html": """
<p>Each level gives you a <strong>rank</strong>, and each rank opens a visual tier: border color, card glow, particles around the avatar, title shown next to your username.</p>
<table>
  <thead>
    <tr><th>Levels</th><th>Rank</th><th>Title</th></tr>
  </thead>
  <tbody>
    <tr><td>1 → 5</td><td>Bronze</td><td>Spectator / Amateur</td></tr>
    <tr><td>6 → 10</td><td>Silver</td><td>Regular</td></tr>
    <tr><td>11 → 19</td><td>Gold</td><td>Passionate</td></tr>
    <tr><td>20 → 29</td><td>Platinum</td><td>Expert</td></tr>
    <tr><td>30 → 39</td><td>Diamond</td><td>Master</td></tr>
    <tr><td>40 → 49</td><td>Master</td><td>Master</td></tr>
    <tr><td>50</td><td>Legendary</td><td>Legend</td></tr>
  </tbody>
</table>
<p>Progress follows an increasingly demanding curve: going from level 1 to 2 takes little XP, but reaching level 50 (the <em>Legend</em>) takes months of regular activity.</p>
<p>Your rank is <strong>permanent</strong>: you cannot lose it. Only an administrator can adjust your level by hand from the debug panel, to fix a mistake.</p>
""".strip(),
    },
    "le-classement-mensuel": {
        "title": "The monthly leaderboard",
        "body_html": """
<p>The <strong>leaderboard</strong> compares the members' activity. On <strong>“My profile”</strong>, the <strong>“This month's ranking”</strong> block shows your place, and the <strong>“Leaderboard”</strong> card shows the current leaders. Tap the card's title to see the full leaderboard.</p>
<p><strong>Four periods:</strong> <em>Today</em>, <em>Week</em>, <em>Month</em> and <em>All time</em>. The week starts on Monday and the month on the 1st: with each new period, everyone starts again from zero.</p>
<p><strong>What counts:</strong> only the XP your activity earns during the period, that is movies and episodes watched, sign-ins and requests. Trophy XP raises your level, not your place on the leaderboard.</p>
<ul>
  <li>Your <strong>place</strong> (#1, #2…) and your <strong>“Top x%”</strong> show where you stand among the members ranked this month.</li>
  <li>In that block, the gap (for example “+2 places”) compares your place with the one you had at the end of last month. In the card and the full leaderboard, the small arrow compares with the day before, last week or last month, depending on the period chosen.</li>
  <li>As long as you have earned nothing during the period, you do not appear.</li>
</ul>
<p><strong>Who is on it:</strong> members with a <em>public</em> profile. If you switch your profile to <em>Private</em> (<strong>Settings → Visibility</strong>), you disappear from the leaderboard, but you keep earning XP.</p>
<p>Ending a month in the top 10, the top 5, the top 3 or in first place unlocks the <strong>“Competitor”</strong> trophies.</p>
""".strip(),
    },
    "comment-fonctionnent-les-recommandations": {
        "title": "How do recommendations work?",
        "body_html": """
<p>The <strong>My profile</strong> tab holds several sections of personal recommendations. Each one relies on a different signal:</p>
<ul>
  <li><strong>Continue watching</strong> — your latest Emby content started but not finished.</li>
  <li><strong>For you</strong> — based on your <em>favorite genres</em> (which you can change in <em>Settings → Preferences</em>) and on your average rating per genre.</li>
  <li><strong>Because you liked X</strong> — titles TMDB finds similar to what you recently rated highly (8/10 or more).</li>
  <li><strong>Community trends</strong> — what other MediaKeeper users are watching right now, filtered so it does not suggest what you have already seen.</li>
  <li><strong>Don't miss</strong> — recent releases (theaters and streaming) that match your taste.</li>
</ul>
<p>The more you <strong>rate</strong> and <strong>watch</strong>, the sharper the recommendations get. If a suggestion seems off, lower the rating of the content in question — the algorithm learns from your corrections.</p>
""".strip(),
    },
    "choisir-son-pseudo": {
        "title": "Choosing your username",
        "body_html": """
<p>The first time you sign in to the portal, MediaKeeper asks you to <strong>choose a username</strong>. Until then, other members see a temporary username drawn at random (“Blue-Fox-42”): it cannot be kept. A few rules to know:</p>
<ul>
  <li>The username must be <strong>unique</strong> on the platform (case does not count: “Lola” and “lola” are the same).</li>
  <li>Between 3 and 50 characters long (2 are enough in Chinese or Korean). For the minimum, only letters, digits and symbols count.</li>
  <li>Some names are <strong>reserved</strong> and refused, as are their look-alikes and usernames where they read as a word (<em>SuperAdmin</em>, <em>Joe Root</em>): <em>admin, administrator, administrateur, root</em>.</li>
  <li>If the username is already taken, MediaKeeper suggests <strong>up to 5</strong> free alternatives (with a number at the end).</li>
  <li>If an administrator resets your username, choose a new one: the old one is no longer accepted.</li>
</ul>
<p><strong>6-month lock</strong>: once you have chosen or changed your username, you cannot change it again for <strong>180 days</strong>. This is on purpose, to prevent impersonation and to assure other users that one name means one stable person.</p>
<p>Administrators can lift the lock if you have a real reason to change (typo, incident).</p>
""".strip(),
    },
    "ajouter-un-avatar-perso": {
        "title": "Adding a custom avatar",
        "body_html": """
<p>By default, your avatar comes from Emby. You can <strong>replace</strong> it with an image of your choice from <strong>Settings → Identity → Avatar</strong>.</p>
<ul>
  <li><strong>Accepted formats</strong>: JPEG, PNG, WebP, GIF.</li>
  <li><strong>Maximum size</strong>: 5 MB.</li>
  <li><strong>Recommended</strong>: a square image, at least 256×256 pixels, so it looks sharp everywhere (profile card, leaderboard, comments).</li>
</ul>
<p>Your custom avatar <strong>always takes precedence</strong> over the Emby avatar. To go back to the Emby avatar, simply delete your custom avatar with the dedicated button.</p>
<p>Your avatar is stored on the server and never shared with a third party.</p>
""".strip(),
    },
    "visibilite-du-profil": {
        "title": "Profile visibility",
        "body_html": """
<p>In <strong>Settings → Visibility</strong> you choose who can see your profile and your statistics:</p>
<ul>
  <li><strong>Public</strong> — any signed-in user can open your page <code>/portal/u/&lt;your id&gt;</code> and see your level, your trophies and your favorite genres. You appear on the leaderboard.</li>
  <li><strong>Private</strong> — only you can see your page. Other users see a <em>“Private profile”</em> screen. You no longer appear on the public leaderboard.</li>
</ul>
<p>You can also fine-tune:</p>
<ul>
  <li><strong>Hide my ratings</strong> — your scores are not shown on your public page.</li>
  <li><strong>Hide my lists</strong> — only the lists you mark as public stay visible.</li>
  <li><strong>Hide my viewing statistics</strong> — total time, top genres, movies and series watched.</li>
</ul>
<p>You can change these settings at any time, with no cooldown.</p>
""".strip(),
    },
    "parametrer-son-compte": {
        "title": "Setting up your account",
        "body_html": """
<p>The <strong>Settings</strong> page gathers every setting of your account, in 5 tabs:</p>
<ol>
  <li><strong>Identity</strong> — username, bio, avatar.</li>
  <li><strong>Appearance</strong> — theme (light / dark / auto), custom accents, animations.</li>
  <li><strong>Preferences</strong> — language, favorite genres, adult content (allowed or not), default notifications.</li>
  <li><strong>Visibility</strong> — who can see your profile, your ratings, your lists (see the dedicated article).</li>
  <li><strong>Account</strong> — sign out everywhere, data deletion, export.</li>
</ol>
<p>All changes are <strong>saved in one go</strong> with the <em>Save</em> button at the bottom of the page. Until you click it, your changes are pending — a pulsing banner reminds you.</p>
""".strip(),
    },
    "comment-faire-une-demande": {
        "title": "How do I make a request?",
        "body_html": """
<p>MediaKeeper lets you request a movie or a series that is not in the library yet. Everything happens from the home page or the search:</p>
<ol>
  <li>On the <strong>home page</strong>, a featured title can be requested directly with the <strong>“Request”</strong> button.</li>
  <li>Otherwise, type its name in <strong>“Search”</strong>, at the top (the magnifier on a phone), then pick a suggestion or browse the results.</li>
  <li>Open the title's page and tap <strong>“Request”</strong>. With a mouse, the button also shows on the poster, in the results.</li>
  <li>In the <strong>“Make a request”</strong> window, confirm. For a series, first tick the seasons you want.</li>
</ol>
<p>The title switches to <em>“Requested”</em>. Once the request is approved and the title added, the notification bell tells you it is available.</p>
""".strip(),
    },
    "les-differents-tags": {
        "title": "The different tags",
        "body_html": """
<p>Each request shows one or more <strong>colored tags</strong> that sum up its progress at a glance:</p>
<ul>
  <li><strong>Pending</strong> — the request was just created and is waiting for the administrator's approval.</li>
  <li><strong>Approved</strong> — the administrator accepted the request, the download is scheduled.</li>
  <li><strong>In progress</strong> — the content is being added to the library.</li>
  <li><strong>Available</strong> — done, the content can be played on Emby. A notification was sent to you.</li>
  <li><strong>Rejected</strong> — the request was not accepted. The reason appears in the comments.</li>
  <li><strong>Unavailable</strong> — the content cannot be found in an acceptable quality, or is blocked for technical reasons.</li>
  <li><strong>Duplicate</strong> — another user already requested the same title; vote on the existing request.</li>
</ul>
<p>You can <strong>filter</strong> requests by tag from the list, to quickly see “everything available” or “everything pending”.</p>
""".strip(),
    },
    "les-quotas-de-demandes": {
        "title": "Request quotas",
        "body_html": """
<p>The number of requests you can send is limited <strong>per month</strong>. The administrator sets this limit, for each member.</p>
<ul>
  <li><strong>Every request you send counts</strong>, whatever happens next: approved, available or rejected, it stays counted until the end of the month. A request sent again after a rejection counts too.</li>
  <li>A series counts as <strong>a single request</strong>, even if you tick several seasons.</li>
  <li>The counter goes back to zero <strong>on the 1st of each month</strong>.</li>
</ul>
<p><strong>To follow your counter:</strong></p>
<ul>
  <li>In the <strong>“Today's digest”</strong> window (your avatar menu), the <strong>“Requests left”</strong> box.</li>
  <li>After each request, a message tells you how many you have used this month.</li>
  <li>Your requests and their status are in <strong>“My requests”</strong>, on <strong>“My profile”</strong>.</li>
</ul>
<p>When the limit is reached, the portal shows <em>“You've reached your monthly request quota.”</em> Wait for the next month, or talk to the administrator.</p>
<p>The administrator can also give you <strong>unlimited</strong> requests, or choose an <strong>automatic</strong> quota: it rises little by little while you are active (viewing, sign-ins, requests, lists, tickets) and only drops after a long absence.</p>
""".strip(),
    },
}
