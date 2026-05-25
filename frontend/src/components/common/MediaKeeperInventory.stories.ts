import type { Meta, StoryObj } from '@storybook/vue3-vite'

/* ──────────────────────────────────────────────────────────────────────
 * Inventaire visuel des boutons MediaKeeper actuels
 *
 * Reproduit fidèlement les principaux styles trouvés dans le codebase,
 * regroupés par famille visuelle puis par intention sémantique.
 * Pour chaque bouton : aperçu visuel, nom de classe CSS, où il vit dans l'app.
 *
 * Objectif : permettre une décision éclairée sur quelles variantes
 * conserver dans MkButton.
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

/* Styles for this story are loaded globally via .storybook/preview.ts
 * which imports .storybook/inventory.css — keeps the template clean
 * and lets Storybook's HMR pick up CSS edits without rebuilding stories.
 */

export const Inventory: Story = {
  name: 'Inventaire complet',
  render: () => ({
    template: `
      <div>
        <div class="inv-page">

          <h1 style="margin: 0 0 8px; color: #fff;">📋 Inventaire des boutons MediaKeeper</h1>
          <p style="color: #a8b2c2; margin: 0 0 32px; max-width: 780px;">
            Reproduction visuelle des différents styles de boutons trouvés dans le code MediaKeeper,
            regroupés par <strong>intention sémantique</strong> (Enregistrer, Supprimer, etc.).<br>
            L'objectif : voir d'un coup d'œil lesquels se ressemblent visuellement et peuvent fusionner
            sous une seule variante de <code>&lt;MkButton&gt;</code>.
          </p>

          <!-- ═══════════════════════════════════════════════════════════ -->
          <div class="inv-section">
            <h2>🟦 FAMILLE 1 — Actions principales (fond plein violet/indigo)</h2>
            <p class="intro">
              Le bouton le plus utilisé : action forte et attendue. Fond plein, texte blanc, parfois icône.
              <br>Tu as au moins <strong>~30 variantes</strong> visuellement identiques dispersées dans le code.
            </p>
            <div class="reco">
              💡 <strong>Recommandation :</strong> toutes ces variantes fusionnent en <code>&lt;MkButton variant="primary"&gt;</code>
            </div>

            <h3>1.A — "Enregistrer / Sauvegarder"</h3>
            <table class="inv-table">
              <thead>
                <tr><th class="preview">Aperçu</th><th class="name">Nom de classe</th><th class="where">Où ça vit</th></tr>
              </thead>
              <tbody>
                <tr>
                  <td><button class="x-btn-primary-flat">💾 Enregistrer</button></td>
                  <td class="name">.hc-save-btn</td>
                  <td class="where">Santé média → Configuration</td>
                </tr>
                <tr>
                  <td><button class="x-btn-primary-flat">Enregistrer</button></td>
                  <td class="name">.str-save-btn</td>
                  <td class="where">Paramètres → Planificateur</td>
                </tr>
                <tr>
                  <td><button class="x-btn-primary-flat">Enregistrer</button></td>
                  <td class="name">.tc-save-btn</td>
                  <td class="where">Paramètres → Outils</td>
                </tr>
                <tr>
                  <td><button class="x-btn-primary-flat">Enregistrer</button></td>
                  <td class="name">.sub-modal-save</td>
                  <td class="where">Sous-titres (4 modales différentes)</td>
                </tr>
                <tr>
                  <td><button class="x-btn-primary-flat">Enregistrer</button></td>
                  <td class="name">.nf-save-btn</td>
                  <td class="where">Notifications</td>
                </tr>
                <tr>
                  <td><button class="x-btn-primary-flat">Enregistrer</button></td>
                  <td class="name">.params-save-btn</td>
                  <td class="where">Paramètres → Apparence</td>
                </tr>
                <tr>
                  <td><button class="x-btn-primary-flat">Enregistrer</button></td>
                  <td class="name">.pt-gdpr-save</td>
                  <td class="where">Admin Portail → RGPD</td>
                </tr>
                <tr>
                  <td><button class="x-btn-primary-flat">Enregistrer</button></td>
                  <td class="name">.pt-settings-savebar</td>
                  <td class="where">Portail → Paramètres (barre Save sticky)</td>
                </tr>
                <tr>
                  <td><button class="x-btn-primary-flat">Enregistrer</button></td>
                  <td class="name">.backup-retention-save / .backup-dest-save</td>
                  <td class="where">Paramètres → Sauvegardes</td>
                </tr>
              </tbody>
            </table>

            <h3>1.B — "Confirmer / Valider / OK" (modales et formulaires)</h3>
            <table class="inv-table">
              <thead>
                <tr><th class="preview">Aperçu</th><th class="name">Nom de classe</th><th class="where">Où ça vit</th></tr>
              </thead>
              <tbody>
                <tr>
                  <td><button class="x-btn-primary-flat">Confirmer</button></td>
                  <td class="name">.wn-btn-primary</td>
                  <td class="where">Modale "Nouveautés" (admin)</td>
                </tr>
                <tr>
                  <td><button class="x-btn-primary-flat">Confirmer</button></td>
                  <td class="name">.mk-confirm-btn-info / .mk-confirm-btn-warn</td>
                  <td class="where">Composant MkConfirmDialog (transverse)</td>
                </tr>
                <tr>
                  <td><button class="x-btn-primary-flat">Renommer</button></td>
                  <td class="name">.mr-btn-primary</td>
                  <td class="where">Modale renommer dossier (Media Manager)</td>
                </tr>
                <tr>
                  <td><button class="x-btn-primary-flat">Déplacer</button></td>
                  <td class="name">.mv-btn-primary</td>
                  <td class="where">Modale déplacer (Media Manager)</td>
                </tr>
                <tr>
                  <td><button class="x-btn-primary-flat">OK</button></td>
                  <td class="name">.mf-btn-primary</td>
                  <td class="where">Modale dossier (Media Manager)</td>
                </tr>
                <tr>
                  <td><button class="x-btn-primary-flat">Confirmer</button></td>
                  <td class="name">.lfm-btn--primary</td>
                  <td class="where">Modale formulaire liste (Portail)</td>
                </tr>
                <tr>
                  <td><button class="x-btn-primary-flat">Confirmer</button></td>
                  <td class="name">.so-btn--primary</td>
                  <td class="where">Surprise overlay (Portail)</td>
                </tr>
                <tr>
                  <td><button class="x-btn-primary-flat">Confirmer</button></td>
                  <td class="name">.ddd-btn-primary</td>
                  <td class="where">Daily digest (Portail)</td>
                </tr>
                <tr>
                  <td><button class="x-btn-primary-flat">Inviter</button></td>
                  <td class="name">.pt-evd-btn--primary</td>
                  <td class="where">Modale détail événement (Soirées ciné)</td>
                </tr>
                <tr>
                  <td><button class="x-btn-primary-flat">Créer</button></td>
                  <td class="name">.pt-evc-btn--primary</td>
                  <td class="where">Modale création événement</td>
                </tr>
              </tbody>
            </table>

            <h3>1.C — "Créer / Ajouter" (avec icône +)</h3>
            <table class="inv-table">
              <thead>
                <tr><th class="preview">Aperçu</th><th class="name">Nom de classe</th><th class="where">Où ça vit</th></tr>
              </thead>
              <tbody>
                <tr>
                  <td><button class="x-btn-primary-flat">+ Créer une liste</button></td>
                  <td class="name">.arr-create-btn</td>
                  <td class="where">Portail → Listes</td>
                </tr>
                <tr>
                  <td><button class="x-btn-primary-flat">+ Nouveau ticket</button></td>
                  <td class="name">.ptl-create</td>
                  <td class="where">Portail → Tickets</td>
                </tr>
                <tr>
                  <td><button class="x-btn-primary-flat">+ Ajouter</button></td>
                  <td class="name">.nf-add-btn</td>
                  <td class="where">Notifications → Templates</td>
                </tr>
                <tr>
                  <td><button class="x-btn-primary-flat">+ Ajouter dossier</button></td>
                  <td class="name">.ob-add-folder-btn</td>
                  <td class="where">Onboarding → Étape dossiers</td>
                </tr>
                <tr>
                  <td><button class="x-btn-primary-flat">+ Créer</button></td>
                  <td class="name">.backup-btn-create</td>
                  <td class="where">Paramètres → Sauvegardes</td>
                </tr>
                <tr>
                  <td><button class="x-btn-primary-flat">+ Ajouter</button></td>
                  <td class="name">.excl-add-btn</td>
                  <td class="where">Stats → Outils (exclusions)</td>
                </tr>
              </tbody>
            </table>

            <h3>1.D — "Importer / Lancer / Soumettre" (action immédiate)</h3>
            <table class="inv-table">
              <thead>
                <tr><th class="preview">Aperçu</th><th class="name">Nom de classe</th><th class="where">Où ça vit</th></tr>
              </thead>
              <tbody>
                <tr>
                  <td><button class="x-btn-primary-flat">↑ Choisir un fichier</button></td>
                  <td class="name">(import-jellystats)</td>
                  <td class="where">Stats → Outils → Import Jellystats</td>
                </tr>
                <tr>
                  <td><button class="x-btn-primary-flat">⟳ Lancer</button></td>
                  <td class="name">(migration-mediatheques)</td>
                  <td class="where">Stats → Outils → Migration médiathèques</td>
                </tr>
                <tr>
                  <td><button class="x-btn-primary-flat">Se connecter</button></td>
                  <td class="name">.login-submit</td>
                  <td class="where">Page de connexion</td>
                </tr>
                <tr>
                  <td><button class="x-btn-primary-flat">⟳ Scanner</button></td>
                  <td class="name">.wls-scan-btn</td>
                  <td class="where">Vigilance média → Séries</td>
                </tr>
                <tr>
                  <td><button class="x-btn-primary-flat">⟳ Scanner</button></td>
                  <td class="name">.wl-scan-btn</td>
                  <td class="where">Vigilance média (vue principale)</td>
                </tr>
                <tr>
                  <td><button class="x-btn-primary-gradient">⟳ Suivant</button></td>
                  <td class="name">.ob-btn-launch</td>
                  <td class="where">Onboarding → Bouton "Lancer" (gradient unique violet)</td>
                </tr>
              </tbody>
            </table>

            <h3>1.E — Cas particuliers à arbitrer</h3>
            <table class="inv-table">
              <thead>
                <tr><th class="preview">Aperçu</th><th class="name">Nom de classe</th><th class="where">Où ça vit</th></tr>
              </thead>
              <tbody>
                <tr>
                  <td><button class="x-btn-primary-white">Bande-annonce</button></td>
                  <td class="name">.vmd2-btn--primary</td>
                  <td class="where">Portail → Fiche détail média (UNIQUE : gradient blanc)</td>
                </tr>
                <tr>
                  <td><button class="x-btn-primary-gradient">Lancer</button></td>
                  <td class="name">.ob-btn-launch</td>
                  <td class="where">Onboarding (UNIQUE : gradient indigo→violet)</td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- ═══════════════════════════════════════════════════════════ -->
          <div class="inv-section">
            <h2>🟥 FAMILLE 2 — Actions destructives (fond plein rouge)</h2>
            <p class="intro">
              Suppression, retrait, bannissement. Fond rouge plein, texte blanc.
              <br>Tu as au moins <strong>~15 variantes</strong> visuellement identiques.
            </p>
            <div class="reco">
              💡 <strong>Recommandation :</strong> toutes ces variantes fusionnent en <code>&lt;MkButton variant="danger"&gt;</code>
            </div>

            <table class="inv-table">
              <thead>
                <tr><th class="preview">Aperçu</th><th class="name">Nom de classe</th><th class="where">Où ça vit</th></tr>
              </thead>
              <tbody>
                <tr>
                  <td><button class="x-btn-danger-flat">🗑 Supprimer</button></td>
                  <td class="name">.mm-btn-danger</td>
                  <td class="where">Media Manager → diverses modales</td>
                </tr>
                <tr>
                  <td><button class="x-btn-danger-flat">🗑 Supprimer</button></td>
                  <td class="name">.doub-delete-btn</td>
                  <td class="where">Doublons</td>
                </tr>
                <tr>
                  <td><button class="x-btn-danger-flat">Supprimer</button></td>
                  <td class="name">.sec-btn-danger</td>
                  <td class="where">Paramètres → Sécurité</td>
                </tr>
                <tr>
                  <td><button class="x-btn-danger-flat">🗑 Purger</button></td>
                  <td class="name">.tool-btn-danger</td>
                  <td class="where">Stats → Outils → Purger import</td>
                </tr>
                <tr>
                  <td><button class="x-btn-danger-flat">Supprimer</button></td>
                  <td class="name">.params-danger-btn</td>
                  <td class="where">Paramètres → Réinitialisation</td>
                </tr>
                <tr>
                  <td><button class="x-btn-danger-flat">Bannir</button></td>
                  <td class="name">.ru-btn--danger</td>
                  <td class="where">Admin Portail → Users</td>
                </tr>
                <tr>
                  <td><button class="x-btn-danger-flat">Supprimer</button></td>
                  <td class="name">.nf-btn-danger</td>
                  <td class="where">Notifications</td>
                </tr>
                <tr>
                  <td><button class="x-btn-danger-flat">Annuler RSVP</button></td>
                  <td class="name">.pt-evd-btn--danger</td>
                  <td class="where">Modale détail événement (Soirées)</td>
                </tr>
                <tr>
                  <td><button class="x-btn-danger-flat">Supprimer mon compte</button></td>
                  <td class="name">.pt-settings-btn--danger</td>
                  <td class="where">Portail → Paramètres → Compte</td>
                </tr>
                <tr>
                  <td><button class="x-btn-danger-flat">Confirmer suppression</button></td>
                  <td class="name">.mk-confirm-btn-danger</td>
                  <td class="where">Composant MkConfirmDialog (transverse)</td>
                </tr>
                <tr>
                  <td><button class="x-btn-danger-flat">Confirmer</button></td>
                  <td class="name">.pt-dcm-btn--danger</td>
                  <td class="where">Modale "Supprimer mon compte"</td>
                </tr>
                <tr>
                  <td><button class="x-btn-danger-flat">Effacer données</button></td>
                  <td class="name">.pt-privacy-delete</td>
                  <td class="where">Portail → Paramètres → Vie privée</td>
                </tr>
                <tr>
                  <td><button class="x-btn-danger-flat">Supprimer</button></td>
                  <td class="name">.adm-btn--danger</td>
                  <td class="where">Admin Portail → Listes</td>
                </tr>
              </tbody>
            </table>

            <h3>2.B — "Retirer" (suppression douce, souvent en croix petite)</h3>
            <table class="inv-table">
              <thead>
                <tr><th class="preview">Aperçu</th><th class="name">Nom de classe</th><th class="where">Où ça vit</th></tr>
              </thead>
              <tbody>
                <tr>
                  <td><button class="x-btn-remove-x">✕</button> <span style="color: #a8b2c2;">("Marvel" × Retirer)</span></td>
                  <td class="name">.ru-tag-remove</td>
                  <td class="where">Admin Portail → Users → Tags</td>
                </tr>
                <tr>
                  <td><button class="x-btn-remove-x">✕</button></td>
                  <td class="name">.ob-folder-remove</td>
                  <td class="where">Onboarding → Étape dossiers</td>
                </tr>
                <tr>
                  <td><button class="x-btn-remove-x">✕</button></td>
                  <td class="name">.ale-item-remove</td>
                  <td class="where">Portail → Listes (item d'une liste)</td>
                </tr>
                <tr>
                  <td><button class="x-btn-remove-x">✕</button></td>
                  <td class="name">.ale-contrib-remove</td>
                  <td class="where">Portail → Listes (contributeurs)</td>
                </tr>
                <tr>
                  <td><button class="x-btn-remove-x">✕</button></td>
                  <td class="name">.mm-rt-remove</td>
                  <td class="where">Media Manager → Release tags</td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- ═══════════════════════════════════════════════════════════ -->
          <div class="inv-section">
            <h2>⬜ FAMILLE 3 — Actions secondaires / Annuler (transparent + contour)</h2>
            <p class="intro">
              Action alternative discrète. Fond transparent ou très subtil, contour gris, texte blanc/gris.
              <br>Tu as au moins <strong>~15 variantes</strong> avec 3 sous-styles visuels.
            </p>
            <div class="reco">
              💡 <strong>Recommandation :</strong> tout fusionne en <code>&lt;MkButton variant="ghost"&gt;</code>
            </div>

            <h3>3.A — "Annuler" et "Précédent"</h3>
            <table class="inv-table">
              <thead>
                <tr><th class="preview">Aperçu</th><th class="name">Nom de classe</th><th class="where">Où ça vit</th></tr>
              </thead>
              <tbody>
                <tr>
                  <td><button class="x-btn-secondary-grey">Annuler</button></td>
                  <td class="name">.wn-btn-secondary</td>
                  <td class="where">Modale "Nouveautés" (admin)</td>
                </tr>
                <tr>
                  <td><button class="x-btn-secondary-grey">Annuler</button></td>
                  <td class="name">.mk-confirm-btn-cancel</td>
                  <td class="where">Composant MkConfirmDialog (transverse)</td>
                </tr>
                <tr>
                  <td><button class="x-btn-secondary-grey">Annuler</button></td>
                  <td class="name">.sub-modal-cancel</td>
                  <td class="where">Sous-titres (4 modales)</td>
                </tr>
                <tr>
                  <td><button class="x-btn-secondary-grey">Annuler</button></td>
                  <td class="name">.sub-batch-cancel-btn</td>
                  <td class="where">Sous-titres → Progress batch</td>
                </tr>
                <tr>
                  <td><button class="x-btn-secondary-grey">Annuler</button></td>
                  <td class="name">.pt-dpb-cancel</td>
                  <td class="where">Portail → Bannière suppression compte</td>
                </tr>
                <tr>
                  <td><button class="x-btn-secondary-grey">Annuler</button></td>
                  <td class="name">.pt-gdpr-pending-cancel</td>
                  <td class="where">Admin → RGPD</td>
                </tr>
                <tr>
                  <td><button class="x-btn-secondary-grey">← Retour</button></td>
                  <td class="name">.ob-btn-ghost</td>
                  <td class="where">Onboarding wizard → Précédent</td>
                </tr>
                <tr>
                  <td><button class="x-btn-secondary-grey">← Retour</button></td>
                  <td class="name">.ptd-back</td>
                  <td class="where">Portail → Ticket détail</td>
                </tr>
                <tr>
                  <td><button class="x-btn-secondary-grey">← Retour</button></td>
                  <td class="name">.pt-search-back / .pt-help-article-back</td>
                  <td class="where">Portail → Recherche / Aide</td>
                </tr>
              </tbody>
            </table>

            <h3>3.B — Variantes avec fond légèrement teinté (sur cartes)</h3>
            <table class="inv-table">
              <thead>
                <tr><th class="preview">Aperçu</th><th class="name">Nom de classe</th><th class="where">Où ça vit</th></tr>
              </thead>
              <tbody>
                <tr>
                  <td><button class="x-btn-secondary-bg">Annuler</button></td>
                  <td class="name">.pt-btn--secondary</td>
                  <td class="where">Portail → Soirées ciné / Wrapped / Profile-edit</td>
                </tr>
                <tr>
                  <td><button class="x-btn-secondary-bg">Annuler</button></td>
                  <td class="name">.doub-btn-secondary</td>
                  <td class="where">Doublons → Modales</td>
                </tr>
                <tr>
                  <td><button class="x-btn-secondary-bg">Annuler</button></td>
                  <td class="name">.mm-btn-secondary</td>
                  <td class="where">Media Manager (transverse)</td>
                </tr>
                <tr>
                  <td><button class="x-btn-secondary-pill">Auto-détecter</button></td>
                  <td class="name">.mf-btn-secondary</td>
                  <td class="where">Modale dossier (variante PILL arrondie)</td>
                </tr>
                <tr>
                  <td><button class="x-btn-secondary-bg">Annuler</button></td>
                  <td class="name">.lfm-btn--secondary</td>
                  <td class="where">Modale formulaire liste</td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- ═══════════════════════════════════════════════════════════ -->
          <div class="inv-section">
            <h2>⊕ FAMILLE 4 — Boutons "Fermer" (X dans modales/popups)</h2>
            <p class="intro">
              Le bouton X en haut à droite d'une modale, popup, drawer. Carré ou rond, presque toujours icône seule.
              <br>Tu as au moins <strong>~30 variantes</strong> de ce X selon les modales !
            </p>
            <div class="reco">
              💡 <strong>Recommandation :</strong> tout fusionne en <code>&lt;MkButton variant="icon" icon="x"&gt;</code>
            </div>

            <h3>4.A — Style carré contour subtle (le plus courant)</h3>
            <table class="inv-table">
              <thead>
                <tr><th class="preview">Aperçu</th><th class="name">Nom de classe</th><th class="where">Où ça vit</th></tr>
              </thead>
              <tbody>
                <tr><td><button class="x-btn-close-x">✕</button></td><td class="name">.wn-close</td><td class="where">Modale Nouveautés</td></tr>
                <tr><td><button class="x-btn-close-x">✕</button></td><td class="name">.sm-close</td><td class="where">Modale recherche globale</td></tr>
                <tr><td><button class="x-btn-close-x">✕</button></td><td class="name">.mf-close / .mv-close / .mr-close</td><td class="where">Media Manager (3 modales)</td></tr>
                <tr><td><button class="x-btn-close-x">✕</button></td><td class="name">.mm-close-btn</td><td class="where">Media Manager (2 ctx menus)</td></tr>
                <tr><td><button class="x-btn-close-x">✕</button></td><td class="name">.wlsu-detail-close / .wlsu-add-close</td><td class="where">Watchlist → Suivi (2 modales)</td></tr>
                <tr><td><button class="x-btn-close-x">✕</button></td><td class="name">.wlcal-popup-close / .wlcal-modal-close</td><td class="where">Watchlist → Calendrier (2)</td></tr>
                <tr><td><button class="x-btn-close-x">✕</button></td><td class="name">.so-close / .si-close</td><td class="where">Sous-titres overlays</td></tr>
                <tr><td><button class="x-btn-close-x">✕</button></td><td class="name">.sub-prof-close / .sub-matrix-close / .sub-audit-close</td><td class="where">Sous-titres (3 modales)</td></tr>
                <tr><td><button class="x-btn-close-x">✕</button></td><td class="name">.pt-popup-close</td><td class="where">Portail (5+ popups différentes)</td></tr>
                <tr><td><button class="x-btn-close-x">✕</button></td><td class="name">.pt-rmodal-close</td><td class="where">Portail → Modale demande</td></tr>
                <tr><td><button class="x-btn-close-x">✕</button></td><td class="name">.pt-help-close / .pt-tlb-close</td><td class="where">Portail → Aide / Trailer</td></tr>
                <tr><td><button class="x-btn-close-x">✕</button></td><td class="name">.ddd-close</td><td class="where">Portail → Daily digest</td></tr>
                <tr><td><button class="x-btn-close-x">✕</button></td><td class="name">.ta-close / .gc-trophy-modal-close</td><td class="where">Portail → Trophées</td></tr>
                <tr><td><button class="x-btn-close-x">✕</button></td><td class="name">.dwn-close</td><td class="where">Portail → Modale nouveautés</td></tr>
                <tr><td><button class="x-btn-close-x">✕</button></td><td class="name">.atl-close</td><td class="where">Portail → Ajout liste overlay</td></tr>
                <tr><td><button class="x-btn-close-x">✕</button></td><td class="name">.lfm-close</td><td class="where">Portail → Modale liste form</td></tr>
                <tr><td><button class="x-btn-close-x">✕</button></td><td class="name">.rrm-close</td><td class="where">Portail Admin → Rejeter raison</td></tr>
                <tr><td><button class="x-btn-close-x">✕</button></td><td class="name">.ru-drawer-close</td><td class="where">Admin → Drawer user</td></tr>
                <tr><td><button class="x-btn-close-x">✕</button></td><td class="name">.np-close</td><td class="where">Dashboard → Now Playing fullscreen</td></tr>
                <tr><td><button class="x-btn-close-x">✕</button></td><td class="name">.up-close</td><td class="where">Stats → Popover utilisateur / Modale fusion</td></tr>
              </tbody>
            </table>

            <h3>4.B — Variante ronde (cercle)</h3>
            <table class="inv-table">
              <thead>
                <tr><th class="preview">Aperçu</th><th class="name">Nom de classe</th><th class="where">Où ça vit</th></tr>
              </thead>
              <tbody>
                <tr><td><button class="x-btn-close-circle">✕</button></td><td class="name">.mm-btn-sm--close</td><td class="where">Media Manager → Petite croix</td></tr>
              </tbody>
            </table>
          </div>

          <!-- ═══════════════════════════════════════════════════════════ -->
          <div class="inv-section">
            <h2>⚙ FAMILLE 5 — Boutons icône seule (carré ou rond)</h2>
            <p class="intro">
              Bouton compact avec une icône (engrenage, crayon, lecture, etc.), pas de texte.
              Utilisé dans les barres d'outils, headers de carte, listes.
            </p>
            <div class="reco">
              💡 <strong>Recommandation :</strong> <code>&lt;MkButton variant="icon" icon="..."&gt;</code>
            </div>

            <table class="inv-table">
              <thead>
                <tr><th class="preview">Aperçu</th><th class="name">Nom de classe</th><th class="where">Où ça vit</th></tr>
              </thead>
              <tbody>
                <tr>
                  <td><button class="x-btn-icon-square">⚙</button></td>
                  <td class="name">.pt-icon-btn</td>
                  <td class="where">Portail (4 endroits : Calendar / XpEvents / News / Featured)</td>
                </tr>
                <tr>
                  <td><button class="x-btn-icon-square">✎</button></td>
                  <td class="name">.ru-icon-btn</td>
                  <td class="where">Admin → Demandes utilisateurs</td>
                </tr>
                <tr>
                  <td><button class="x-btn-icon-square">⋯</button></td>
                  <td class="name">.mk-iconbtn</td>
                  <td class="where">PosterCard (carte affiche)</td>
                </tr>
                <tr>
                  <td><button class="x-btn-icon-gold">★</button></td>
                  <td class="name">.mk-iconbtn--gold</td>
                  <td class="where">PosterCard → Bookmark gold</td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- ═══════════════════════════════════════════════════════════ -->
          <div class="inv-section">
            <h2>🔗 FAMILLE 6 — Liens / Skip (texte seul, sans rien autour)</h2>
            <p class="intro">
              Action très discrète, juste du texte cliquable. Pas de fond, pas de contour.
              <br>Rare dans MediaKeeper (~3 cas) mais présent dans le wizard et quelques modales.
            </p>
            <div class="reco">
              💡 <strong>Recommandation :</strong> ajouter une variante <code>&lt;MkButton variant="link"&gt;</code> ou utiliser un <code>&lt;a&gt;</code> stylisé
            </div>

            <table class="inv-table">
              <thead>
                <tr><th class="preview">Aperçu</th><th class="name">Nom de classe</th><th class="where">Où ça vit</th></tr>
              </thead>
              <tbody>
                <tr>
                  <td><button class="x-btn-skip">Passer</button></td>
                  <td class="name">.ob-btn-skip</td>
                  <td class="where">Onboarding wizard → Skip étape</td>
                </tr>
                <tr>
                  <td><button class="x-btn-skip">Plus tard</button></td>
                  <td class="name">.mk-skip-link</td>
                  <td class="where">Lien d'accessibilité (a11y)</td>
                </tr>
                <tr>
                  <td><button class="x-btn-link">Voir tout →</button></td>
                  <td class="name">(divers carousels/sections)</td>
                  <td class="where">Dashboard, portail (liens "Voir plus")</td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- ═══════════════════════════════════════════════════════════ -->
          <div class="inv-section" style="border-top: 1px solid rgb(255,255,255,0.1); padding-top: 32px;">
            <h2>📊 Synthèse</h2>
            <table class="inv-table">
              <thead>
                <tr>
                  <th>Famille</th>
                  <th style="text-align: center;">Nombre de versions actuelles</th>
                  <th>Variante MkButton cible</th>
                </tr>
              </thead>
              <tbody>
                <tr><td>1 — Action principale (plein violet)</td><td style="text-align: center;"><strong>~30</strong></td><td><code>variant="primary"</code></td></tr>
                <tr><td>2 — Destructive (plein rouge)</td><td style="text-align: center;"><strong>~15</strong></td><td><code>variant="danger"</code></td></tr>
                <tr><td>3 — Annuler / Précédent (transparent contour)</td><td style="text-align: center;"><strong>~15</strong></td><td><code>variant="ghost"</code></td></tr>
                <tr><td>4 — Fermer (X de modale)</td><td style="text-align: center;"><strong>~30</strong></td><td><code>variant="icon" icon="x"</code></td></tr>
                <tr><td>5 — Icône seule (engrenage, etc.)</td><td style="text-align: center;"><strong>~10</strong></td><td><code>variant="icon"</code></td></tr>
                <tr><td>6 — Lien / Skip (texte seul)</td><td style="text-align: center;"><strong>~3</strong></td><td><code>variant="link"</code> (à ajouter)</td></tr>
                <tr style="background: rgb(92, 87, 146, 0.15); font-weight: 600;">
                  <td>TOTAL</td>
                  <td style="text-align: center;">~100 boutons disséminés</td>
                  <td>fusionnent en <strong>5 variantes</strong></td>
                </tr>
              </tbody>
            </table>

            <h3 style="margin-top: 32px;">⚠ Cas particuliers à arbitrer</h3>
            <ul style="color: #dde2eb; line-height: 1.8;">
              <li><code>.vmd2-btn--primary</code> (Portail → Fiche détail) — <strong>gradient blanc unique</strong>. À garder distinct ou aligner sur primary violet ?</li>
              <li><code>.ob-btn-launch</code> (Onboarding → Lancer) — <strong>gradient indigo→violet unique</strong>. À garder distinct ?</li>
              <li>Variantes "Retirer" (croix rouge ronde mini) — c'est en réalité un <code>variant="icon"</code> avec couleur danger. Pas besoin de variante dédiée.</li>
            </ul>
          </div>

        </div>
      </div>
    `,
  }),
}
