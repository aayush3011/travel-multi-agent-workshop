/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{html,ts}",
  ],
  theme: {
    extend: {
      colors: {
        cosmos: {
          primary: '#0078D4',
          accent: '#00BCF2',
          dark: '#1a1a1a',
        }
      }
    },
  },
  plugins: [],
}
