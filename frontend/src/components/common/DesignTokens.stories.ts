import type { Meta, StoryObj } from '@storybook/vue3-vite'

/* ──────────────────────────────────────────────────────────────────────
 * MediaKeeper — Design tokens reference (admin namespace).
 *
 * Exhaustive catalogue of every token defined in:
 *   • frontend/src/styles/main.css            (theme block, accent palette, chrome)
 *   • frontend/src/styles/tokens/_colors.css  (surfaces, borders, semantics)
 *   • frontend/src/styles/tokens/_typography.css
 *   • frontend/src/styles/tokens/_motion.css
 *   • frontend/src/styles/tokens/_layout.css  (spacing, radius, shadow, blur, z…)
 *   • frontend/src/styles/tokens/_tiers.css   (rank c1/c2/c3 + glow)
 *   • frontend/src/styles/tokens/_avatar-tiers.css
 *
 * Portal-namespaced tokens (``--portal-*``) live in
 * frontend/src/styles/portal/tokens/ and have their own future catalogue.
 * Rules.md §3.4 forbids mixing the two namespaces.
 *
 * Each swatch displays its computed runtime value via the small
 * ``data-token`` resolver script appended to every story.
 * ────────────────────────────────────────────────────────────────────── */

const meta: Meta = {
  title: 'Design system/Design tokens',
  parameters: {
    layout: 'fullscreen',
    backgrounds: { default: 'admin' },
  },
}
export default meta

type Story = StoryObj

/* The ``.tk-*`` styles ship via .storybook/design-tokens.css (loaded
 * globally by preview.ts). The runtime token resolver lives in
 * .storybook/design-tokens.js so every story page can read it after
 * Vue is done rendering. */
const styles = ''
const resolveTokenScript = ''

function swatch(
  token: string,
  usage: string,
  opts: {
    background?: string
    check?: boolean
    tall?: boolean
    sampleText?: string
    color?: string
  } = {},
) {
  const bg = opts.background ?? `var(${token})`
  const cls = [
    'tk-swatch',
    opts.check ? 'tk-swatch--check' : '',
    opts.tall ? 'tk-swatch--tall' : '',
    opts.sampleText ? 'tk-swatch--text' : '',
  ]
    .filter(Boolean)
    .join(' ')
  const content = opts.sampleText
    ? `<span style="color: ${opts.color ?? `var(${token})`}; font-weight: 600; font-size: 14px;">${opts.sampleText}</span>`
    : ''
  return `
    <div class="tk-card">
      <div class="${cls}" style="background: ${bg};">${content}</div>
      <div class="tk-meta">
        <span class="tk-name">${token}</span>
        <span class="tk-val" data-token="${token}">…</span>
        <span class="tk-use">${usage}</span>
      </div>
    </div>
  `
}

/* ────────────────────────────────────────────────────────────────────── */
/* 1. Overview                                                            */
/* ────────────────────────────────────────────────────────────────────── */
export const Overview: Story = {
  name: "1. Vue d'ensemble",
  render: () => ({
    template: `
      ${styles}
      <div class="tk-page">
        <h1 class="tk-h1">🎨 MediaKeeper — Catalogue des design tokens</h1>
        <p class="tk-intro">
          Catalogue exhaustif des tokens du <strong>namespace admin</strong>. Les tokens portail
          (<code>--portal-*</code>) ont leur propre catalogue séparé — Rules.md §3.4 interdit de
          mélanger les deux namespaces.
        </p>
        <p class="tk-intro">
          Le système couleurs est volontairement segmenté en <strong>4 couches indépendantes</strong>
          pour que modifier une couche ne propage jamais sur les autres.
        </p>
        <div class="tk-layer-banner"><strong>Couche 1 — <code>--mk-btn-*</code></strong> · signature locked, boutons MkButton uniquement.</div>
        <div class="tk-layer-banner"><strong>Couche 2 — <code>--color-*</code></strong> · sémantique (success / error / warning / info) — graphiques, jauges, badges.</div>
        <div class="tk-layer-banner"><strong>Couche 3 — <code>--accent-*</code></strong> · décorations globales (halos, focus, hovers).</div>
        <div class="tk-layer-banner"><strong>Couche 4 — <code>--text-highlight</code></strong> · émphase typo (compteurs, XP, headers).</div>

        <div class="tk-section">
          <h2>Sommaire</h2>
          <div class="tk-toc">
            <ol>
              <li><strong>Couleurs</strong>
                <ol>
                  <li>Boutons (couche 1)</li>
                  <li>Sémantique (couche 2)</li>
                  <li>Accent (couche 3)</li>
                  <li>Émphase texte (couche 4)</li>
                  <li>Fonds & chrome admin</li>
                  <li>Surfaces & overlays</li>
                  <li>Bordures</li>
                  <li>Texte (échelle de lisibilité)</li>
                  <li>Modules</li>
                  <li>Tiers (rangs)</li>
                  <li>Avatar tiers (anneaux)</li>
                </ol>
              </li>
              <li><strong>Typographie</strong> · tailles, poids, tracking, line-height, familles</li>
              <li><strong>Espacement & layout</strong> · spacing, radius, border widths, containers, aspect ratios</li>
              <li><strong>Animation</strong> · durées, easings, transitions composites, gradients animés</li>
              <li><strong>Effets visuels</strong> · shadows, blurs, opacity, focus rings, scrollbar, icons, text shadows, gradients, glow</li>
              <li><strong>Z-index</strong> · hiérarchie d'empilement</li>
            </ol>
          </div>
        </div>
      </div>
    `,
  }),
}

/* ────────────────────────────────────────────────────────────────────── */
/* 2. Couleurs — Couche 1 boutons                                          */
/* ────────────────────────────────────────────────────────────────────── */
export const ColorsButtons: Story = {
  name: '2. Couleurs — Couche 1 (boutons --mk-btn-*)',
  render: () => ({
    template: `
      ${styles}
      <div class="tk-page">
        <h1 class="tk-h1">🟪 Couche 1 — Boutons MkButton</h1>
        <p class="tk-intro">
          <strong>Locked, signature MediaKeeper.</strong> Uniquement consommé par <code>&lt;MkButton&gt;</code>
          (variants <code>primary</code>, <code>danger</code>, <code>success</code>). Chaque variant a
          3 états : base, hover, active.
        </p>

        <div class="tk-section">
          <h2>Primary — violet MK</h2>
          <p class="lead">Action principale (Enregistrer, Confirmer, Lancer).</p>
          <div class="tk-grid">
            ${swatch('--mk-btn-primary', 'Base — état repos')}
            ${swatch('--mk-btn-primary-hover', 'Hover')}
            ${swatch('--mk-btn-primary-active', 'Active (clic)')}
          </div>
        </div>

        <div class="tk-section">
          <h2>Danger — rouge brique</h2>
          <p class="lead">Action destructive (Supprimer, Purger).</p>
          <div class="tk-grid">
            ${swatch('--mk-btn-danger', 'Base')}
            ${swatch('--mk-btn-danger-hover', 'Hover')}
            ${swatch('--mk-btn-danger-active', 'Active')}
          </div>
        </div>

        <div class="tk-section">
          <h2>Success — vert forêt</h2>
          <p class="lead">Confirmation positive (Valider).</p>
          <div class="tk-grid">
            ${swatch('--mk-btn-success', 'Base')}
            ${swatch('--mk-btn-success-hover', 'Hover')}
            ${swatch('--mk-btn-success-active', 'Active')}
          </div>
        </div>
      </div>
      ${resolveTokenScript}
    `,
  }),
}

/* ────────────────────────────────────────────────────────────────────── */
/* 3. Couleurs — Couche 2 sémantique                                       */
/* ────────────────────────────────────────────────────────────────────── */
export const ColorsSemantic: Story = {
  name: '3. Couleurs — Couche 2 (sémantique --color-*)',
  render: () => ({
    template: `
      ${styles}
      <div class="tk-page">
        <h1 class="tk-h1">🌈 Couche 2 — Sémantique</h1>
        <p class="tk-intro">
          <strong>Tons clairs, lisibles sur fond sombre.</strong> Pour graphiques (CPU, RAM, courbes),
          jauges, badges, toasts, icônes status. Chaque famille a 3 strengths : <code>canonical</code>
          (texte/icône), <code>light</code> (hover), <code>soft</code> (fond pastille). RGB companions
          dispos pour composer des transparences via <code>rgba(var(--color-X-rgb), a)</code>.
        </p>

        <div class="tk-section">
          <h2>✅ Success</h2>
          <div class="tk-grid">
            ${swatch('--color-success', 'Canonical — courbe CPU OK, icône check')}
            ${swatch('--color-success-light', 'Hover')}
            ${swatch('--color-success-soft', 'Fond pastille')}
          </div>
        </div>

        <div class="tk-section">
          <h2>⚠ Warning</h2>
          <div class="tk-grid">
            ${swatch('--color-warning', 'Canonical — alerte, ETA, transcode')}
            ${swatch('--color-warning-light', 'Hover')}
            ${swatch('--color-warning-soft', 'Fond pastille')}
          </div>
        </div>

        <div class="tk-section">
          <h2>❌ Error</h2>
          <div class="tk-grid">
            ${swatch('--color-error', 'Canonical — erreur, jauge RAM saturée')}
            ${swatch('--color-error-light', 'Hover')}
            ${swatch('--color-error-soft', 'Fond pastille')}
            ${swatch('--color-error-strong', 'Badge non lu, alerte critique')}
          </div>
        </div>

        <div class="tk-section">
          <h2>ℹ Info</h2>
          <div class="tk-grid">
            ${swatch('--color-info', 'Canonical — info, lien neutre')}
            ${swatch('--color-info-light', 'Hover')}
            ${swatch('--color-info-soft', 'Fond pastille')}
          </div>
        </div>

        <div class="tk-section">
          <h2>⚪ On-accent</h2>
          <p class="lead">Texte/icône posé sur fond accent saturé.</p>
          <div class="tk-grid">
            ${swatch('--color-on-accent', 'Label des boutons primary/danger/success')}
          </div>
        </div>
      </div>
      ${resolveTokenScript}
    `,
  }),
}

/* ────────────────────────────────────────────────────────────────────── */
/* 4. Couleurs — Couche 3 accent                                           */
/* ────────────────────────────────────────────────────────────────────── */
export const ColorsAccent: Story = {
  name: '4. Couleurs — Couche 3 (accent --accent-*)',
  render: () => ({
    template: `
      ${styles}
      <div class="tk-page">
        <h1 class="tk-h1">💫 Couche 3 — Accent global</h1>
        <p class="tk-intro">
          Halos, focus rings, bordures actives d'onglets, hovers de listes. Échelle 9 nuances (50 → 900)
          calquée sur Tailwind. Pilotable via <code>useTheme.applyAccent()</code> (picker UI dormant,
          code prêt à être réactivé). Par défaut : indigo Tailwind.
        </p>

        <div class="tk-section">
          <h2>Échelle complète (50 → 900)</h2>
          <div class="tk-grid">
            ${swatch('--accent-50', 'Backgrounds très clairs')}
            ${swatch('--accent-100', 'Pastilles légères')}
            ${swatch('--accent-200', 'Tints discrets')}
            ${swatch('--accent-300', 'Texte secondaire accent')}
            ${swatch('--accent-400', 'Hover icônes')}
            ${swatch('--accent-500', 'Référence — focus ring, surlignage actif')}
            ${swatch('--accent-600', 'Variante profonde')}
            ${swatch('--accent-700', 'Pressed / actif')}
            ${swatch('--accent-800', 'Très profond')}
            ${swatch('--accent-900', 'Quasi noir teinté')}
          </div>
        </div>

        <div class="tk-section">
          <h2>RGB companion + alias</h2>
          <p class="lead">Permet <code>rgb(var(--accent-rgb), 0.x)</code> pour halos / glow.</p>
          <div class="tk-grid">
            <div class="tk-card">
              <div class="tk-swatch" style="background: rgb(var(--accent-rgb), 0.85);"></div>
              <div class="tk-meta">
                <span class="tk-name">--accent-rgb @ 85%</span>
                <span class="tk-val" data-token="--accent-rgb">…</span>
                <span class="tk-use">Glow fort</span>
              </div>
            </div>
            <div class="tk-card">
              <div class="tk-swatch" style="background: rgb(var(--accent-rgb), 0.5);"></div>
              <div class="tk-meta">
                <span class="tk-name">--accent-rgb @ 50%</span>
                <span class="tk-val">—</span>
                <span class="tk-use">Halo moyen</span>
              </div>
            </div>
            <div class="tk-card">
              <div class="tk-swatch" style="background: rgb(var(--accent-rgb), 0.2);"></div>
              <div class="tk-meta">
                <span class="tk-name">--accent-rgb @ 20%</span>
                <span class="tk-val">—</span>
                <span class="tk-use">Halo discret</span>
              </div>
            </div>
            ${swatch('--accent', 'Alias legacy — utilise --accent-700')}
            ${swatch('--accent-light', 'Alias legacy — utilise --accent-700 + 33 alpha')}
          </div>
        </div>
      </div>
      ${resolveTokenScript}
    `,
  }),
}

/* ────────────────────────────────────────────────────────────────────── */
/* 5. Couleurs — Couche 4 émphase texte                                    */
/* ────────────────────────────────────────────────────────────────────── */
export const ColorsTextHighlight: Story = {
  name: '5. Couleurs — Couche 4 (émphase --text-highlight)',
  render: () => ({
    template: `
      ${styles}
      <div class="tk-page">
        <h1 class="tk-h1">📝 Couche 4 — Émphase texte</h1>
        <p class="tk-intro">
          Token dédié à l'émphase typographique, distinct de l'accent global. Remplace
          <code>color: var(--accent-*)</code> sur du texte (compteurs, XP, headers). Par défaut
          <code>= --text-primary</code> (blanc) pour que les surfaces "highlight" ne pullulent pas
          l'accent global sur la copie. Une seule variable à modifier pour repeindre toutes les
          émphases du projet.
        </p>

        <div class="tk-section">
          <h2>Token actif</h2>
          <div class="tk-grid">
            ${swatch('--text-highlight', 'Compteurs, XP totals, headers mis en avant')}
          </div>
        </div>

        <div class="tk-section">
          <h2>Exemple en situation</h2>
          <div class="tk-card" style="grid-column: 1 / -1;">
            <div class="tk-demo">
              Yunaïka <span style="color: var(--text-highlight); font-weight: 600;">127 500 XP</span>
              · LÉGENDE
              <div style="color: #a8b2c2; font-size: 12px; margin-top: 6px;">
                La valeur XP en émphase utilise <code style="background: rgb(255,255,255,0.06); padding: 1px 4px; border-radius: 3px;">color: var(--text-highlight)</code>
                au lieu de <code style="background: rgb(255,255,255,0.06); padding: 1px 4px; border-radius: 3px;">color: var(--accent-500)</code>.
              </div>
            </div>
          </div>
        </div>
      </div>
      ${resolveTokenScript}
    `,
  }),
}

/* ────────────────────────────────────────────────────────────────────── */
/* 6. Couleurs — Fonds & chrome admin                                      */
/* ────────────────────────────────────────────────────────────────────── */
export const ColorsBackgrounds: Story = {
  name: '6. Couleurs — Fonds & chrome',
  render: () => ({
    template: `
      ${styles}
      <div class="tk-page">
        <h1 class="tk-h1">🪟 Fonds & chrome admin</h1>
        <p class="tk-intro">
          Hiérarchie de fonds sombres + chrome admin (sidebar, topbar). Définis directement dans
          <code>main.css</code> :root du thème admin.
        </p>

        <div class="tk-section">
          <h2>Fonds page</h2>
          <div class="tk-grid">
            ${swatch('--bg-primary', 'Fond principal — body / app')}
            ${swatch('--bg-secondary', 'Cartes, panels — un cran plus clair que primary')}
            ${swatch('--bg-tertiary', 'Couches empilées, layers')}
            ${swatch('--bg-panel', 'Alias = bg-secondary — modal / panel')}
          </div>
        </div>

        <div class="tk-section">
          <h2>Chrome admin (sidebar + topbar)</h2>
          <div class="tk-grid">
            ${swatch('--mk-chrome-bg', 'Sidebar + topbar surface')}
            ${swatch('--mk-chrome-gradient', 'Gradient vertical sidebar (top → bottom)', { background: 'var(--mk-chrome-gradient)' })}
            ${swatch('--mk-chrome-gradient-top', 'Stop haut du gradient chrome')}
            ${swatch('--mk-chrome-gradient-bottom', 'Stop bas du gradient chrome')}
          </div>
        </div>

        <div class="tk-section">
          <h2>RGB companions (pour transparences)</h2>
          <div class="tk-grid">
            <div class="tk-card">
              <div class="tk-swatch" style="background: rgb(var(--bg-primary-rgb), 0.8);"></div>
              <div class="tk-meta">
                <span class="tk-name">--bg-primary-rgb @ 80%</span>
                <span class="tk-val" data-token="--bg-primary-rgb">…</span>
                <span class="tk-use">Composer rgba() depuis le fond primary</span>
              </div>
            </div>
            <div class="tk-card">
              <div class="tk-swatch" style="background: rgb(var(--mk-chrome-bg-rgb), 0.85);"></div>
              <div class="tk-meta">
                <span class="tk-name">--mk-chrome-bg-rgb @ 85%</span>
                <span class="tk-val" data-token="--mk-chrome-bg-rgb">…</span>
                <span class="tk-use">Composer rgba() depuis le chrome</span>
              </div>
            </div>
          </div>
        </div>

        <div class="tk-section">
          <h2>Bordures globales (main.css)</h2>
          <p class="lead">Distinct des <code>--border-*</code> de la couche surfaces.</p>
          <div class="tk-grid">
            ${swatch('--border', 'Bordure par défaut — séparation subtile sur thème sombre')}
            ${swatch('--border-hover', 'Bordure hover/focus — différenciation claire')}
          </div>
        </div>
      </div>
      ${resolveTokenScript}
    `,
  }),
}

/* ────────────────────────────────────────────────────────────────────── */
/* 7. Couleurs — Surfaces & overlays                                       */
/* ────────────────────────────────────────────────────────────────────── */
export const ColorsSurfaces: Story = {
  name: '7. Couleurs — Surfaces & overlays',
  render: () => ({
    template: `
      ${styles}
      <div class="tk-page">
        <h1 class="tk-h1">🧊 Surfaces "glass" & overlays</h1>
        <p class="tk-intro">
          Hiérarchie de surfaces translucides (effet "glass") en 3 niveaux pour empiler cartes / panels
          sans saturer. Les overlays sont des fonds opaques pour modales / dropdowns.
        </p>

        <div class="tk-section">
          <h2>Glass surfaces</h2>
          <div class="tk-grid">
            ${swatch('--surface-1', 'Base — cartes, panels')}
            ${swatch('--surface-2', 'Hover, seconde couche')}
            ${swatch('--surface-3', 'Active / pressed / tertiaire')}
          </div>
        </div>

        <div class="tk-section">
          <h2>Overlays</h2>
          <div class="tk-grid">
            ${swatch('--overlay-bg', 'Corps de modale / dropdown')}
            ${swatch('--overlay-backdrop', 'Voile derrière les modales')}
          </div>
        </div>
      </div>
      ${resolveTokenScript}
    `,
  }),
}

/* ────────────────────────────────────────────────────────────────────── */
/* 8. Couleurs — Bordures                                                  */
/* ────────────────────────────────────────────────────────────────────── */
export const ColorsBorders: Story = {
  name: '8. Couleurs — Bordures',
  render: () => ({
    template: `
      ${styles}
      <div class="tk-page">
        <h1 class="tk-h1">▭ Bordures</h1>
        <p class="tk-intro">
          Échelle de forces de bordure, du plus subtil au plus marqué. Les deux dernières
          (<code>ghost</code> / <code>ghost-hover</code>) sont dédiées aux boutons ghost / icon.
        </p>

        <div class="tk-section">
          <div class="tk-grid">
            ${swatch('--border-subtle', 'Sur surface-1')}
            ${swatch('--border-default', 'Cartes standard')}
            ${swatch('--border-strong', 'Modales, dropdowns')}
            ${swatch('--border-intense', 'Hover sur surfaces prominentes')}
            ${swatch('--border-ghost', 'MkButton ghost/icon — au repos')}
            ${swatch('--border-ghost-hover', 'MkButton ghost/icon — hover')}
          </div>
        </div>
      </div>
      ${resolveTokenScript}
    `,
  }),
}

/* ────────────────────────────────────────────────────────────────────── */
/* 9. Couleurs — Texte (échelle de lisibilité)                             */
/* ────────────────────────────────────────────────────────────────────── */
export const ColorsText: Story = {
  name: '9. Couleurs — Texte',
  render: () => ({
    template: `
      ${styles}
      <div class="tk-page">
        <h1 class="tk-h1">🅰 Couleurs de texte</h1>
        <p class="tk-intro">
          Hiérarchie de couleur pour la copie. <code>--text-primary</code> / <code>secondary</code> /
          <code>muted</code> sont définis dans <code>main.css</code>. Les extensions
          (<code>faint</code>, <code>very-faint</code>, <code>decorative</code>) couvrent les patterns
          <code>rgba(255,255,255,x)</code> qui dérivaient ailleurs.
        </p>

        <div class="tk-section">
          <h2>Aperçu lisibilité</h2>
          <div class="tk-card" style="grid-column: 1 / -1;">
            <div class="tk-demo">
              <div class="tk-demo-row" style="color: var(--text-primary); font-size: 15px;">--text-primary — Aa Bb Cc 0123 — Titres, valeurs principales</div>
              <div class="tk-demo-row" style="color: var(--text-secondary); font-size: 14px;">--text-secondary — Aa Bb Cc 0123 — Corps de texte</div>
              <div class="tk-demo-row" style="color: var(--text-muted); font-size: 13px;">--text-muted — Aa Bb Cc 0123 — Labels, légendes</div>
              <div class="tk-demo-row" style="color: var(--text-faint); font-size: 13px;">--text-faint — Aa Bb Cc 0123 — Labels désactivés, hints</div>
              <div class="tk-demo-row" style="color: var(--text-very-faint); font-size: 12px;">--text-very-faint — Aa Bb Cc 0123 — Placeholders, sub-hints</div>
              <div class="tk-demo-row" style="color: var(--text-decorative); font-size: 11px;">--text-decorative — Aa Bb Cc 0123 — Version footer, décoratif</div>
              <div class="tk-demo-row" style="color: var(--text-highlight); font-size: 14px; font-weight: 600;">--text-highlight — Aa Bb Cc 0123 — Émphase couche 4</div>
            </div>
          </div>
        </div>

        <div class="tk-section">
          <h2>Tokens</h2>
          <div class="tk-grid">
            ${swatch('--text-primary', 'main.css — titres, valeurs principales', { sampleText: 'Aa', color: 'var(--text-primary)' })}
            ${swatch('--text-secondary', 'main.css — corps de texte', { sampleText: 'Aa', color: 'var(--text-secondary)' })}
            ${swatch('--text-muted', 'main.css — labels, légendes', { sampleText: 'Aa', color: 'var(--text-muted)' })}
            ${swatch('--text-faint', '_colors.css — labels désactivés', { sampleText: 'Aa', color: 'var(--text-faint)' })}
            ${swatch('--text-very-faint', '_colors.css — placeholders', { sampleText: 'Aa', color: 'var(--text-very-faint)' })}
            ${swatch('--text-decorative', '_colors.css — footer version', { sampleText: 'Aa', color: 'var(--text-decorative)' })}
          </div>
        </div>

        <div class="tk-section">
          <h2>RGB companion</h2>
          <p class="lead">Pour composer <code>rgba(var(--text-primary-rgb), 0.X)</code> sans redéfinir.</p>
          <div class="tk-grid">
            <div class="tk-card">
              <div class="tk-swatch tk-swatch--text">
                <span style="color: rgb(var(--text-primary-rgb), 0.6); font-weight: 500;">@ 60%</span>
              </div>
              <div class="tk-meta">
                <span class="tk-name">--text-primary-rgb</span>
                <span class="tk-val" data-token="--text-primary-rgb">…</span>
                <span class="tk-use">Composer rgba() depuis le blanc principal</span>
              </div>
            </div>
          </div>
        </div>
      </div>
      ${resolveTokenScript}
    `,
  }),
}

/* ────────────────────────────────────────────────────────────────────── */
/* 10. Couleurs — Modules                                                  */
/* ────────────────────────────────────────────────────────────────────── */
export const ColorsModules: Story = {
  name: '10. Couleurs — Modules',
  render: () => ({
    template: `
      ${styles}
      <div class="tk-page">
        <h1 class="tk-h1">🧩 Couleurs de modules</h1>
        <p class="tk-intro">
          Chaque module MediaKeeper a une couleur signature stable utilisée dans son icône sidebar,
          ses badges, ses indicateurs. Volontairement <strong>hors couche accent</strong> pour que
          l'identité du module reste constante.
        </p>

        <div class="tk-section">
          <div class="tk-grid">
            ${swatch('--color-module-watchlist', 'Suivi séries — purple')}
            ${swatch('--color-module-stats', 'Stats lecture — green')}
            ${swatch('--color-module-duplicates', 'Nettoyage doublons — rose')}
            ${swatch('--color-module-healthcheck', 'Santé média — cyan')}
            ${swatch('--color-module-notifications', 'Notifications / webhooks — amber')}
            ${swatch('--color-module-subtitles', 'Outillage sous-titres — magenta')}
          </div>
        </div>
      </div>
      ${resolveTokenScript}
    `,
  }),
}

/* ────────────────────────────────────────────────────────────────────── */
/* 11. Couleurs — Tiers (rangs admin)                                      */
/* ────────────────────────────────────────────────────────────────────── */
export const ColorsTiers: Story = {
  name: '11. Couleurs — Tiers (rangs)',
  render: () => ({
    template: `
      ${styles}
      <div class="tk-page">
        <h1 class="tk-h1">🏅 Tiers (rangs)</h1>
        <p class="tk-intro">
          Palette de rangs (bronze → legendary) miroir des <code>--portal-tier-*</code> côté portail —
          mêmes hex pour garantir la cohérence admin / portail. Chaque tier a 3 stops (<code>c1</code>
          clair, <code>c2</code> medium, <code>c3</code> profond) + un <code>glow</code> compagnon
          pour les halos.
        </p>

        ${['bronze', 'silver', 'gold', 'platinum', 'diamond', 'master', 'legendary']
          .map(
            t => `
          <div class="tk-section">
            <h2 style="text-transform: capitalize;">${t}</h2>
            <div class="tk-grid">
              ${swatch(`--tier-${t}-c1`, 'Stop clair')}
              ${swatch(`--tier-${t}-c2`, 'Stop medium')}
              ${swatch(`--tier-${t}-c3`, 'Stop profond')}
              ${swatch(`--tier-${t}-glow`, 'Halo (rgba)')}
            </div>
          </div>
        `,
          )
          .join('')}
      </div>
      ${resolveTokenScript}
    `,
  }),
}

/* ────────────────────────────────────────────────────────────────────── */
/* 12. Couleurs — Avatar tiers                                             */
/* ────────────────────────────────────────────────────────────────────── */
export const ColorsAvatarTiers: Story = {
  name: '12. Couleurs — Avatar tiers',
  render: () => ({
    template: `
      ${styles}
      <div class="tk-page">
        <h1 class="tk-h1">⭕ Avatar tiers — anneaux</h1>
        <p class="tk-intro">
          Palette dédiée aux anneaux d'avatar (MkAvatar). Distincte des <code>--tier-*</code> rangs car
          MkAvatar tourne aussi en contexte admin (topbar, stats, requests) où les
          <code>--portal-color-*</code> ne sont pas dispo. Halos additionnels pour gold+.
        </p>

        <div class="tk-section">
          <div class="tk-grid">
            ${swatch('--mk-tier-bronze', 'Ring bronze — défaut historique / Emby-only')}
            ${swatch('--mk-tier-silver', 'Ring silver — niveau 6-10')}
            ${swatch('--mk-tier-gold', 'Ring gold — niveau 11-19')}
            ${swatch('--mk-tier-platinum', 'Ring platinum — niveau 20-29')}
            ${swatch('--mk-tier-diamond', 'Ring diamond — niveau 30-39')}
            ${swatch('--mk-tier-master', 'Ring master — niveau 40-49')}
            <!-- Legendary (50+) has no flat ring colour: its ring is a spinning
                 rainbow conic-gradient (see .mk-avatar-tier--legendary::after in
                 _avatar-tiers.css), not a single swatchable token. -->
          </div>
        </div>

        <div class="tk-section">
          <h2>RGB companions (pour halos box-shadow)</h2>
          <p class="lead">Diamond + legendary ont un halo-rgb distinct du ring pour effet de profondeur.</p>
          <div class="tk-grid">
            ${swatch('--mk-tier-gold-rgb', 'rgba(…) halo gold', { background: 'rgb(var(--mk-tier-gold-rgb), 0.6)' })}
            ${swatch('--mk-tier-platinum-rgb', 'rgba(…) halo platinum', { background: 'rgb(var(--mk-tier-platinum-rgb), 0.6)' })}
            ${swatch('--mk-tier-diamond-halo-rgb', 'rgba(…) halo diamond', { background: 'rgb(var(--mk-tier-diamond-halo-rgb), 0.6)' })}
            ${swatch('--mk-tier-master-rgb', 'rgba(…) halo master', { background: 'rgb(var(--mk-tier-master-rgb), 0.6)' })}
            ${swatch('--mk-tier-legendary-rgb', 'rgba(…) halo legendary inner', { background: 'rgb(var(--mk-tier-legendary-rgb), 0.6)' })}
            ${swatch('--mk-tier-legendary-halo-rgb', 'rgba(…) halo legendary outer', { background: 'rgb(var(--mk-tier-legendary-halo-rgb), 0.6)' })}
          </div>
        </div>
      </div>
      ${resolveTokenScript}
    `,
  }),
}

/* ────────────────────────────────────────────────────────────────────── */
/* 13. Typographie                                                         */
/* ────────────────────────────────────────────────────────────────────── */
export const Typography: Story = {
  name: '13. Typographie',
  render: () => ({
    template: `
      ${styles}
      <div class="tk-page">
        <h1 class="tk-h1">🅰 Typographie</h1>
        <p class="tk-intro">
          Échelle de tailles "Tailwind-like" (3xs → xl) qui absorbe ~70% des font-sizes existants.
          Poids, tracking, line-height et familles ont des noms sémantiques.
        </p>

        <div class="tk-section">
          <h2>Tailles (font-size)</h2>
          <div class="tk-card" style="grid-column: 1 / -1;">
            <div class="tk-demo">
              <div class="tk-demo-row" style="font-size: var(--text-3xs);">--text-3xs — 0.62rem — tags, mini badges</div>
              <div class="tk-demo-row" style="font-size: var(--text-2xs);">--text-2xs — 0.7rem — pill buttons, meta compact</div>
              <div class="tk-demo-row" style="font-size: var(--text-xs);">--text-xs — 0.75rem — table cells, texte secondaire</div>
              <div class="tk-demo-row" style="font-size: var(--text-sm);">--text-sm — 0.82rem — body small</div>
              <div class="tk-demo-row" style="font-size: var(--text-base);">--text-base — 0.9rem — body</div>
              <div class="tk-demo-row" style="font-size: var(--text-md);">--text-md — 1rem — section titles</div>
              <div class="tk-demo-row" style="font-size: var(--text-lg);">--text-lg — 1.3rem — KPI values</div>
              <div class="tk-demo-row" style="font-size: var(--text-xl);">--text-xl — clamp() — titres responsive</div>
            </div>
          </div>
        </div>

        <div class="tk-section">
          <h2>Poids (font-weight)</h2>
          <div class="tk-card" style="grid-column: 1 / -1;">
            <div class="tk-demo">
              <div class="tk-demo-row" style="font-weight: var(--font-regular);">--font-regular (500) — body, nav items</div>
              <div class="tk-demo-row" style="font-weight: var(--font-medium);">--font-medium (600) — labels, section titles</div>
              <div class="tk-demo-row" style="font-weight: var(--font-bold);">--font-bold (700) — KPIs, emphase forte</div>
              <div class="tk-demo-row" style="font-weight: var(--font-extrabold);">--font-extrabold (800) — pill buttons, standard app</div>
            </div>
          </div>
        </div>

        <div class="tk-section">
          <h2>Letter spacing (tracking)</h2>
          <div class="tk-card" style="grid-column: 1 / -1;">
            <div class="tk-demo">
              <div class="tk-demo-row" style="letter-spacing: var(--tracking-tight);">--tracking-tight (-0.02em) — titres de page</div>
              <div class="tk-demo-row" style="letter-spacing: var(--tracking-normal);">--tracking-normal (0) — défaut</div>
              <div class="tk-demo-row" style="letter-spacing: var(--tracking-wide);">--tracking-wide (0.02em) — pill buttons</div>
              <div class="tk-demo-row" style="letter-spacing: var(--tracking-widest); text-transform: uppercase;">--tracking-widest (0.06em) — labels uppercase</div>
            </div>
          </div>
        </div>

        <div class="tk-section">
          <h2>Line height</h2>
          <div class="tk-card" style="grid-column: 1 / -1;">
            <div class="tk-demo">
              <div class="tk-demo-row" style="line-height: var(--lh-tight); background: rgb(255,255,255,0.02); padding: 4px;">--lh-tight (1) — counters inline, KPI values</div>
              <div class="tk-demo-row" style="line-height: var(--lh-snug-tight); background: rgb(255,255,255,0.02); padding: 4px;">--lh-snug-tight (1.2) — display headings compactes</div>
              <div class="tk-demo-row" style="line-height: var(--lh-compact); background: rgb(255,255,255,0.02); padding: 4px;">--lh-compact (1.3) — titres, listes denses</div>
              <div class="tk-demo-row" style="line-height: var(--lh-snug); background: rgb(255,255,255,0.02); padding: 4px;">--lh-snug (1.4) — captions aérées</div>
              <div class="tk-demo-row" style="line-height: var(--lh-normal); background: rgb(255,255,255,0.02); padding: 4px;">--lh-normal (1.5) — paragraphes</div>
              <div class="tk-demo-row" style="line-height: var(--lh-relaxed); background: rgb(255,255,255,0.02); padding: 4px;">--lh-relaxed (1.6) — long-form descriptions</div>
            </div>
          </div>
        </div>

        <div class="tk-section">
          <h2>Familles (font-family)</h2>
          <div class="tk-card" style="grid-column: 1 / -1;">
            <div class="tk-demo">
              <div class="tk-demo-row" style="font-family: var(--font-system); font-size: 14px;">--font-system — Aa Bb Cc 0123 — Stack système (Apple, Segoe, Roboto, etc.)</div>
              <div class="tk-demo-row" style="font-family: var(--font-mono); font-size: 14px;">--font-mono — Aa Bb Cc 0123 — Stack monospace (SF Mono, Consolas, etc.)</div>
            </div>
          </div>
        </div>
      </div>
      ${resolveTokenScript}
    `,
  }),
}

/* ────────────────────────────────────────────────────────────────────── */
/* 14. Espacement & layout                                                 */
/* ────────────────────────────────────────────────────────────────────── */
export const SpacingLayout: Story = {
  name: '14. Espacement & layout',
  render: () => ({
    template: `
      ${styles}
      <div class="tk-page">
        <h1 class="tk-h1">📐 Espacement & layout</h1>
        <p class="tk-intro">
          Échelle d'espacement 8px grid + half-step 4px. Border widths réduisent les 287
          <code>0.5px</code> et 156 <code>1px</code> hardcodés à 2 tokens. Radius pilotés par le
          slider Apparence + les tokens fixes <code>pill</code> / <code>circle</code>.
        </p>

        <div class="tk-section">
          <h2>Spacing scale (8px grid)</h2>
          <div class="tk-card" style="grid-column: 1 / -1;">
            <div class="tk-demo">
              ${[1, 2, 3, 4, 5, 6, 8]
                .map(
                  n => `
                <div class="tk-demo-row" style="display: flex; align-items: center; gap: 14px;">
                  <span style="background: var(--accent-500); height: 14px; width: var(--space-${n}); border-radius: 2px;"></span>
                  <span style="font-family: 'SF Mono', monospace; font-size: 12px;">--space-${n}</span>
                  <span style="font-family: 'SF Mono', monospace; font-size: 11px; color: #a8b2c2;" data-token="--space-${n}">…</span>
                </div>
              `,
                )
                .join('')}
              <div class="tk-demo-row" style="display: flex; align-items: center; gap: 14px; padding-top: 6px;">
                <span style="background: var(--color-success); height: 14px; width: var(--touch-target); border-radius: 2px;"></span>
                <span style="font-family: 'SF Mono', monospace; font-size: 12px;">--touch-target</span>
                <span style="font-family: 'SF Mono', monospace; font-size: 11px; color: #a8b2c2;" data-token="--touch-target">…</span>
                <span style="font-size: 11px; color: #a8b2c2;">WCAG 2.5.5 minimum (mobile)</span>
              </div>
            </div>
          </div>
        </div>

        <div class="tk-section">
          <h2>Border widths</h2>
          <div class="tk-grid">
            <div class="tk-card">
              <div class="tk-swatch" style="background: #1f2126; border: var(--border-width-thin) solid #fff;"></div>
              <div class="tk-meta">
                <span class="tk-name">--border-width-thin</span>
                <span class="tk-val" data-token="--border-width-thin">…</span>
                <span class="tk-use">0.5px — défaut app, cartes, dividers</span>
              </div>
            </div>
            <div class="tk-card">
              <div class="tk-swatch" style="background: #1f2126; border: var(--border-width) solid #fff;"></div>
              <div class="tk-meta">
                <span class="tk-name">--border-width</span>
                <span class="tk-val" data-token="--border-width">…</span>
                <span class="tk-use">1px — modales, inputs</span>
              </div>
            </div>
          </div>
        </div>

        <div class="tk-section">
          <h2>Radius</h2>
          <div class="tk-grid">
            <div class="tk-card"><div class="tk-swatch" style="background: var(--accent-500); border-radius: var(--radius-sm);"></div><div class="tk-meta"><span class="tk-name">--radius-sm</span><span class="tk-val" data-token="--radius-sm">…</span><span class="tk-use">Pastilles, mini badges (fixe)</span></div></div>
            <div class="tk-card"><div class="tk-swatch" style="background: var(--accent-500); border-radius: var(--radius-btn);"></div><div class="tk-meta"><span class="tk-name">--radius-btn</span><span class="tk-val" data-token="--radius-btn">…</span><span class="tk-use">Boutons — pilotable via slider Apparence</span></div></div>
            <div class="tk-card"><div class="tk-swatch" style="background: var(--accent-500); border-radius: var(--radius-input);"></div><div class="tk-meta"><span class="tk-name">--radius-input</span><span class="tk-val" data-token="--radius-input">…</span><span class="tk-use">Inputs — pilotable via slider</span></div></div>
            <div class="tk-card"><div class="tk-swatch" style="background: var(--accent-500); border-radius: var(--radius-card);"></div><div class="tk-meta"><span class="tk-name">--radius-card</span><span class="tk-val" data-token="--radius-card">…</span><span class="tk-use">Cartes — pilotable via slider</span></div></div>
            <div class="tk-card"><div class="tk-swatch" style="background: var(--accent-500); border-radius: var(--radius-pill); height: 28px; width: 100px; margin: 15px auto;"></div><div class="tk-meta"><span class="tk-name">--radius-pill</span><span class="tk-val" data-token="--radius-pill">…</span><span class="tk-use">999px — pills, badges D-shape</span></div></div>
            <div class="tk-card"><div class="tk-swatch" style="background: var(--accent-500); border-radius: var(--radius-circle); width: 50px; height: 50px; margin: 4px auto;"></div><div class="tk-meta"><span class="tk-name">--radius-circle</span><span class="tk-val" data-token="--radius-circle">…</span><span class="tk-use">50% — avatars, status dots</span></div></div>
          </div>
        </div>

        <div class="tk-section">
          <h2>Container widths (page-level)</h2>
          <div class="tk-grid">
            ${swatch('--container-narrow', 'Article-style content (720px)', { background: 'var(--accent-500)' })}
            ${swatch('--container-default', 'Pages admin standard (1080px)', { background: 'var(--accent-500)' })}
            ${swatch('--container-wide', 'Dashboards, tables (1280px)', { background: 'var(--accent-500)' })}
            ${swatch('--container-full', 'Edge-to-edge (1800px)', { background: 'var(--accent-500)' })}
          </div>
        </div>

        <div class="tk-section">
          <h2>Aspect ratios (média)</h2>
          <div class="tk-grid">
            <div class="tk-card"><div class="tk-swatch" style="background: var(--accent-500); aspect-ratio: var(--aspect-poster); height: 80px;"></div><div class="tk-meta"><span class="tk-name">--aspect-poster</span><span class="tk-val" data-token="--aspect-poster">…</span><span class="tk-use">2/3 — poster film/série</span></div></div>
            <div class="tk-card"><div class="tk-swatch" style="background: var(--accent-500); aspect-ratio: var(--aspect-backdrop); height: 50px;"></div><div class="tk-meta"><span class="tk-name">--aspect-backdrop</span><span class="tk-val" data-token="--aspect-backdrop">…</span><span class="tk-use">16/9 — backdrop TMDB, hero</span></div></div>
            <div class="tk-card"><div class="tk-swatch" style="background: var(--accent-500); aspect-ratio: var(--aspect-square); height: 50px;"></div><div class="tk-meta"><span class="tk-name">--aspect-square</span><span class="tk-val" data-token="--aspect-square">…</span><span class="tk-use">1/1 — thumbnails carrées, avatars</span></div></div>
            <div class="tk-card"><div class="tk-swatch" style="background: var(--accent-500); aspect-ratio: var(--aspect-banner); height: 40px;"></div><div class="tk-meta"><span class="tk-name">--aspect-banner</span><span class="tk-val" data-token="--aspect-banner">…</span><span class="tk-use">3/1 — banners horizontaux, hero strips</span></div></div>
          </div>
        </div>

        <div class="tk-section">
          <h2>Sidebar</h2>
          <div class="tk-grid">
            ${swatch('--sidebar-width', 'Largeur sidebar admin déployée (état réduit géré inline)', { background: 'var(--mk-chrome-bg)' })}
          </div>
        </div>
      </div>
      ${resolveTokenScript}
    `,
  }),
}

/* ────────────────────────────────────────────────────────────────────── */
/* 15. Animation                                                           */
/* ────────────────────────────────────────────────────────────────────── */
export const Animation: Story = {
  name: '15. Animation',
  render: () => ({
    template: `
      ${styles}
      <style>
        .tk-anim-demo { background: var(--accent-500); width: 40px; height: 40px; border-radius: 6px; }
        .tk-anim-fast { animation: tk-pulse var(--duration-fast) var(--ease-default) infinite alternate; }
        .tk-anim-base { animation: tk-pulse var(--duration-base) var(--ease-default) infinite alternate; }
        .tk-anim-slow { animation: tk-pulse var(--duration-slow) var(--ease-default) infinite alternate; }
        .tk-anim-slower { animation: tk-pulse var(--duration-slower) var(--ease-default) infinite alternate; }
        .tk-anim-animation { animation: tk-pulse var(--duration-animation) var(--ease-linear) infinite; }
        .tk-anim-pulse { animation: tk-pulse var(--duration-pulse) var(--ease-in-out) infinite; }
        @keyframes tk-pulse { from { opacity: 0.3; transform: scale(0.8); } to { opacity: 1; transform: scale(1.1); } }
      </style>
      <div class="tk-page">
        <h1 class="tk-h1">⏱ Animation</h1>
        <p class="tk-intro">
          Durées séparées en interactions courtes vs animations continues. Easings = 3 courbes
          canoniques + linear pour spinners. Transitions composites pré-faites pour les patterns
          courants.
        </p>

        <div class="tk-section">
          <h2>Durations</h2>
          <div class="tk-grid">
            <div class="tk-card"><div class="tk-swatch"><div class="tk-anim-demo tk-anim-fast"></div></div><div class="tk-meta"><span class="tk-name">--duration-fast</span><span class="tk-val" data-token="--duration-fast">…</span><span class="tk-use">Hover, focus — snappy</span></div></div>
            <div class="tk-card"><div class="tk-swatch"><div class="tk-anim-demo tk-anim-base"></div></div><div class="tk-meta"><span class="tk-name">--duration-base</span><span class="tk-val" data-token="--duration-base">…</span><span class="tk-use">Transitions d'état standard</span></div></div>
            <div class="tk-card"><div class="tk-swatch"><div class="tk-anim-demo tk-anim-slow"></div></div><div class="tk-meta"><span class="tk-name">--duration-slow</span><span class="tk-val" data-token="--duration-slow">…</span><span class="tk-use">Enter/leave, expand/collapse</span></div></div>
            <div class="tk-card"><div class="tk-swatch"><div class="tk-anim-demo tk-anim-slower"></div></div><div class="tk-meta"><span class="tk-name">--duration-slower</span><span class="tk-val" data-token="--duration-slower">…</span><span class="tk-use">Cérémonies, transitions de route</span></div></div>
            <div class="tk-card"><div class="tk-swatch"><div class="tk-anim-demo tk-anim-animation"></div></div><div class="tk-meta"><span class="tk-name">--duration-animation</span><span class="tk-val" data-token="--duration-animation">…</span><span class="tk-use">Skeleton shimmer, progress stripes</span></div></div>
            <div class="tk-card"><div class="tk-swatch"><div class="tk-anim-demo tk-anim-pulse"></div></div><div class="tk-meta"><span class="tk-name">--duration-pulse</span><span class="tk-val" data-token="--duration-pulse">…</span><span class="tk-use">Status indicators pulsants</span></div></div>
          </div>
        </div>

        <div class="tk-section">
          <h2>Easings</h2>
          <div class="tk-grid">
            ${swatch('--ease-default', 'ease — courbe générique', { background: '#1f2126' })}
            ${swatch('--ease-out', 'spring-out — modales, sheets', { background: '#1f2126' })}
            ${swatch('--ease-in-out', 'Material — drawers, sidebar', { background: '#1f2126' })}
            ${swatch('--ease-linear', 'linear — spinners, progress', { background: '#1f2126' })}
          </div>
        </div>

        <div class="tk-section">
          <h2>Transitions composites (shorthand)</h2>
          <p class="lead">À utiliser au lieu de réécrire property + duration + easing à chaque fois.</p>
          <div class="tk-grid">
            ${swatch('--transition-color', 'color — labels qui changent de teinte', { background: '#1f2126' })}
            ${swatch('--transition-bg', 'background — fonds en hover', { background: '#1f2126' })}
            ${swatch('--transition-border', 'border-color — outlines en hover', { background: '#1f2126' })}
            ${swatch('--transition-transform', 'transform — translate/scale', { background: '#1f2126' })}
            ${swatch('--transition-opacity', 'opacity — fade in/out', { background: '#1f2126' })}
          </div>
        </div>

        <div class="tk-section">
          <h2>Gradient skeleton shimmer</h2>
          <p class="lead">Combiner avec <code>--duration-animation</code> + <code>--ease-in-out</code> sur placeholders de chargement.</p>
          <div class="tk-grid">
            <div class="tk-card"><div class="tk-swatch" style="background: var(--gradient-skeleton-shimmer);"></div><div class="tk-meta"><span class="tk-name">--gradient-skeleton-shimmer</span><span class="tk-val">linear-gradient(…)</span><span class="tk-use">Placeholder de loading</span></div></div>
          </div>
        </div>
      </div>
      ${resolveTokenScript}
    `,
  }),
}

/* ────────────────────────────────────────────────────────────────────── */
/* 16. Effets visuels                                                      */
/* ────────────────────────────────────────────────────────────────────── */
export const Effects: Story = {
  name: '16. Effets visuels',
  render: () => ({
    template: `
      ${styles}
      <div class="tk-page">
        <h1 class="tk-h1">✨ Effets visuels</h1>
        <p class="tk-intro">
          Shadows par profondeur (sm → xl) + alias sémantiques (card/button/dropdown/popover/modal).
          Blurs combinés blur + saturate pour effet "glass". Opacity sémantique. Focus rings, scrollbar,
          icon sizes, text shadows, gradients, glow.
        </p>

        <div class="tk-section">
          <h2>Shadows (par profondeur)</h2>
          <div class="tk-grid tk-grid--wide">
            <div class="tk-card"><div class="tk-shadow-demo" style="box-shadow: var(--shadow-sm);"></div><div class="tk-meta"><span class="tk-name">--shadow-sm</span><span class="tk-val" data-token="--shadow-sm">…</span><span class="tk-use">Cartes au hover</span></div></div>
            <div class="tk-card"><div class="tk-shadow-demo" style="box-shadow: var(--shadow-md);"></div><div class="tk-meta"><span class="tk-name">--shadow-md</span><span class="tk-val" data-token="--shadow-md">…</span><span class="tk-use">Cartes élevées</span></div></div>
            <div class="tk-card"><div class="tk-shadow-demo" style="box-shadow: var(--shadow-lg);"></div><div class="tk-meta"><span class="tk-name">--shadow-lg</span><span class="tk-val" data-token="--shadow-lg">…</span><span class="tk-use">Dropdowns, popovers</span></div></div>
            <div class="tk-card"><div class="tk-shadow-demo" style="box-shadow: var(--shadow-xl);"></div><div class="tk-meta"><span class="tk-name">--shadow-xl</span><span class="tk-val" data-token="--shadow-xl">…</span><span class="tk-use">Modales</span></div></div>
          </div>
        </div>

        <div class="tk-section">
          <h2>Shadows (alias sémantiques)</h2>
          <div class="tk-grid tk-grid--wide">
            <div class="tk-card"><div class="tk-shadow-demo" style="box-shadow: var(--shadow-card);"></div><div class="tk-meta"><span class="tk-name">--shadow-card</span><span class="tk-val">= --shadow-sm</span><span class="tk-use">Glass cards in-flow</span></div></div>
            <div class="tk-card"><div class="tk-shadow-demo" style="box-shadow: var(--shadow-button);"></div><div class="tk-meta"><span class="tk-name">--shadow-button</span><span class="tk-val">= --shadow-sm</span><span class="tk-use">Boutons surélevés, pills</span></div></div>
            <div class="tk-card"><div class="tk-shadow-demo" style="box-shadow: var(--shadow-dropdown);"></div><div class="tk-meta"><span class="tk-name">--shadow-dropdown</span><span class="tk-val">= --shadow-lg</span><span class="tk-use">Nav popovers, selects</span></div></div>
            <div class="tk-card"><div class="tk-shadow-demo" style="box-shadow: var(--shadow-popover);"></div><div class="tk-meta"><span class="tk-name">--shadow-popover</span><span class="tk-val">= --shadow-lg</span><span class="tk-use">Popovers contextuels</span></div></div>
            <div class="tk-card"><div class="tk-shadow-demo" style="box-shadow: var(--shadow-modal);"></div><div class="tk-meta"><span class="tk-name">--shadow-modal</span><span class="tk-val">= --shadow-xl</span><span class="tk-use">Modales pleines, dialogs</span></div></div>
          </div>
        </div>

        <div class="tk-section">
          <h2>Blurs (backdrop-filter)</h2>
          <p class="lead">Combinés blur + saturate pour profondeur "glass". Posé sur un fond coloré pour l'effet visible.</p>
          <div class="tk-grid">
            <div class="tk-card"><div class="tk-blur-demo"><div style="position: absolute; inset: 0; backdrop-filter: var(--blur-xs); background: rgb(0,0,0,0.1);"></div></div><div class="tk-meta"><span class="tk-name">--blur-xs</span><span class="tk-val" data-token="--blur-xs">…</span><span class="tk-use">Petites surfaces, pills</span></div></div>
            <div class="tk-card"><div class="tk-blur-demo"><div style="position: absolute; inset: 0; backdrop-filter: var(--blur-sm); background: rgb(0,0,0,0.1);"></div></div><div class="tk-meta"><span class="tk-name">--blur-sm</span><span class="tk-val" data-token="--blur-sm">…</span><span class="tk-use">Cartes secondaires</span></div></div>
            <div class="tk-card"><div class="tk-blur-demo"><div style="position: absolute; inset: 0; backdrop-filter: var(--blur-md); background: rgb(0,0,0,0.1);"></div></div><div class="tk-meta"><span class="tk-name">--blur-md</span><span class="tk-val" data-token="--blur-md">…</span><span class="tk-use">Cartes glass standard</span></div></div>
            <div class="tk-card"><div class="tk-blur-demo"><div style="position: absolute; inset: 0; backdrop-filter: var(--blur-lg); background: rgb(0,0,0,0.1);"></div></div><div class="tk-meta"><span class="tk-name">--blur-lg</span><span class="tk-val" data-token="--blur-lg">…</span><span class="tk-use">Topbar, sidebar, modales</span></div></div>
          </div>
        </div>

        <div class="tk-section">
          <h2>Opacity (états UI sémantiques)</h2>
          <div class="tk-grid">
            <div class="tk-card"><div class="tk-swatch" style="background: var(--accent-500); opacity: var(--opacity-disabled);"></div><div class="tk-meta"><span class="tk-name">--opacity-disabled</span><span class="tk-val" data-token="--opacity-disabled">…</span><span class="tk-use">Boutons, inputs désactivés</span></div></div>
            <div class="tk-card"><div class="tk-swatch" style="background: var(--accent-500); opacity: var(--opacity-loading);"></div><div class="tk-meta"><span class="tk-name">--opacity-loading</span><span class="tk-val" data-token="--opacity-loading">…</span><span class="tk-use">Contenu en rafraîchissement</span></div></div>
            <div class="tk-card"><div class="tk-swatch" style="background: var(--accent-500); opacity: var(--opacity-skeleton);"></div><div class="tk-meta"><span class="tk-name">--opacity-skeleton</span><span class="tk-val" data-token="--opacity-skeleton">…</span><span class="tk-use">Shimmer placeholder</span></div></div>
            <div class="tk-card"><div class="tk-swatch" style="background: var(--accent-500); opacity: var(--opacity-hover);"></div><div class="tk-meta"><span class="tk-name">--opacity-hover</span><span class="tk-val" data-token="--opacity-hover">…</span><span class="tk-use">Image / overlay dim au hover</span></div></div>
          </div>
        </div>

        <div class="tk-section">
          <h2>Focus rings (a11y)</h2>
          <p class="lead">Appliqué via <code>:focus-visible</code> sur tous les éléments interactifs (Rules §23).</p>
          <div class="tk-grid">
            <div class="tk-card"><div class="tk-swatch" style="background: var(--surface-2); outline: var(--focus-ring); outline-offset: var(--focus-ring-offset);"></div><div class="tk-meta"><span class="tk-name">--focus-ring (composite)</span><span class="tk-val" data-token="--focus-ring">…</span><span class="tk-use">Outline complet prêt à poser</span></div></div>
            ${swatch('--focus-ring-color', 'Couleur de la bordure focus')}
            ${swatch('--focus-ring-width', '2px par défaut', { background: 'var(--accent-500)' })}
            ${swatch('--focus-ring-offset', '2px par défaut', { background: 'var(--accent-500)' })}
          </div>
        </div>

        <div class="tk-section">
          <h2>Scrollbar (custom webkit)</h2>
          <div class="tk-grid">
            ${swatch('--scrollbar-width', 'Épaisseur scrollbar (6px)', { background: 'var(--scrollbar-thumb)' })}
            ${swatch('--scrollbar-thumb', 'Couleur thumb au repos', { background: 'var(--scrollbar-thumb)' })}
            ${swatch('--scrollbar-thumb-hover', 'Couleur thumb au hover', { background: 'var(--scrollbar-thumb-hover)' })}
            ${swatch('--scrollbar-track', 'Couleur track (transparent par défaut)', { check: true })}
          </div>
        </div>

        <div class="tk-section">
          <h2>Icon sizes (lucide-vue-next :size)</h2>
          <p class="lead">Résolvent vers un entier px (pas de px suffix). À passer en prop <code>:size</code>.</p>
          <div class="tk-grid">
            ${swatch('--icon-xs', '12px — pastilles, mini badges')}
            ${swatch('--icon-sm', '14px — boutons sm, table cells')}
            ${swatch('--icon-md', '16px — boutons md, défaut')}
            ${swatch('--icon-lg', '20px — boutons lg, headers')}
            ${swatch('--icon-xl', '24px — hero, page titles')}
            ${swatch('--icon-2xl', '32px — onboarding, empty states')}
          </div>
        </div>

        <div class="tk-section">
          <h2>Text shadows</h2>
          <div class="tk-grid">
            <div class="tk-card"><div class="tk-swatch" style="background: linear-gradient(45deg, #6366f1, #f43f5e);"><span style="color: #fff; font-weight: 600; text-shadow: var(--text-shadow-subtle);">Aa subtle</span></div><div class="tk-meta"><span class="tk-name">--text-shadow-subtle</span><span class="tk-val" data-token="--text-shadow-subtle">…</span><span class="tk-use">Lisibilité légère</span></div></div>
            <div class="tk-card"><div class="tk-swatch" style="background: linear-gradient(45deg, #6366f1, #f43f5e);"><span style="color: #fff; font-weight: 600; text-shadow: var(--text-shadow-strong);">Aa strong</span></div><div class="tk-meta"><span class="tk-name">--text-shadow-strong</span><span class="tk-val" data-token="--text-shadow-strong">…</span><span class="tk-use">Modales / backdrops</span></div></div>
            <div class="tk-card"><div class="tk-swatch" style="background: linear-gradient(45deg, #6366f1, #f43f5e);"><span style="color: #fff; font-weight: 600; text-shadow: var(--text-shadow-hero);">Aa hero</span></div><div class="tk-meta"><span class="tk-name">--text-shadow-hero</span><span class="tk-val" data-token="--text-shadow-hero">…</span><span class="tk-use">Titres sur images/vidéos</span></div></div>
          </div>
        </div>

        <div class="tk-section">
          <h2>Gradients</h2>
          <div class="tk-grid">
            <div class="tk-card"><div class="tk-swatch" style="background: var(--gradient-pill-active);"></div><div class="tk-meta"><span class="tk-name">--gradient-pill-active</span><span class="tk-val">linear-gradient(…)</span><span class="tk-use">État actif d'un pill button</span></div></div>
            <div class="tk-card"><div class="tk-swatch" style="background: #1f2126;"><div style="background: var(--gradient-shine); position: absolute; inset: 0;"></div></div><div class="tk-meta"><span class="tk-name">--gradient-shine</span><span class="tk-val">linear-gradient(…)</span><span class="tk-use">Reflet "shine" animé</span></div></div>
          </div>
        </div>

        <div class="tk-section">
          <h2>Pill glow (halo accent)</h2>
          <p class="lead">Pilotable via <code>--mk-glow</code> (slider Apparence, 0 → 2, défaut 1).</p>
          <div class="tk-grid">
            <div class="tk-card"><div class="tk-swatch" style="background: var(--accent-500); border-radius: 999px; height: 40px; width: 100px; margin: 9px auto; box-shadow: var(--mk-pill-shadow);"></div><div class="tk-meta"><span class="tk-name">--mk-pill-shadow</span><span class="tk-val">box-shadow composite</span><span class="tk-use">Halo standard (3px ring + 18px blur)</span></div></div>
            <div class="tk-card"><div class="tk-swatch" style="background: var(--accent-500); border-radius: 999px; height: 28px; width: 80px; margin: 15px auto; box-shadow: var(--mk-pill-shadow-sm);"></div><div class="tk-meta"><span class="tk-name">--mk-pill-shadow-sm</span><span class="tk-val">box-shadow composite</span><span class="tk-use">Halo compact (2px ring + 12px blur)</span></div></div>
            ${swatch('--mk-glow', "Multiplicateur d'intensité (0=off, 2=boost)", { background: 'var(--surface-2)' })}
          </div>
        </div>
      </div>
      ${resolveTokenScript}
    `,
  }),
}

/* ────────────────────────────────────────────────────────────────────── */
/* 17. Z-index                                                             */
/* ────────────────────────────────────────────────────────────────────── */
export const ZIndex: Story = {
  name: '17. Z-index',
  render: () => ({
    template: `
      ${styles}
      <div class="tk-page">
        <h1 class="tk-h1">🗂 Z-index — hiérarchie d'empilement</h1>
        <p class="tk-intro">
          Échelle géométrique qui laisse de l'espace entre couches pour que rien ne collision.
          Du bas (z-base) au sommet (z-reconnect overlay backend-down).
        </p>

        <div class="tk-section">
          <div class="tk-card" style="grid-column: 1 / -1;">
            <div class="tk-demo">
              <div class="tk-z-bar" style="background: var(--accent-100); color: #1f2126; font-family: 'SF Mono', monospace;">--z-base — <span data-token="--z-base">…</span> · empilement local d'une carte</div>
              <div class="tk-z-bar" style="background: var(--accent-200); color: #1f2126; font-family: 'SF Mono', monospace; margin-top: 4px;">--z-dropdown — <span data-token="--z-dropdown">…</span> · context menus, popovers</div>
              <div class="tk-z-bar" style="background: var(--accent-300); color: #1f2126; font-family: 'SF Mono', monospace; margin-top: 4px;">--z-sticky — <span data-token="--z-sticky">…</span> · sticky tabs, topbar</div>
              <div class="tk-z-bar" style="background: var(--accent-400); font-family: 'SF Mono', monospace; margin-top: 4px;">--z-drawer — <span data-token="--z-drawer">…</span> · drawer sidebar mobile</div>
              <div class="tk-z-bar" style="background: var(--accent-500); font-family: 'SF Mono', monospace; margin-top: 4px;">--z-modal — <span data-token="--z-modal">…</span> · modales standard</div>
              <div class="tk-z-bar" style="background: var(--accent-600); font-family: 'SF Mono', monospace; margin-top: 4px;">--z-overlay — <span data-token="--z-overlay">…</span> · overlays plein écran</div>
              <div class="tk-z-bar" style="background: var(--accent-700); font-family: 'SF Mono', monospace; margin-top: 4px;">--z-toast — <span data-token="--z-toast">…</span> · stack de toasts</div>
              <div class="tk-z-bar" style="background: var(--accent-800); font-family: 'SF Mono', monospace; margin-top: 4px;">--z-reconnect — <span data-token="--z-reconnect">…</span> · backend-down — au-dessus de tout</div>
            </div>
          </div>
        </div>
      </div>
      ${resolveTokenScript}
    `,
  }),
}
