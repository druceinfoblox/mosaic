/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'ib-blue': '#0066cc',
        'ib-dark': '#1a2332',
        'ib-navy': '#152030',
      },
    },
  },
  plugins: [],
}
