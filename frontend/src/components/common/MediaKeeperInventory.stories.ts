import type { Meta, StoryObj } from '@storybook/vue3-vite'
import MkButton from './MkButton.vue'

/* ──────────────────────────────────────────────────────────────────────
 * Inventaire visuel AVANT / APRÈS migration MkButton
 *
 * Colonne « Aperçu actuel » : reproduction fidèle du style trouvé dans le
 * code source MediaKeeper (background, opacités, halo copiés des CSS).
 *
 * Colonne « Après MkButton » : rendu du composant <MkButton> qui va
 * remplacer la classe, selon la taxonomie validée (5 variantes :
 * primary / danger / ghost / icon / link).
 *
 * Cas hors MkButton (composants custom préservés) :
 *   - Login submit (gradient + shimmer)
 *   - Bande-annonce détail média (gradient blanc)
 *   - Soirée ciné mode "Cinéma" (gold pulsing)
 *   - Bookmark gold Top 20 Emby
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
  name: 'Avant / Après MkButton',
  render: () => ({
    components: { MkButton },
    template: `
      <div>
        <div class="inv-page">

          <h1 style="margin: 0 0 8px; color: #fff;">📋 Inventaire MediaKeeper — Avant / Après MkButton</h1>
          <p style="color: #a8b2c2; margin: 0 0 32px; max-width: 880px;">
            Pour chaque famille visuelle, comparaison côte à côte :<br>
            <strong>Colonne 1</strong> — reproduction fidèle du style ACTUEL (CSS source).<br>
            <strong>Colonne 4</strong> — rendu après migration vers <code>&lt;MkButton&gt;</code> selon la
            taxonomie validée (5 variantes : <code>primary</code>, <code>danger</code>,
            <code>ghost</code>, <code>icon</code>, <code>link</code>).
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
                <tr><td><button class="x-mk-flat-primary">Confirmer</button></td><td class="name">.wn-btn-primary</td><td class="where">Modale "Nouveautés" (admin)</td><td><MkButton variant="primary">Confirmer</MkButton></td></tr>
                <tr><td><button class="x-mk-flat-primary">Enregistrer</button></td><td class="name">.str-save-btn</td><td class="where">Paramètres → Planificateur</td><td><MkButton variant="primary" icon="save">Enregistrer</MkButton></td></tr>
                <tr><td><button class="x-mk-flat-primary">Confirmer</button></td><td class="name">.lfm-btn--primary</td><td class="where">Modale formulaire liste (Portail)</td><td><MkButton variant="primary">Confirmer</MkButton></td></tr>
                <tr><td><button class="x-mk-flat-primary">Inviter</button></td><td class="name">.pt-evd-btn--primary</td><td class="where">Modale détail événement (Soirées)</td><td><MkButton variant="primary">Inviter</MkButton></td></tr>
                <tr><td><button class="x-mk-flat-primary">Créer</button></td><td class="name">.pt-evc-btn--primary</td><td class="where">Modale création événement</td><td><MkButton variant="primary" icon="plus">Créer</MkButton></td></tr>
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
              💡 Migration : <code>variant="primary"</code> — <strong>changement visuel notable</strong>
              (le tinted disparaît au profit du plein).
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
                <tr><td><button class="x-mk-pill-gradient">Renommer</button></td><td class="name">.mr-btn-primary</td><td class="where">Media Manager → Modale Renommer dossier</td><td><MkButton variant="primary" icon="pencil">Renommer</MkButton></td></tr>
                <tr><td><button class="x-mk-pill-gradient">Déplacer</button></td><td class="name">.mv-btn-primary</td><td class="where">Media Manager → Modale Déplacer</td><td><MkButton variant="primary">Déplacer</MkButton></td></tr>
                <tr><td><button class="x-mk-pill-gradient">OK</button></td><td class="name">.mf-btn-primary</td><td class="where">Media Manager → Modale Dossier</td><td><MkButton variant="primary" icon="check">OK</MkButton></td></tr>
              </tbody>
            </table>
          </div>

          <!-- ═══════════════════════════════════════════════════════════ -->
          <div class="inv-section">
            <h2>🟪 Famille D — Gradient violet/indigo</h2>
            <p class="intro">
              <code>linear-gradient(135deg, indigo, purple)</code> + shadow accent. CTA premium.
            </p>
            <div class="reco">
              💡 Migration : login <strong>conservé tel quel</strong> (cas N custom). Les autres
              passent en <code>variant="primary"</code>.
            </div>
            <table class="inv-table">
              <thead>
                <tr><th class="preview">Actuel (fidèle)</th><th class="name">Classe CSS</th><th class="where">Où ça vit</th><th class="preview">Après MkButton</th></tr>
              </thead>
              <tbody>
                <tr><td><button class="x-mk-gradient-login">Se connecter</button></td><td class="name">.login-submit</td><td class="where">Page de connexion (signature préservée)</td><td><button class="x-mk-gradient-login">Se connecter</button><br><span style="color:#a8b2c2;font-size:11px;">(reste hors MkButton)</span></td></tr>
                <tr><td><button class="x-mk-gradient-onboarding">Lancer</button></td><td class="name">.ob-btn-launch</td><td class="where">Onboarding wizard → Étape finale</td><td><MkButton variant="primary" icon-right="chevron-right">Lancer</MkButton></td></tr>
                <tr><td><button class="x-mk-gradient-digest">Voir tout</button></td><td class="name">.ddd-btn-primary</td><td class="where">Portail → Daily digest CTA</td><td><MkButton variant="primary">Voir tout</MkButton></td></tr>
                <tr><td><button class="x-mk-gradient-portal">+ Créer une liste</button></td><td class="name">.arr-create-btn</td><td class="where">Portail → Listes</td><td><MkButton variant="primary" icon="plus">Créer une liste</MkButton></td></tr>
              </tbody>
            </table>
          </div>

          <!-- ═══════════════════════════════════════════════════════════ -->
          <div class="inv-section">
            <h2>⚪ Famille N — Cas particuliers (conservés)</h2>
            <p class="intro">
              Styles uniques préservés en composants custom hors design system.
            </p>
            <div class="reco">💡 Migration : <strong>inchangé</strong>, ces boutons gardent leur signature visuelle.</div>
            <table class="inv-table">
              <thead>
                <tr><th class="preview">Actuel (fidèle)</th><th class="name">Classe CSS</th><th class="where">Où ça vit</th><th class="preview">Après MkButton</th></tr>
              </thead>
              <tbody>
                <tr><td><button class="x-mk-white-gradient">▶ Bande-annonce</button></td><td class="name">.vmd2-btn--primary</td><td class="where">Portail → Fiche détail média</td><td><button class="x-mk-white-gradient">▶ Bande-annonce</button><br><span style="color:#a8b2c2;font-size:11px;">(reste custom)</span></td></tr>
                <tr><td><button class="x-mk-cinema-gold">🎬 Cinéma</button></td><td class="name">.pt-evd-btn--cinema</td><td class="where">Soirées ciné → Mode "Cinéma"</td><td><button class="x-mk-cinema-gold">🎬 Cinéma</button><br><span style="color:#a8b2c2;font-size:11px;">(reste custom)</span></td></tr>
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
              💡 Migration : <code>variant="danger"</code> — <strong>plein rouge plus tranché.</strong>
            </div>
            <table class="inv-table">
              <thead>
                <tr><th class="preview">Actuel (fidèle)</th><th class="name">Classe CSS</th><th class="where">Où ça vit</th><th class="preview">Après MkButton</th></tr>
              </thead>
              <tbody>
                <tr><td><button class="x-mk-tinted-danger">🗑 Supprimer</button></td><td class="name">.mm-btn-danger</td><td class="where">Media Manager → diverses modales</td><td><MkButton variant="danger" icon="trash-2">Supprimer</MkButton></td></tr>
                <tr><td><button class="x-mk-tinted-danger">Supprimer</button></td><td class="name">.mk-confirm-btn-danger</td><td class="where">MkConfirmDialog (transverse)</td><td><MkButton variant="danger">Supprimer</MkButton></td></tr>
                <tr><td><button class="x-mk-tinted-warn">Attention</button></td><td class="name">.mk-confirm-btn-warn</td><td class="where">MkConfirmDialog (variante warn)</td><td><MkButton variant="danger">Attention</MkButton><br><span style="color:#a8b2c2;font-size:11px;">(warn fusionné dans danger)</span></td></tr>
              </tbody>
            </table>
          </div>

          <!-- ═══════════════════════════════════════════════════════════ -->
          <div class="inv-section">
            <h2>🟥 Famille G — Solid danger (rouge plein)</h2>
            <p class="intro">Background rouge plein, texte blanc. Style destructif fort.</p>
            <div class="reco">💡 Migration : <code>variant="danger"</code> — pas de changement visuel.</div>
            <table class="inv-table">
              <thead>
                <tr><th class="preview">Actuel (fidèle)</th><th class="name">Classe CSS</th><th class="where">Où ça vit</th><th class="preview">Après MkButton</th></tr>
              </thead>
              <tbody>
                <tr><td><button class="x-mk-flat-danger">Annuler RSVP</button></td><td class="name">.pt-evd-btn--danger</td><td class="where">Soirées ciné → Modale détail (danger)</td><td><MkButton variant="danger">Annuler RSVP</MkButton></td></tr>
              </tbody>
            </table>
          </div>

          <!-- ═══════════════════════════════════════════════════════════ -->
          <div class="inv-section">
            <h2>🟢 Famille I — Tinted success → devient PRIMARY ou TOAST</h2>
            <p class="intro">
              Background vert translucide + bord vert + texte vert.
              <br><strong>Décision retenue :</strong> pas de <code>variant="success"</code> dédié. Les actions "Valider"
              deviennent <code>primary</code>. L'état "✓ Sauvegardé" devient un toast.
            </p>
            <div class="reco">💡 Migration : <code>variant="primary"</code> pour les boutons, toast pour les états.</div>
            <table class="inv-table">
              <thead>
                <tr><th class="preview">Actuel (fidèle)</th><th class="name">Classe CSS</th><th class="where">Où ça vit</th><th class="preview">Après MkButton</th></tr>
              </thead>
              <tbody>
                <tr><td><button class="x-mk-tinted-success">✓ Valider</button></td><td class="name">.mm-btn-success</td><td class="where">Media Manager → action validation</td><td><MkButton variant="primary" icon="check">Valider</MkButton></td></tr>
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
                <tr><td><button class="x-mk-ghost-neutral">Annuler</button></td><td class="name">.wn-btn-secondary</td><td class="where">Modale Nouveautés</td><td><MkButton variant="ghost">Annuler</MkButton></td></tr>
                <tr><td><button class="x-mk-ghost-neutral">Annuler</button></td><td class="name">.mk-confirm-btn-cancel</td><td class="where">MkConfirmDialog (transverse)</td><td><MkButton variant="ghost">Annuler</MkButton></td></tr>
                <tr><td><button class="x-mk-ghost-neutral">Annuler</button></td><td class="name">.lfm-btn--secondary</td><td class="where">Modale formulaire liste</td><td><MkButton variant="ghost">Annuler</MkButton></td></tr>
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
            <h2>⊕ Famille K-close — X de modales (icon)</h2>
            <p class="intro">
              Bouton X en haut à droite des modales/popups. ~25 instances visuellement identiques.
            </p>
            <div class="reco">💡 Migration : <code>variant="icon" icon="x"</code>.</div>
            <table class="inv-table">
              <thead>
                <tr><th class="preview">Actuel (fidèle)</th><th class="name">Classe CSS</th><th class="where">Où ça vit</th><th class="preview">Après MkButton</th></tr>
              </thead>
              <tbody>
                <tr><td><button class="x-mk-icon-close">✕</button></td><td class="name">.wn-close / .sm-close / .pt-popup-close (×5+)</td><td class="where">Modales transverses (~25)</td><td><MkButton variant="icon" icon="x" ariaLabel="Fermer" /></td></tr>
                <tr><td><button class="x-mk-icon-close">✕</button></td><td class="name">.mf-close / .mv-close / .mr-close</td><td class="where">Media Manager (3 modales)</td><td><MkButton variant="icon" icon="x" ariaLabel="Fermer" /></td></tr>
                <tr><td><button class="x-mk-icon-close">✕</button></td><td class="name">.so-close / .si-close / .sub-prof-close</td><td class="where">Sous-titres / Surprise overlay</td><td><MkButton variant="icon" icon="x" ariaLabel="Fermer" /></td></tr>
              </tbody>
            </table>
          </div>

          <!-- ═══════════════════════════════════════════════════════════ -->
          <div class="inv-section">
            <h2>⚙ Famille K — Icône seule (engrenage, crayon, edit)</h2>
            <p class="intro">Bouton compact 32×32 avec icône lucide. Header de carte, toolbar.</p>
            <div class="reco">💡 Migration : <code>variant="icon" icon="..."</code>.</div>
            <table class="inv-table">
              <thead>
                <tr><th class="preview">Actuel (fidèle)</th><th class="name">Classe CSS</th><th class="where">Où ça vit</th><th class="preview">Après MkButton</th></tr>
              </thead>
              <tbody>
                <tr><td><button class="x-mk-icon-square">⚙</button></td><td class="name">.pt-icon-btn</td><td class="where">Portail (Calendar / News / Featured)</td><td><MkButton variant="icon" icon="settings" ariaLabel="Paramètres" /></td></tr>
                <tr><td><button class="x-mk-icon-square">✎</button></td><td class="name">.ru-icon-btn</td><td class="where">Admin → Demandes utilisateurs</td><td><MkButton variant="icon" icon="pencil" ariaLabel="Modifier" /></td></tr>
                <tr><td><button class="x-mk-icon-square">⋯</button></td><td class="name">.mk-iconbtn</td><td class="where">PosterCard (carte affiche)</td><td><MkButton variant="icon" icon="eye" ariaLabel="Aperçu" /></td></tr>
                <tr><td><button class="x-mk-icon-gold">★</button></td><td class="name">.mk-iconbtn--gold</td><td class="where">PosterCard → Bookmark Top 20 Emby</td><td><button class="x-mk-icon-gold">★</button><br><span style="color:#a8b2c2;font-size:11px;">(reste custom)</span></td></tr>
              </tbody>
            </table>
          </div>

          <!-- ═══════════════════════════════════════════════════════════ -->
          <div class="inv-section">
            <h2>⊝ Famille L — Mini "Retirer" → devient ICON sm</h2>
            <p class="intro">
              Mini bouton circulaire 18×18 pour retirer un élément d'une liste/tag.
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
                <tr><td>Item <button class="x-mk-mini-remove">✕</button></td><td class="name">.ale-item-remove</td><td class="where">Portail → Listes (item)</td><td>Item <MkButton variant="icon" icon="x" size="sm" ariaLabel="Retirer" /></td></tr>
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
            <h2>📊 Synthèse migration</h2>
            <table class="inv-table">
              <thead>
                <tr><th>Famille</th><th>Action</th><th>Cible MkButton</th></tr>
              </thead>
              <tbody>
                <tr><td>A — Solid accent</td><td>identique</td><td><code>primary</code></td></tr>
                <tr><td>B — Tinted accent</td><td>⚠ changement visuel</td><td><code>primary</code></td></tr>
                <tr><td>C — Pill gradient MM</td><td>⚠ perd pill + halo</td><td><code>primary</code></td></tr>
                <tr><td>D — Gradient (sauf login)</td><td>⚠ perd gradient</td><td><code>primary</code></td></tr>
                <tr><td>D — login submit</td><td>conservé</td><td>custom (hors MkButton)</td></tr>
                <tr><td>N — Bande-annonce, Cinéma gold</td><td>conservés</td><td>custom (hors MkButton)</td></tr>
                <tr><td>F — Tinted danger</td><td>⚠ changement visuel</td><td><code>danger</code></td></tr>
                <tr><td>G — Solid danger</td><td>identique</td><td><code>danger</code></td></tr>
                <tr><td>I — Tinted success (action)</td><td>⚠ change couleur</td><td><code>primary</code></td></tr>
                <tr><td>I — Tinted success (état)</td><td>devient toast</td><td>useToast</td></tr>
                <tr><td>H — Ghost outline</td><td>identique</td><td><code>ghost</code></td></tr>
                <tr><td>H-pill — Ghost pill MM</td><td>⚠ perd pill</td><td><code>ghost</code></td></tr>
                <tr><td>K-close — X de modale</td><td>identique</td><td><code>icon</code> + <code>icon="x"</code></td></tr>
                <tr><td>K — Icon-only (engrenage, edit)</td><td>identique</td><td><code>icon</code></td></tr>
                <tr><td>K — Bookmark gold Top 20</td><td>conservé</td><td>custom (hors MkButton)</td></tr>
                <tr><td>L — Mini remove</td><td>⚠ devient carré 28×28</td><td><code>icon size="sm"</code></td></tr>
                <tr><td>J — Skip / lien</td><td>nouveau</td><td><code>link</code></td></tr>
              </tbody>
            </table>
          </div>

        </div>
      </div>
    `,
  }),
}
