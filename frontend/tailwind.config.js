/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{vue,js,ts}',
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        mk: {
          primary: '#4f46e5',    // indigo-600
          hover:   '#4338ca',    // indigo-700
          accent:  '#818cf8',    // indigo-400
          bg: {
            primary:   'var(--bg-primary)',
            secondary: 'var(--bg-secondary)',
            tertiary:  'var(--bg-tertiary)',
          },
          text: {
            primary:   'var(--text-primary)',
            secondary: 'var(--text-secondary)',
            muted:     'var(--text-muted)',
          },
          border: 'var(--border)',
        },
      },
    },
  },
  plugins: [],
}
