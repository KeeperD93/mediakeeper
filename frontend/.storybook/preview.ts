import type { Preview } from '@storybook/vue3-vite'

import '../src/styles/design-tokens.css'
import '../src/styles/main.css'
import './inventory.css'

const preview: Preview = {
  parameters: {
    layout: 'centered',
    controls: {
      matchers: {
        color: /(background|color)$/i,
        date: /Date$/i,
      },
    },
    backgrounds: {
      default: 'admin',
      values: [
        { name: 'admin', value: '#1f2126' },
        { name: 'admin-card', value: '#24262b' },
        { name: 'portal', value: '#1f2126' },
        { name: 'chrome', value: '#1c2533' },
      ],
    },
    a11y: {
      test: 'todo',
    },
  },
}

export default preview
