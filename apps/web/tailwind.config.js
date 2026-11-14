/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: [
          "-apple-system",
          "BlinkMacSystemFont",
          "SF Pro Text",
          "Segoe UI",
          "PingFang SC",
          "Hiragino Sans GB",
          "Noto Sans SC",
          "sans-serif",
        ],
        serif: ["Source Serif 4", "Georgia", "Times New Roman", "serif"],
      },
    },
  },
  plugins: [],
};
