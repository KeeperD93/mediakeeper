import type { Meta, StoryObj } from '@storybook/vue3-vite'
import MkButton from './MkButton.vue'

/* ──────────────────────────────────────────────────────────────────────
 * Inventaire visuel ADMIN UNIQUEMENT — Avant / Après migration MkButton
 *
 * Scope strict : seuls les boutons utilisant les tokens admin (sans
 * préfixe --portal-*). Les boutons portail seront couverts par un
 * composant séparé futur (<PortalButton>) pour respecter §3.4 de
 * Rules.md (séparation stricte admin ↔ portail).
 *
 * Colonne « Aperçu actuel » : reproduction fidèle du style trouvé dans
 * le code source MediaKeeper.
 * Colonne « Après MkButton » : rendu du composant <MkButton> qui va
 * remplacer la classe selon la taxonomie validée (6 variantes :
 * primary / danger / success / ghost / icon / link).
 *
 * Cas hors MkButton (composants custom préservés côté admin) :
 *   - Login submit (gradient + shimmer signature)
 * ────────────────────────────────────────────────────────────────────── */

const meta: Meta = {
  title: 'Design system/Inventaire MediaKeeper',
  parameters: {
    layout: 'fullscreen',
    backgrounds: { default: 'admin' },
  },
}
export default meta

type Story = StoryObj

export const Inventory: Story = {
  name: 'Admin — Avant / Après MkButton',
  render: () => ({
    components: { MkButton },
    template: `
      <div>
        <div class="inv-page">

          <h1 style="margin: 0 0 8px; color: #fff;">📋 Inventaire admin MediaKeeper — Avant / Après MkButton</h1>
          <p style="color: #a8b2c2; margin: 0 0 12px; max-width: 880px;">
            <strong>Scope : admin uniquement.</strong> Les boutons portail (préfixe <code>.pt-*</code>, listes,
            événements, daily digest, etc.) sont exclus et seront couverts par un composant séparé.
          </p>
          <p style="color: #a8b2c2; margin: 0 0 32px; max-width: 880px;">
            Pour chaque famille, comparaison <strong>côte à côte</strong> :<br>
            <strong>Colonne 1</strong> — reproduction fidèle du style ACTUEL.<br>
            <strong>Colonne 4</strong> — rendu après migration vers <code>&lt;MkButton&gt;</code>.
          </p>

          <!-- ═══════════════════════════════════════════════════════════ -->
          <div class="inv-section">
            <h2>🟦 Famille A — Solid accent (plein violet/indigo)</h2>
            <p class="intro">
              Background plein <code>var(--accent-600)</code>, texte blanc. Style "primary" canonique.
            </p>
            <div class="reco">💡 Migration : <code>variant="primary"</code> — pas de changement visuel</div>
            <table class="inv-table">
              <thead>
                <tr><th class="preview">Actuel (fidèle)</th><th class="name">Classe CSS</th><th class="where">Où ça vit</th><th class="preview">Après MkButton</th></tr>
              </thead>
              <tbody>
                <tr><td><button class="x-mk-flat-primary">Confirmer</button></td><td class="name">.wn-btn-primary</td><td class="where">Modale "Nouveautés" admin</td><td><MkButton variant="primary">Confirmer</MkButton></td></tr>
                <tr><td><button class="x-mk-flat-primary">Enregistrer</button></td><td class="name">.str-save-btn</td><td class="where">Paramètres → Planificateur</td><td><MkButton variant="primary" icon="save">Enregistrer</MkButton></td></tr>
                <tr><td><button class="x-mk-flat-primary">Enregistrer</button></td><td class="name">.nf-save-btn</td><td class="where">Notifications → Save bar</td><td><MkButton variant="primary" icon="save">Enregistrer</MkButton></td></tr>
              </tbody>
            </table>
          </div>

          <!-- ═══════════════════════════════════════════════════════════ -->
          <div class="inv-section">
            <h2>💜 Famille B — Tinted accent → devient PLEIN</h2>
            <p class="intro">
              Background accent translucide 18% + bord 30% + texte accent-400.
              Beaucoup de boutons "Enregistrer" admin actuellement (Santé média, Notifications).
            </p>
            <div class="reco">
              💡 Migration : <code>variant="primary"</code> — <strong>changement visuel notable</strong>.
            </div>
            <table class="inv-table">
              <thead>
                <tr><th class="preview">Actuel (fidèle)</th><th class="name">Classe CSS</th><th class="where">Où ça vit</th><th class="preview">Après MkButton</th></tr>
              </thead>
              <tbody>
                <tr><td><button class="x-mk-tinted-primary">💾 Enregistrer</button></td><td class="name">.hc-save-btn</td><td class="where">Santé média → Configuration</td><td><MkButton variant="primary" icon="save">Enregistrer</MkButton></td></tr>
                <tr><td><button class="x-mk-tinted-primary">▶ Lancer</button></td><td class="name">.str-run-btn</td><td class="where">Paramètres → Planificateur (Run)</td><td><MkButton variant="primary" icon="refresh-cw">Lancer</MkButton></td></tr>
                <tr><td><button class="x-mk-tinted-primary">+ Ajouter</button></td><td class="name">.nf-add-btn</td><td class="where">Notifications → Templates</td><td><MkButton variant="primary" icon="plus">Ajouter</MkButton></td></tr>
                <tr><td><button class="x-mk-tinted-primary">OK</button></td><td class="name">.mk-confirm-btn-info</td><td class="where">MkConfirmDialog (info/transverse)</td><td><MkButton variant="primary" icon="check">OK</MkButton></td></tr>
              </tbody>
            </table>
          </div>

          <!-- ═══════════════════════════════════════════════════════════ -->
          <div class="inv-section">
            <h2>🟣 Famille C — Pill gradient MM → devient PLEIN</h2>
            <p class="intro">
              Pill (radius 999px) + gradient translucide + halo concentrique accent.
              Style signature des modales Media Manager (Renommer, Déplacer, Dossier).
            </p>
            <div class="reco">
              💡 Migration : <code>variant="primary"</code> — <strong>perd la forme pill et le halo</strong>.
            </div>
            <table class="inv-table">
              <thead>
                <tr><th class="preview">Actuel (fidèle)</th><th class="name">Classe CSS</th><th class="where">Où ça vit</th><th class="preview">Après MkButton</th></tr>
              </thead>
              <tbody>
                <tr><td><button class="x-mk-pill-gradient">Renommer</button></td><td class="name">.mr-btn-primary</td><td class="where">Media Manager → Modale Renommer</td><td><MkButton variant="primary" icon="pencil">Renommer</MkButton></td></tr>
                <tr><td><button class="x-mk-pill-gradient">Déplacer</button></td><td class="name">.mv-btn-primary</td><td class="where">Media Manager → Modale Déplacer</td><td><MkButton variant="primary">Déplacer</MkButton></td></tr>
                <tr><td><button class="x-mk-pill-gradient">OK</button></td><td class="name">.mf-btn-primary</td><td class="where">Media Manager → Modale Dossier</td><td><MkButton variant="primary" icon="check">OK</MkButton></td></tr>
              </tbody>
            </table>
          </div>

          <!-- ═══════════════════════════════════════════════════════════ -->
          <div class="inv-section">
            <h2>🟪 Famille D — Gradient violet/indigo (login + onboarding)</h2>
            <p class="intro">
              <code>linear-gradient(135deg, indigo, purple)</code> + shadow accent. CTA premium admin.
            </p>
            <div class="reco">
              💡 Migration : <strong>login conservé</strong> (cas custom). L'onboarding "Lancer" passe en <code>primary</code>.
            </div>
            <table class="inv-table">
              <thead>
                <tr><th class="preview">Actuel (fidèle)</th><th class="name">Classe CSS</th><th class="where">Où ça vit</th><th class="preview">Après MkButton</th></tr>
              </thead>
              <tbody>
                <tr><td><button class="x-mk-gradient-login">Se connecter</button></td><td class="name">.login-submit</td><td class="where">Page de connexion admin (signature préservée)</td><td><button class="x-mk-gradient-login">Se connecter</button><br><span style="color:#a8b2c2;font-size:11px;">(reste hors MkButton)</span></td></tr>
                <tr><td><button class="x-mk-gradient-onboarding">Lancer</button></td><td class="name">.ob-btn-launch</td><td class="where">Onboarding wizard → Étape finale</td><td><MkButton variant="primary" icon-right="chevron-right">Lancer</MkButton></td></tr>
              </tbody>
            </table>
          </div>

          <!-- ═══════════════════════════════════════════════════════════ -->
          <div class="inv-section">
            <h2>🟥 Famille F — Tinted danger → devient PLEIN rouge</h2>
            <p class="intro">
              Background rouge translucide 15% + bord 30% + texte rouge clair.
              Style le plus utilisé pour "Supprimer" en admin actuellement.
            </p>
            <div class="reco">
              💡 Migration : <code>variant="danger"</code> — <strong>plein rouge plus tranché</strong>.
            </div>
            <table class="inv-table">
              <thead>
                <tr><th class="preview">Actuel (fidèle)</th><th class="name">Classe CSS</th><th class="where">Où ça vit</th><th class="preview">Après MkButton</th></tr>
              </thead>
              <tbody>
                <tr><td><button class="x-mk-tinted-danger">🗑 Supprimer</button></td><td class="name">.mm-btn-danger</td><td class="where">Media Manager → diverses modales</td><td><MkButton variant="danger" icon="trash-2">Supprimer</MkButton></td></tr>
                <tr><td><button class="x-mk-tinted-danger">Supprimer</button></td><td class="name">.mk-confirm-btn-danger</td><td class="where">MkConfirmDialog (transverse)</td><td><MkButton variant="danger">Supprimer</MkButton></td></tr>
                <tr><td><button class="x-mk-tinted-warn">Attention</button></td><td class="name">.mk-confirm-btn-warn</td><td class="where">MkConfirmDialog (variante warn)</td><td><MkButton variant="danger">Attention</MkButton><br><span style="color:#a8b2c2;font-size:11px;">(warn fusionné dans danger)</span></td></tr>
                <tr><td><button class="x-mk-tinted-danger">Supprimer</button></td><td class="name">.sec-btn-danger / .tool-btn-danger / .params-danger-btn / .nf-btn-danger</td><td class="where">Paramètres → Sécurité / Stats → Outils / Apparence / Notifications</td><td><MkButton variant="danger" icon="trash-2">Supprimer</MkButton></td></tr>
              </tbody>
            </table>
          </div>

          <!-- ═══════════════════════════════════════════════════════════ -->
          <div class="inv-section">
            <h2>🟢 Famille I — Tinted success → devient PLEIN VERT</h2>
            <p class="intro">
              Background vert translucide + bord vert + texte vert.
              Action positive (Valider).
            </p>
            <div class="reco">
              💡 Migration : <code>variant="success"</code> plein vert pour l'action.
              L'état "✓ Sauvegardé" transitoire devient un toast.
            </div>
            <table class="inv-table">
              <thead>
                <tr><th class="preview">Actuel (fidèle)</th><th class="name">Classe CSS</th><th class="where">Où ça vit</th><th class="preview">Après MkButton</th></tr>
              </thead>
              <tbody>
                <tr><td><button class="x-mk-tinted-success">✓ Valider</button></td><td class="name">.mm-btn-success</td><td class="where">Media Manager → action validation</td><td><MkButton variant="success" icon="check">Valider</MkButton></td></tr>
                <tr><td><button class="x-mk-tinted-success">✓ Sauvegardé</button></td><td class="name">.mm-btn-saved</td><td class="where">Media Manager → état post-save (transitoire)</td><td><span style="color:#a8b2c2;font-size:12px;font-style:italic;">→ Toast "Enregistré" via useToast</span></td></tr>
              </tbody>
            </table>
          </div>

          <!-- ═══════════════════════════════════════════════════════════ -->
          <div class="inv-section">
            <h2>⬜ Famille H — Ghost outline neutre (Annuler / Retour)</h2>
            <p class="intro">Background transparent + bord gris + texte gris/blanc. Action secondaire discrète.</p>
            <div class="reco">💡 Migration : <code>variant="ghost"</code> — pas de changement visuel.</div>
            <table class="inv-table">
              <thead>
                <tr><th class="preview">Actuel (fidèle)</th><th class="name">Classe CSS</th><th class="where">Où ça vit</th><th class="preview">Après MkButton</th></tr>
              </thead>
              <tbody>
                <tr><td><button class="x-mk-ghost-neutral">Annuler</button></td><td class="name">.wn-btn-secondary</td><td class="where">Modale Nouveautés admin</td><td><MkButton variant="ghost">Annuler</MkButton></td></tr>
                <tr><td><button class="x-mk-ghost-neutral">Annuler</button></td><td class="name">.mk-confirm-btn-cancel</td><td class="where">MkConfirmDialog (transverse)</td><td><MkButton variant="ghost">Annuler</MkButton></td></tr>
                <tr><td><button class="x-mk-ghost-neutral">← Retour</button></td><td class="name">.ob-btn-ghost</td><td class="where">Onboarding wizard → Précédent</td><td><MkButton variant="ghost" icon="chevron-left">Retour</MkButton></td></tr>
              </tbody>
            </table>
          </div>

          <!-- ═══════════════════════════════════════════════════════════ -->
          <div class="inv-section">
            <h2>⬜ Famille H-pill — Ghost pill MM → devient GHOST</h2>
            <p class="intro">Pill ghost dans modales Media Manager (associé à C pill gradient).</p>
            <div class="reco">💡 Migration : <code>variant="ghost"</code> — <strong>perd la forme pill</strong>.</div>
            <table class="inv-table">
              <thead>
                <tr><th class="preview">Actuel (fidèle)</th><th class="name">Classe CSS</th><th class="where">Où ça vit</th><th class="preview">Après MkButton</th></tr>
              </thead>
              <tbody>
                <tr><td><button class="x-mk-pill-ghost">Annuler</button></td><td class="name">.mr-btn-ghost</td><td class="where">Media Manager → Modale Renommer</td><td><MkButton variant="ghost">Annuler</MkButton></td></tr>
                <tr><td><button class="x-mk-pill-ghost">Annuler</button></td><td class="name">.mv-btn-ghost</td><td class="where">Media Manager → Modale Déplacer</td><td><MkButton variant="ghost">Annuler</MkButton></td></tr>
                <tr><td><button class="x-mk-pill-ghost">Annuler</button></td><td class="name">.mf-btn-ghost</td><td class="where">Media Manager → Modale Dossier</td><td><MkButton variant="ghost">Annuler</MkButton></td></tr>
              </tbody>
            </table>
          </div>

          <!-- ═══════════════════════════════════════════════════════════ -->
          <div class="inv-section">
            <h2>⊕ Famille K-close — X de modales admin (icon)</h2>
            <p class="intro">
              Bouton X en haut à droite des modales admin. Instances identiques dans Media Manager,
              Recherche globale, Modale Nouveautés, etc.
            </p>
            <div class="reco">💡 Migration : <code>variant="icon" icon="x"</code>.</div>
            <table class="inv-table">
              <thead>
                <tr><th class="preview">Actuel (fidèle)</th><th class="name">Classe CSS</th><th class="where">Où ça vit</th><th class="preview">Après MkButton</th></tr>
              </thead>
              <tbody>
                <tr><td><button class="x-mk-icon-close">✕</button></td><td class="name">.wn-close</td><td class="where">Modale Nouveautés admin</td><td><MkButton variant="icon" icon="x" ariaLabel="Fermer" /></td></tr>
                <tr><td><button class="x-mk-icon-close">✕</button></td><td class="name">.sm-close</td><td class="where">Modale Recherche globale (admin)</td><td><MkButton variant="icon" icon="x" ariaLabel="Fermer" /></td></tr>
                <tr><td><button class="x-mk-icon-close">✕</button></td><td class="name">.mf-close / .mv-close / .mr-close</td><td class="where">Media Manager (3 modales)</td><td><MkButton variant="icon" icon="x" ariaLabel="Fermer" /></td></tr>
                <tr><td><button class="x-mk-icon-close">✕</button></td><td class="name">.mm-close-btn / .wlsu-detail-close</td><td class="where">Media Manager + Watchlist Suivi (admin)</td><td><MkButton variant="icon" icon="x" ariaLabel="Fermer" /></td></tr>
              </tbody>
            </table>
          </div>

          <!-- ═══════════════════════════════════════════════════════════ -->
          <div class="inv-section">
            <h2>⚙ Famille K — Icône seule admin (engrenage, crayon)</h2>
            <p class="intro">Bouton compact 32×32 avec icône lucide. Header de carte, toolbar admin.</p>
            <div class="reco">💡 Migration : <code>variant="icon" icon="..."</code>.</div>
            <table class="inv-table">
              <thead>
                <tr><th class="preview">Actuel (fidèle)</th><th class="name">Classe CSS</th><th class="where">Où ça vit</th><th class="preview">Après MkButton</th></tr>
              </thead>
              <tbody>
                <tr><td><button class="x-mk-icon-square">✎</button></td><td class="name">.ru-icon-btn</td><td class="where">Admin → Demandes utilisateurs</td><td><MkButton variant="icon" icon="pencil" ariaLabel="Modifier" /></td></tr>
              </tbody>
            </table>
          </div>

          <!-- ═══════════════════════════════════════════════════════════ -->
          <div class="inv-section">
            <h2>⊝ Famille L — Mini "Retirer" → devient ICON sm</h2>
            <p class="intro">
              Mini bouton circulaire 18×18 pour retirer un élément d'une liste/tag admin.
            </p>
            <div class="reco">
              💡 Migration : <code>variant="icon" icon="x" size="sm"</code>.
              <br>(Le rendu MkButton est carré 28×28 — légère différence vs le rond 18×18 actuel.)
            </div>
            <table class="inv-table">
              <thead>
                <tr><th class="preview">Actuel (fidèle)</th><th class="name">Classe CSS</th><th class="where">Où ça vit</th><th class="preview">Après MkButton</th></tr>
              </thead>
              <tbody>
                <tr><td>Marvel <button class="x-mk-mini-remove">✕</button></td><td class="name">.ru-tag-remove</td><td class="where">Admin → Tags utilisateur</td><td>Marvel <MkButton variant="icon" icon="x" size="sm" ariaLabel="Retirer" /></td></tr>
                <tr><td>/films <button class="x-mk-mini-remove">✕</button></td><td class="name">.ob-folder-remove</td><td class="where">Onboarding → Étape dossiers</td><td>/films <MkButton variant="icon" icon="x" size="sm" ariaLabel="Retirer" /></td></tr>
              </tbody>
            </table>
          </div>

          <!-- ═══════════════════════════════════════════════════════════ -->
          <div class="inv-section">
            <h2>🔗 Famille J — Skip / Lien (sans bordure)</h2>
            <p class="intro">
              Bouton très discret : texte seul, pas de fond, pas de bord. Pour "Passer", "Plus tard".
            </p>
            <div class="reco">💡 Migration : <code>variant="link"</code> (nouveau).</div>
            <table class="inv-table">
              <thead>
                <tr><th class="preview">Actuel (fidèle)</th><th class="name">Classe CSS</th><th class="where">Où ça vit</th><th class="preview">Après MkButton</th></tr>
              </thead>
              <tbody>
                <tr><td><button class="x-mk-skip">Passer</button></td><td class="name">.ob-btn-skip</td><td class="where">Onboarding → Skip étape</td><td><MkButton variant="link">Passer</MkButton></td></tr>
              </tbody>
            </table>
          </div>

          <!-- ═══════════════════════════════════════════════════════════ -->
          <div class="inv-section" style="border-top: 1px solid rgb(255,255,255,0.1); padding-top: 32px;">
            <h2>📊 Synthèse migration (admin only)</h2>
            <table class="inv-table">
              <thead>
                <tr><th>Famille</th><th>Action</th><th>Cible MkButton</th></tr>
              </thead>
              <tbody>
                <tr><td>A — Solid accent</td><td>identique</td><td><code>primary</code></td></tr>
                <tr><td>B — Tinted accent</td><td>⚠ changement visuel</td><td><code>primary</code></td></tr>
                <tr><td>C — Pill gradient MM</td><td>⚠ perd pill + halo</td><td><code>primary</code></td></tr>
                <tr><td>D — Gradient onboarding</td><td>⚠ perd gradient</td><td><code>primary</code></td></tr>
                <tr><td>D — login submit</td><td>conservé</td><td>custom (hors MkButton)</td></tr>
                <tr><td>F — Tinted danger / warn</td><td>⚠ changement visuel</td><td><code>danger</code></td></tr>
                <tr><td>I — Tinted success (action)</td><td>⚠ devient plein vert</td><td><code>success</code></td></tr>
                <tr><td>I — Tinted success (état)</td><td>devient toast</td><td>useToast</td></tr>
                <tr><td>H — Ghost outline</td><td>identique</td><td><code>ghost</code></td></tr>
                <tr><td>H-pill — Ghost pill MM</td><td>⚠ perd pill</td><td><code>ghost</code></td></tr>
                <tr><td>K-close — X de modale</td><td>identique</td><td><code>icon</code> + <code>icon="x"</code></td></tr>
                <tr><td>K — Icon-only (engrenage, edit)</td><td>identique</td><td><code>icon</code></td></tr>
                <tr><td>L — Mini remove</td><td>⚠ devient carré 28×28</td><td><code>icon size="sm"</code></td></tr>
                <tr><td>J — Skip / lien</td><td>nouveau</td><td><code>link</code></td></tr>
              </tbody>
            </table>
            <p style="color: #a8b2c2; margin-top: 16px; max-width: 880px;">
              Les boutons portail (préfixe <code>.pt-*</code>, listes, soirées ciné, daily digest…) ne sont pas
              concernés par <code>&lt;MkButton&gt;</code> — ils auront leur propre composant futur avec les
              tokens <code>--portal-*</code>.
            </p>
          </div>

        </div>
      </div>
    `,
  }),
}
