import type { Meta, StoryObj } from '@storybook/vue3-vite'

/* ──────────────────────────────────────────────────────────────────────
 * Inventaire visuel des boutons MediaKeeper actuels
 *
 * Regroupé par FAMILLE VISUELLE RÉELLE (non plus par intention sémantique)
 * après lecture des CSS sources. Chaque preview reproduit fidèlement le
 * style trouvé dans le code (background, bordure, shadow, gradient, halo,
 * opacités exactes copiées des fichiers source).
 *
 * Découverte clé : la plupart des boutons "Enregistrer" ne sont PAS pleins
 * violet, mais TINTED (fond accent translucide). MediaKeeper a en réalité
 * ~14 styles visuels distincts, pas 5.
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
  name: 'Inventaire complet (styles visuels réels)',
  render: () => ({
    template: `
      <div>
        <div class="inv-page">

          <h1 style="margin: 0 0 8px; color: #fff;">📋 Inventaire des boutons MediaKeeper</h1>
          <p style="color: #a8b2c2; margin: 0 0 32px; max-width: 880px;">
            Reproduction <strong>fidèle</strong> des styles visuels trouvés dans le code source MediaKeeper,
            regroupés par <strong>famille visuelle réelle</strong> (et non par intention sémantique).<br>
            Chaque preview reproduit l'apparence exacte de la classe citée — backgrounds, opacités, halos copiés
            des fichiers CSS sources.
          </p>

          <!-- ═══════════════════════════════════════════════════════════ -->
          <div class="inv-section">
            <h2>🟦 Famille A — Solid accent (plein violet/indigo)</h2>
            <p class="intro">
              Background plein <code>var(--accent-600)</code> ou <code>--accent-700</code>, texte blanc, pas de bord.
              Le style "primary" tel qu'on l'imagine généralement.
            </p>
            <div class="reco">
              💡 Migration cible : <code>&lt;MkButton variant="primary"&gt;</code>
            </div>
            <table class="inv-table">
              <thead>
                <tr><th class="preview">Aperçu (fidèle)</th><th class="name">Classe CSS</th><th class="where">Où ça vit</th></tr>
              </thead>
              <tbody>
                <tr><td><button class="x-mk-flat-primary">Confirmer</button></td><td class="name">.wn-btn-primary</td><td class="where">Modale "Nouveautés" (admin)</td></tr>
                <tr><td><button class="x-mk-flat-primary">Enregistrer</button></td><td class="name">.str-save-btn</td><td class="where">Paramètres → Planificateur</td></tr>
                <tr><td><button class="x-mk-flat-primary">Confirmer</button></td><td class="name">.lfm-btn--primary</td><td class="where">Modale formulaire liste (Portail)</td></tr>
                <tr><td><button class="x-mk-flat-primary">Inviter</button></td><td class="name">.pt-evd-btn--primary</td><td class="where">Modale détail événement (Soirées)</td></tr>
                <tr><td><button class="x-mk-flat-primary">Créer</button></td><td class="name">.pt-evc-btn--primary</td><td class="where">Modale création événement</td></tr>
                <tr><td><button class="x-mk-flat-primary">Enregistrer</button></td><td class="name">.nf-save-btn</td><td class="where">Notifications → Save bar</td></tr>
              </tbody>
            </table>
          </div>

          <!-- ═══════════════════════════════════════════════════════════ -->
          <div class="inv-section">
            <h2>💜 Famille B — Tinted accent (fond translucide + bord + texte clair)</h2>
            <p class="intro">
              Background <code>rgb(accent, 0.15-0.18)</code>, bord <code>rgb(accent, 0.25-0.3)</code>, texte
              <code>--accent-400</code> ou <code>--accent-300</code>. Style "soft" très utilisé en admin.
              <br><strong>⚠ C'est ce style que beaucoup de tes boutons "Enregistrer" utilisent actuellement</strong>
              (Santé média, Notifications…) — pas le plein violet de la famille A.
            </p>
            <div class="reco">
              💡 Migration cible : à arbitrer. Soit fusionner en <code>variant="primary"</code> (plein)
              soit créer un <code>variant="primary-soft"</code> dédié. <strong>Tu as choisi : tout en plein</strong> —
              ces boutons changeront d'apparence à la migration.
            </div>
            <table class="inv-table">
              <thead>
                <tr><th class="preview">Aperçu (fidèle)</th><th class="name">Classe CSS</th><th class="where">Où ça vit</th></tr>
              </thead>
              <tbody>
                <tr><td><button class="x-mk-tinted-primary">💾 Enregistrer</button></td><td class="name">.hc-save-btn</td><td class="where">Santé média → Configuration</td></tr>
                <tr><td><button class="x-mk-tinted-primary">▶ Lancer</button></td><td class="name">.str-run-btn</td><td class="where">Paramètres → Planificateur (Run)</td></tr>
                <tr><td><button class="x-mk-tinted-primary">+ Ajouter</button></td><td class="name">.nf-add-btn</td><td class="where">Notifications → Templates</td></tr>
                <tr><td><button class="x-mk-tinted-primary">OK</button></td><td class="name">.mk-confirm-btn-info</td><td class="where">MkConfirmDialog (info/transverse)</td></tr>
              </tbody>
            </table>
          </div>

          <!-- ═══════════════════════════════════════════════════════════ -->
          <div class="inv-section">
            <h2>🟣 Famille C — Pill gradient (Media Manager modales)</h2>
            <p class="intro">
              Forme pill (<code>border-radius: 999px</code>), gradient <code>--gradient-pill-active</code>,
              bord accent + halo. Style signature des modales Media Manager (Renommer, Déplacer, Dossier).
            </p>
            <div class="reco">
              💡 Migration cible : <code>&lt;MkButton variant="primary"&gt;</code> (perd la forme pill et le halo).
              <br><strong>⚠ Changement visuel important sur Media Manager.</strong>
            </div>
            <table class="inv-table">
              <thead>
                <tr><th class="preview">Aperçu (fidèle)</th><th class="name">Classe CSS</th><th class="where">Où ça vit</th></tr>
              </thead>
              <tbody>
                <tr><td><button class="x-mk-pill-gradient">Renommer</button></td><td class="name">.mr-btn-primary</td><td class="where">Media Manager → Modale Renommer dossier</td></tr>
                <tr><td><button class="x-mk-pill-gradient">Déplacer</button></td><td class="name">.mv-btn-primary</td><td class="where">Media Manager → Modale Déplacer</td></tr>
                <tr><td><button class="x-mk-pill-gradient">OK</button></td><td class="name">.mf-btn-primary</td><td class="where">Media Manager → Modale Dossier</td></tr>
              </tbody>
            </table>
          </div>

          <!-- ═══════════════════════════════════════════════════════════ -->
          <div class="inv-section">
            <h2>🟪 Famille D — Gradient violet/indigo (CTA premium)</h2>
            <p class="intro">
              <code>linear-gradient(135deg, indigo, purple)</code> + shadow accent.
              Réservé aux écrans d'accueil/CTA forts (login, onboarding, daily digest).
            </p>
            <div class="reco">
              💡 Migration cible : <code>&lt;MkButton variant="primary"&gt;</code> perd les gradients distinctifs.
              <br><strong>⚠ Page de login et onboarding perdent leur signature visuelle</strong>
              (shimmer login, halo onboarding).
            </div>
            <table class="inv-table">
              <thead>
                <tr><th class="preview">Aperçu (fidèle)</th><th class="name">Classe CSS</th><th class="where">Où ça vit</th></tr>
              </thead>
              <tbody>
                <tr><td><button class="x-mk-gradient-login">Se connecter</button></td><td class="name">.login-submit</td><td class="where">Page de connexion (+ effet shimmer)</td></tr>
                <tr><td><button class="x-mk-gradient-onboarding">Lancer</button></td><td class="name">.ob-btn-launch</td><td class="where">Onboarding wizard → Étape finale</td></tr>
                <tr><td><button class="x-mk-gradient-digest">Voir tout</button></td><td class="name">.ddd-btn-primary</td><td class="where">Portail → Daily digest CTA</td></tr>
                <tr><td><button class="x-mk-gradient-portal">+ Créer une liste</button></td><td class="name">.arr-create-btn</td><td class="where">Portail → Listes</td></tr>
              </tbody>
            </table>
          </div>

          <!-- ═══════════════════════════════════════════════════════════ -->
          <div class="inv-section">
            <h2>⚪ Famille N — Cas particuliers uniques</h2>
            <p class="intro">
              Styles qui n'ont qu'un seul usage dans tout le code et ne suivent aucune autre famille.
            </p>
            <div class="reco">
              💡 Migration cible : décision au cas par cas. Soit fusionner en <code>variant="primary"</code>
              (perte du look unique), soit garder en exception <code>variant="custom"</code>.
            </div>
            <table class="inv-table">
              <thead>
                <tr><th class="preview">Aperçu (fidèle)</th><th class="name">Classe CSS</th><th class="where">Où ça vit</th></tr>
              </thead>
              <tbody>
                <tr><td><button class="x-mk-white-gradient">▶ Bande-annonce</button></td><td class="name">.vmd2-btn--primary</td><td class="where">Portail → Fiche détail média (gradient BLANC unique)</td></tr>
                <tr><td><button class="x-mk-cinema-gold">🎬 Cinéma</button></td><td class="name">.pt-evd-btn--cinema</td><td class="where">Soirées ciné → Mode "Cinéma" (gold + pulse)</td></tr>
              </tbody>
            </table>
          </div>

          <!-- ═══════════════════════════════════════════════════════════ -->
          <div class="inv-section">
            <h2>🟥 Famille F — Tinted danger (translucide rouge)</h2>
            <p class="intro">
              Background <code>rgb(error, 0.15)</code>, bord rouge translucide, texte rouge clair.
              <br><strong>⚠ Style le plus utilisé pour "Supprimer" en admin</strong>, contrairement à ce qu'on imagine.
            </p>
            <div class="reco">
              💡 Migration cible : <code>&lt;MkButton variant="danger"&gt;</code> (plein rouge).
              <br><strong>⚠ Tous les boutons Media Manager / MkConfirmDialog deviendront plus visuellement agressifs.</strong>
            </div>
            <table class="inv-table">
              <thead>
                <tr><th class="preview">Aperçu (fidèle)</th><th class="name">Classe CSS</th><th class="where">Où ça vit</th></tr>
              </thead>
              <tbody>
                <tr><td><button class="x-mk-tinted-danger">🗑 Supprimer</button></td><td class="name">.mm-btn-danger</td><td class="where">Media Manager → diverses modales</td></tr>
                <tr><td><button class="x-mk-tinted-danger">Supprimer</button></td><td class="name">.mk-confirm-btn-danger</td><td class="where">MkConfirmDialog (transverse)</td></tr>
                <tr><td><button class="x-mk-tinted-warn">Attention</button></td><td class="name">.mk-confirm-btn-warn</td><td class="where">MkConfirmDialog (variante warn jaune)</td></tr>
              </tbody>
            </table>
          </div>

          <!-- ═══════════════════════════════════════════════════════════ -->
          <div class="inv-section">
            <h2>🟥 Famille G — Solid danger (rouge plein)</h2>
            <p class="intro">
              Background rouge plein (<code>#b91c1c</code>), texte blanc. Style "destructif fort".
            </p>
            <div class="reco">
              💡 Migration cible : <code>&lt;MkButton variant="danger"&gt;</code>.
            </div>
            <table class="inv-table">
              <thead>
                <tr><th class="preview">Aperçu (fidèle)</th><th class="name">Classe CSS</th><th class="where">Où ça vit</th></tr>
              </thead>
              <tbody>
                <tr><td><button class="x-mk-flat-danger">Annuler RSVP</button></td><td class="name">.pt-evd-btn--danger</td><td class="where">Soirées ciné → Modale détail (danger)</td></tr>
              </tbody>
            </table>
          </div>

          <!-- ═══════════════════════════════════════════════════════════ -->
          <div class="inv-section">
            <h2>🟢 Famille I — Tinted success (vert translucide)</h2>
            <p class="intro">
              Background <code>rgb(success, 0.12)</code>, bord vert translucide, texte vert.
              Utilisé pour les états "validé/réussi" et confirmations positives.
            </p>
            <div class="reco">
              💡 Cas non couvert par les 5 variantes MkButton actuelles. À discuter : variant="success" ?
              <br>Présent uniquement dans Media Manager actuellement.
            </div>
            <table class="inv-table">
              <thead>
                <tr><th class="preview">Aperçu (fidèle)</th><th class="name">Classe CSS</th><th class="where">Où ça vit</th></tr>
              </thead>
              <tbody>
                <tr><td><button class="x-mk-tinted-success">✓ Valider</button></td><td class="name">.mm-btn-success</td><td class="where">Media Manager → Boutons validation</td></tr>
                <tr><td><button class="x-mk-tinted-success">✓ Sauvegardé</button></td><td class="name">.mm-btn-saved</td><td class="where">Media Manager → État sauvegardé (transitoire)</td></tr>
              </tbody>
            </table>
          </div>

          <!-- ═══════════════════════════════════════════════════════════ -->
          <div class="inv-section">
            <h2>⬜ Famille H — Ghost outline neutre</h2>
            <p class="intro">
              Background transparent, bord gris translucide, texte gris/blanc.
              Le style "Annuler" et "Précédent" standard.
            </p>
            <div class="reco">
              💡 Migration cible : <code>&lt;MkButton variant="ghost"&gt;</code>.
            </div>
            <table class="inv-table">
              <thead>
                <tr><th class="preview">Aperçu (fidèle)</th><th class="name">Classe CSS</th><th class="where">Où ça vit</th></tr>
              </thead>
              <tbody>
                <tr><td><button class="x-mk-ghost-neutral">Annuler</button></td><td class="name">.wn-btn-secondary</td><td class="where">Modale Nouveautés</td></tr>
                <tr><td><button class="x-mk-ghost-neutral">Annuler</button></td><td class="name">.mk-confirm-btn-cancel</td><td class="where">MkConfirmDialog (transverse)</td></tr>
                <tr><td><button class="x-mk-ghost-neutral">Annuler</button></td><td class="name">.lfm-btn--secondary</td><td class="where">Modale formulaire liste</td></tr>
                <tr><td><button class="x-mk-ghost-neutral">← Retour</button></td><td class="name">.ob-btn-ghost</td><td class="where">Onboarding wizard → Précédent</td></tr>
              </tbody>
            </table>
          </div>

          <!-- ═══════════════════════════════════════════════════════════ -->
          <div class="inv-section">
            <h2>⬜ Famille H-pill — Ghost pill (Media Manager modales)</h2>
            <p class="intro">
              Forme pill (<code>border-radius: 999px</code>), bord neutre, texte gris.
              Toujours associé à la famille C (pill gradient) dans la même modale.
            </p>
            <div class="reco">
              💡 Migration cible : <code>&lt;MkButton variant="ghost"&gt;</code> (perd la forme pill).
            </div>
            <table class="inv-table">
              <thead>
                <tr><th class="preview">Aperçu (fidèle)</th><th class="name">Classe CSS</th><th class="where">Où ça vit</th></tr>
              </thead>
              <tbody>
                <tr><td><button class="x-mk-pill-ghost">Annuler</button></td><td class="name">.mr-btn-ghost</td><td class="where">Media Manager → Modale Renommer</td></tr>
                <tr><td><button class="x-mk-pill-ghost">Annuler</button></td><td class="name">.mv-btn-ghost</td><td class="where">Media Manager → Modale Déplacer</td></tr>
                <tr><td><button class="x-mk-pill-ghost">Annuler</button></td><td class="name">.mf-btn-ghost</td><td class="where">Media Manager → Modale Dossier</td></tr>
              </tbody>
            </table>
          </div>

          <!-- ═══════════════════════════════════════════════════════════ -->
          <div class="inv-section">
            <h2>⊕ Famille K — Boutons "Fermer" (X de modales)</h2>
            <p class="intro">
              X en haut à droite des modales/popups. Tu en as <strong>~25 versions</strong> visuellement
              identiques disséminées.
            </p>
            <div class="reco">
              💡 Migration cible : <code>&lt;MkButton variant="icon" icon="x"&gt;</code>.
            </div>
            <table class="inv-table">
              <thead>
                <tr><th class="preview">Aperçu (fidèle)</th><th class="name">Classe CSS</th><th class="where">Où ça vit</th></tr>
              </thead>
              <tbody>
                <tr><td><button class="x-mk-icon-close">✕</button></td><td class="name">.wn-close / .sm-close / .pt-popup-close (×5+)</td><td class="where">Modales transverses (~25 occurrences)</td></tr>
                <tr><td><button class="x-mk-icon-close">✕</button></td><td class="name">.mf-close / .mv-close / .mr-close</td><td class="where">Media Manager (3 modales)</td></tr>
                <tr><td><button class="x-mk-icon-close">✕</button></td><td class="name">.so-close / .si-close / .sub-prof-close</td><td class="where">Sous-titres / Surprise overlay</td></tr>
                <tr><td><button class="x-mk-icon-close">✕</button></td><td class="name">.wlsu-detail-close / .wlcal-popup-close</td><td class="where">Watchlist (Suivi + Calendrier)</td></tr>
              </tbody>
            </table>
          </div>

          <!-- ═══════════════════════════════════════════════════════════ -->
          <div class="inv-section">
            <h2>⚙ Famille K — Boutons icône seule (engrenage, crayon)</h2>
            <p class="intro">
              Bouton compact 32×32 avec icône lucide. Header de carte, toolbar, ligne de liste.
            </p>
            <div class="reco">
              💡 Migration cible : <code>&lt;MkButton variant="icon" icon="..."&gt;</code>.
            </div>
            <table class="inv-table">
              <thead>
                <tr><th class="preview">Aperçu (fidèle)</th><th class="name">Classe CSS</th><th class="where">Où ça vit</th></tr>
              </thead>
              <tbody>
                <tr><td><button class="x-mk-icon-square">⚙</button></td><td class="name">.pt-icon-btn</td><td class="where">Portail (Calendar / News / Featured / XpEvents)</td></tr>
                <tr><td><button class="x-mk-icon-square">✎</button></td><td class="name">.ru-icon-btn</td><td class="where">Admin → Demandes utilisateurs</td></tr>
                <tr><td><button class="x-mk-icon-square">⋯</button></td><td class="name">.mk-iconbtn</td><td class="where">PosterCard (carte affiche)</td></tr>
                <tr><td><button class="x-mk-icon-gold">★</button></td><td class="name">.mk-iconbtn--gold</td><td class="where">PosterCard → Bookmark gold (variante doré)</td></tr>
              </tbody>
            </table>
          </div>

          <!-- ═══════════════════════════════════════════════════════════ -->
          <div class="inv-section">
            <h2>⊝ Famille L — Mini "Retirer" (croix rouge ronde sur tag)</h2>
            <p class="intro">
              Mini bouton circulaire 18×18 utilisé pour retirer un élément d'une liste/tag.
              Pas vraiment un bouton plein écran, c'est une variante d'icône.
            </p>
            <div class="reco">
              💡 Migration cible : <code>&lt;MkButton variant="icon" icon="x" size="sm"&gt;</code>
              avec couleur danger custom OU composant <code>&lt;MkChipRemove&gt;</code> dédié.
            </div>
            <table class="inv-table">
              <thead>
                <tr><th class="preview">Aperçu (fidèle)</th><th class="name">Classe CSS</th><th class="where">Où ça vit</th></tr>
              </thead>
              <tbody>
                <tr><td>Marvel <button class="x-mk-mini-remove">✕</button></td><td class="name">.ru-tag-remove</td><td class="where">Admin → Tags utilisateur</td></tr>
                <tr><td>/films <button class="x-mk-mini-remove">✕</button></td><td class="name">.ob-folder-remove</td><td class="where">Onboarding → Étape dossiers</td></tr>
                <tr><td>Item <button class="x-mk-mini-remove">✕</button></td><td class="name">.ale-item-remove</td><td class="where">Portail → Listes (item)</td></tr>
              </tbody>
            </table>
          </div>

          <!-- ═══════════════════════════════════════════════════════════ -->
          <div class="inv-section">
            <h2>🔗 Famille J — Skip / Lien (texte seul)</h2>
            <p class="intro">
              Bouton plus discret encore que ghost : juste du texte cliquable.
              Rare, utilisé pour "Passer", "Plus tard".
            </p>
            <div class="reco">
              💡 Cas non couvert par les 5 variantes MkButton actuelles. À ajouter <code>variant="link"</code> ?
            </div>
            <table class="inv-table">
              <thead>
                <tr><th class="preview">Aperçu (fidèle)</th><th class="name">Classe CSS</th><th class="where">Où ça vit</th></tr>
              </thead>
              <tbody>
                <tr><td><button class="x-mk-skip">Passer</button></td><td class="name">.ob-btn-skip</td><td class="where">Onboarding → Skip étape</td></tr>
              </tbody>
            </table>
          </div>

          <!-- ═══════════════════════════════════════════════════════════ -->
          <div class="inv-section" style="border-top: 1px solid rgb(255,255,255,0.1); padding-top: 32px;">
            <h2>📊 Synthèse finale</h2>
            <table class="inv-table">
              <thead>
                <tr>
                  <th>Famille visuelle</th>
                  <th style="text-align: center;">Couverte par MkButton ?</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                <tr><td>A — Solid accent (plein violet)</td><td style="text-align: center;">✅ <code>variant="primary"</code></td><td>Migration directe</td></tr>
                <tr><td>B — Tinted accent</td><td style="text-align: center;">⚠️ Non</td><td>Si on garde "que des pleins" → convertir en A</td></tr>
                <tr><td>C — Pill gradient accent (MM modales)</td><td style="text-align: center;">⚠️ Perte forme</td><td>Convertir en A (perte de la pill + halo)</td></tr>
                <tr><td>D — Gradient violet/indigo (login, onboarding)</td><td style="text-align: center;">⚠️ Perte gradient</td><td>Convertir en A OU garder exception</td></tr>
                <tr><td>F — Tinted danger</td><td style="text-align: center;">⚠️ Non</td><td>Convertir en G (plein rouge)</td></tr>
                <tr><td>G — Solid danger</td><td style="text-align: center;">✅ <code>variant="danger"</code></td><td>Migration directe</td></tr>
                <tr><td>H — Ghost outline</td><td style="text-align: center;">✅ <code>variant="ghost"</code></td><td>Migration directe</td></tr>
                <tr><td>H-pill — Ghost pill (MM modales)</td><td style="text-align: center;">⚠️ Perte forme</td><td>Convertir en H (perte pill)</td></tr>
                <tr><td>I — Tinted success</td><td style="text-align: center;">❌ Non couvert</td><td>Décision : ajouter <code>variant="success"</code> ?</td></tr>
                <tr><td>J — Skip / lien</td><td style="text-align: center;">❌ Non couvert</td><td>Décision : ajouter <code>variant="link"</code> ?</td></tr>
                <tr><td>K — Icon-only (close, settings, edit)</td><td style="text-align: center;">✅ <code>variant="icon"</code></td><td>Migration directe</td></tr>
                <tr><td>L — Mini remove (croix tag)</td><td style="text-align: center;">⚠️ Faisable</td><td>Via <code>icon size="sm"</code> + couleur custom</td></tr>
                <tr><td>N — Cas particuliers (gradient blanc, gold pulse)</td><td style="text-align: center;">❌ Non couvert</td><td>Garder en exceptions custom OU fusionner</td></tr>
              </tbody>
            </table>

            <h3 style="margin-top: 32px;">⚠ Implication de "tout en plein" (ta décision actuelle)</h3>
            <p style="color: #dde2eb; line-height: 1.6;">
              Si on fusionne strictement vers les 4-5 variantes MkButton actuelles, on perd
              <strong>~6 styles visuels distincts</strong> de MediaKeeper : les tinted (A→B), les pill MM,
              les gradients login/onboarding, les success, les cas particuliers.
              <br><br>
              C'est un changement d'identité visuelle <strong>non négligeable</strong>. Avantage cohérence,
              inconvénient : perte de "signatures" sur des écrans iconiques (login, onboarding).
              <br><br>
              <strong>Décision à arbitrer</strong> : on garde la radicalité "tout en plein" ou on accepte
              2-3 exceptions documentées (login + onboarding + MM modales par exemple) ?
            </p>
          </div>

        </div>
      </div>
    `,
  }),
}
