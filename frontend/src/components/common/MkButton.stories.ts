import type { Meta, StoryObj } from '@storybook/vue3-vite'
import MkButton from './MkButton.vue'

const meta: Meta<typeof MkButton> = {
  title: 'Design system/MkButton',
  component: MkButton,
  tags: ['autodocs'],
  argTypes: {
    variant: {
      control: 'select',
      options: ['primary', 'secondary', 'danger', 'ghost', 'icon'],
    },
    size: { control: 'select', options: ['sm', 'md', 'lg'] },
    icon: { control: 'text' },
    iconRight: { control: 'text' },
    loading: { control: 'boolean' },
    disabled: { control: 'boolean' },
    fullwidth: { control: 'boolean' },
  },
}
export default meta

type Story = StoryObj<typeof MkButton>

export const Primary: Story = {
  args: { variant: 'primary', icon: 'save' },
  render: args => ({
    components: { MkButton },
    setup: () => ({ args }),
    template: '<MkButton v-bind="args">Enregistrer</MkButton>',
  }),
}

export const Secondary: Story = {
  args: { variant: 'secondary' },
  render: args => ({
    components: { MkButton },
    setup: () => ({ args }),
    template: '<MkButton v-bind="args">Précédent</MkButton>',
  }),
}

export const Danger: Story = {
  args: { variant: 'danger', icon: 'trash-2' },
  render: args => ({
    components: { MkButton },
    setup: () => ({ args }),
    template: '<MkButton v-bind="args">Supprimer</MkButton>',
  }),
}

export const Ghost: Story = {
  args: { variant: 'ghost' },
  render: args => ({
    components: { MkButton },
    setup: () => ({ args }),
    template: '<MkButton v-bind="args">Annuler</MkButton>',
  }),
}

export const IconOnly: Story = {
  args: { variant: 'icon', icon: 'settings', ariaLabel: 'Paramètres' },
  render: args => ({
    components: { MkButton },
    setup: () => ({ args }),
    template: '<MkButton v-bind="args" />',
  }),
}

export const WithIcon: Story = {
  args: { variant: 'primary', icon: 'download' },
  render: args => ({
    components: { MkButton },
    setup: () => ({ args }),
    template: '<MkButton v-bind="args">Importer</MkButton>',
  }),
}

export const WithIconRight: Story = {
  name: 'Icône à droite (wizard)',
  args: { variant: 'primary', iconRight: 'chevron-right' },
  render: args => ({
    components: { MkButton },
    setup: () => ({ args }),
    template: '<MkButton v-bind="args">Suivant</MkButton>',
  }),
}

export const WizardNavigation: Story = {
  name: 'Wizard onboarding (cas réel)',
  render: () => ({
    components: { MkButton },
    template: `
      <div style="display: flex; gap: 12px; align-items: center;">
        <MkButton variant="ghost" icon="chevron-left">Retour</MkButton>
        <MkButton variant="primary" icon-right="chevron-right">Suivant</MkButton>
      </div>
    `,
  }),
}

export const Loading: Story = {
  args: { variant: 'primary', loading: true },
  render: args => ({
    components: { MkButton },
    setup: () => ({ args }),
    template: '<MkButton v-bind="args">Enregistrement…</MkButton>',
  }),
}

export const Disabled: Story = {
  args: { variant: 'primary', disabled: true },
  render: args => ({
    components: { MkButton },
    setup: () => ({ args }),
    template: '<MkButton v-bind="args">Indisponible</MkButton>',
  }),
}

export const Fullwidth: Story = {
  args: { variant: 'primary', fullwidth: true, size: 'lg' },
  render: args => ({
    components: { MkButton },
    setup: () => ({ args }),
    template: `
      <div style="width: 320px; padding: 12px; border: 1px dashed rgb(255,255,255,0.15); border-radius: 8px;">
        <MkButton v-bind="args">Se connecter</MkButton>
      </div>
    `,
  }),
}

export const AllVariants: Story = {
  name: 'Toutes les variantes',
  render: () => ({
    components: { MkButton },
    template: `
      <div style="display: flex; flex-direction: column; gap: 16px; align-items: flex-start;">
        <div style="display: flex; gap: 12px; align-items: center;">
          <MkButton variant="primary" icon="save">Enregistrer</MkButton>
          <MkButton variant="secondary">Précédent</MkButton>
          <MkButton variant="danger" icon="trash-2">Supprimer</MkButton>
          <MkButton variant="ghost">Annuler</MkButton>
          <MkButton variant="icon" icon="settings" aria-label="Paramètres" />
        </div>
      </div>
    `,
  }),
}

export const AdminCardActions: Story = {
  name: 'Cartes admin (cas réel)',
  render: () => ({
    components: { MkButton },
    template: `
      <div style="display: flex; gap: 16px; align-items: stretch;">
        <div style="flex: 1; padding: 20px; background: #24262b; border: 1px solid rgb(255,255,255,0.06); border-radius: 12px;">
          <div style="display: flex; align-items: center; gap: 8px; color: #fff; font-weight: 600; margin-bottom: 6px;">
            ⬆ Import Jellystats
          </div>
          <div style="color: #a8b2c2; font-size: 13px; margin-bottom: 16px;">Importer un backup JSON.</div>
          <MkButton variant="primary" icon="upload">Choisir un fichier</MkButton>
        </div>
        <div style="flex: 1; padding: 20px; background: #24262b; border: 1px solid rgb(255,255,255,0.06); border-radius: 12px;">
          <div style="display: flex; align-items: center; gap: 8px; color: #fff; font-weight: 600; margin-bottom: 6px;">
            🗑 Purger import
          </div>
          <div style="color: #a8b2c2; font-size: 13px; margin-bottom: 16px;">Supprimer les données importées.</div>
          <MkButton variant="danger" icon="trash-2">Purger</MkButton>
        </div>
        <div style="flex: 1; padding: 20px; background: #24262b; border: 1px solid rgb(255,255,255,0.06); border-radius: 12px;">
          <div style="display: flex; align-items: center; gap: 8px; color: #fff; font-weight: 600; margin-bottom: 6px;">
            🔄 Migration médiathèques
          </div>
          <div style="color: #a8b2c2; font-size: 13px; margin-bottom: 16px;">Corrige les lectures sans médiathèque détectée.</div>
          <MkButton variant="primary" icon="refresh-cw">Lancer</MkButton>
        </div>
      </div>
    `,
  }),
}

export const AllSizes: Story = {
  name: 'Toutes les tailles',
  render: () => ({
    components: { MkButton },
    template: `
      <div style="display: flex; gap: 16px; align-items: center;">
        <MkButton variant="primary" size="sm">Petit</MkButton>
        <MkButton variant="primary" size="md">Moyen</MkButton>
        <MkButton variant="primary" size="lg">Grand</MkButton>
      </div>
    `,
  }),
}

export const AllStates: Story = {
  name: 'Tous les états',
  render: () => ({
    components: { MkButton },
    template: `
      <div style="display: flex; gap: 16px; align-items: center;">
        <MkButton variant="primary">Normal</MkButton>
        <MkButton variant="primary" disabled>Désactivé</MkButton>
        <MkButton variant="primary" loading>En cours…</MkButton>
      </div>
    `,
  }),
}
