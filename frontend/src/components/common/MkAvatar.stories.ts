import type { Meta, StoryObj } from '@storybook/vue3-vite'
import MkAvatar from './MkAvatar.vue'

const TIERS = ['bronze', 'silver', 'gold', 'platinum', 'diamond', 'master', 'legendary'] as const

const meta: Meta<typeof MkAvatar> = {
  title: 'Design system/MkAvatar',
  component: MkAvatar,
  tags: ['autodocs'],
  argTypes: {
    src: { control: 'text' },
    name: { control: 'text' },
    size: { control: { type: 'range', min: 16, max: 120, step: 4 } },
    shape: { control: 'select', options: ['circle', 'square'] },
    tier: {
      control: 'select',
      options: [null, ...TIERS],
    },
  },
}
export default meta

type Story = StoryObj<typeof MkAvatar>

export const Silhouette: Story = {
  name: 'Silhouette (no image)',
  args: { name: 'Alice', size: 56 },
  render: args => ({
    components: { MkAvatar },
    setup: () => ({ args }),
    template: '<MkAvatar v-bind="args" />',
  }),
}

export const WithImage: Story = {
  name: 'With image',
  args: {
    name: 'Alice',
    size: 56,
    src: 'https://i.pravatar.cc/120?img=12',
  },
  render: args => ({
    components: { MkAvatar },
    setup: () => ({ args }),
    template: '<MkAvatar v-bind="args" />',
  }),
}

export const TierBronze: Story = {
  args: { name: 'Bronze user', size: 56, tier: 'bronze' },
  render: args => ({
    components: { MkAvatar },
    setup: () => ({ args }),
    template: '<MkAvatar v-bind="args" />',
  }),
}

export const TierSilver: Story = {
  args: { name: 'Silver user', size: 56, tier: 'silver' },
  render: args => ({
    components: { MkAvatar },
    setup: () => ({ args }),
    template: '<MkAvatar v-bind="args" />',
  }),
}

export const TierGold: Story = {
  args: { name: 'Gold user', size: 56, tier: 'gold' },
  render: args => ({
    components: { MkAvatar },
    setup: () => ({ args }),
    template: '<MkAvatar v-bind="args" />',
  }),
}

export const TierPlatinum: Story = {
  args: { name: 'Platinum user', size: 56, tier: 'platinum' },
  render: args => ({
    components: { MkAvatar },
    setup: () => ({ args }),
    template: '<MkAvatar v-bind="args" />',
  }),
}

export const TierDiamond: Story = {
  args: { name: 'Diamond user', size: 56, tier: 'diamond' },
  render: args => ({
    components: { MkAvatar },
    setup: () => ({ args }),
    template: '<MkAvatar v-bind="args" />',
  }),
}

export const TierMaster: Story = {
  args: { name: 'Master user', size: 56, tier: 'master' },
  render: args => ({
    components: { MkAvatar },
    setup: () => ({ args }),
    template: '<MkAvatar v-bind="args" />',
  }),
}

export const TierLegendary: Story = {
  args: { name: 'Legendary user', size: 56, tier: 'legendary' },
  render: args => ({
    components: { MkAvatar },
    setup: () => ({ args }),
    template: '<MkAvatar v-bind="args" />',
  }),
}

export const AllTiers: Story = {
  name: 'Tous les tiers (silhouette)',
  render: () => ({
    components: { MkAvatar },
    setup: () => ({ tiers: TIERS }),
    template: `
      <div style="display: flex; gap: 32px; align-items: flex-end; flex-wrap: wrap; padding: 24px;">
        <div v-for="t in tiers" :key="t" style="display: flex; flex-direction: column; align-items: center; gap: 8px;">
          <MkAvatar :name="t" :size="56" :tier="t" />
          <span style="color: #a8b2c2; font-size: 12px; text-transform: uppercase; letter-spacing: 0.04em;">{{ t }}</span>
        </div>
      </div>
    `,
  }),
}

export const AllTiersWithImage: Story = {
  name: 'Tous les tiers (avec image)',
  render: () => ({
    components: { MkAvatar },
    setup: () => {
      const samples = [
        { tier: 'bronze', img: 12 },
        { tier: 'silver', img: 23 },
        { tier: 'gold', img: 14 },
        { tier: 'platinum', img: 45 },
        { tier: 'diamond', img: 56 },
        { tier: 'master', img: 17 },
        { tier: 'legendary', img: 33 },
      ]
      return { samples }
    },
    template: `
      <div style="display: flex; gap: 32px; align-items: flex-end; flex-wrap: wrap; padding: 24px;">
        <div v-for="s in samples" :key="s.tier" style="display: flex; flex-direction: column; align-items: center; gap: 8px;">
          <MkAvatar
            :name="s.tier"
            :size="56"
            :tier="s.tier"
            :src="'https://i.pravatar.cc/120?img=' + s.img"
          />
          <span style="color: #a8b2c2; font-size: 12px; text-transform: uppercase; letter-spacing: 0.04em;">{{ s.tier }}</span>
        </div>
      </div>
    `,
  }),
}

export const SizesAndTiers: Story = {
  name: 'Tailles × tiers (matrice)',
  render: () => ({
    components: { MkAvatar },
    setup: () => ({
      tiers: TIERS,
      sizes: [22, 32, 40, 56, 88],
    }),
    template: `
      <div style="display: flex; flex-direction: column; gap: 24px; padding: 24px;">
        <div v-for="t in tiers" :key="t" style="display: flex; gap: 24px; align-items: center;">
          <span style="width: 80px; color: #a8b2c2; font-size: 12px; text-transform: uppercase; letter-spacing: 0.04em;">{{ t }}</span>
          <MkAvatar v-for="s in sizes" :key="s" :name="t" :size="s" :tier="t" />
        </div>
      </div>
    `,
  }),
}

export const SquareTier: Story = {
  name: 'Carré avec tier',
  args: { name: 'Square legend', size: 56, tier: 'legendary', shape: 'square' },
  render: args => ({
    components: { MkAvatar },
    setup: () => ({ args }),
    template: '<MkAvatar v-bind="args" />',
  }),
}

export const FallbackOnError: Story = {
  name: 'Image cassée → fallback silhouette',
  args: {
    name: 'Broken image',
    size: 56,
    tier: 'gold',
    src: 'https://example.com/nonexistent-avatar.jpg',
  },
  render: args => ({
    components: { MkAvatar },
    setup: () => ({ args }),
    template: '<MkAvatar v-bind="args" />',
  }),
}
