/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        background: '#463F3A',
        text: '#F4F3EE',
        highlight: '#E0AFA0',
        box: '#BCB8B1',
      },
      fontFamily: {
        oswald: ['var(--font-oswald)', 'sans-serif'],
        inter: ['var(--font-inter)', 'sans-serif'],
      },
      spacing: {
        'clear': '70px', // Clear space kiri-kanan
      },
    },
  },
  plugins: [],
}
