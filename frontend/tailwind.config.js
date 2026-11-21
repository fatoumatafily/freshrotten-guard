/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "Segoe UI", "Roboto", "sans-serif"],
      },
      colors: {
        // Identité « fraîcheur » : contrastes vérifiés WCAG AA sur fond clair et sombre.
        frais: { 50: "#ecfdf3", 100: "#d1fadf", 500: "#16a34a", 600: "#15803d", 700: "#166534", 300: "#86efac", 900: "#052e16" },
        pourri: { 50: "#fff7ed", 100: "#ffedd5", 500: "#c2410c", 600: "#9a3412", 700: "#7c2d12", 300: "#fdba74", 900: "#431407" },
        bouclier: { 50: "#eef2ff", 100: "#e0e7ff", 500: "#4f46e5", 600: "#4338ca", 700: "#3730a3", 300: "#a5b4fc", 900: "#1e1b4b" },
      },
      keyframes: {
        apparition: { "0%": { opacity: "0", transform: "translateY(6px) scale(.98)" }, "100%": { opacity: "1", transform: "none" } },
      },
      animation: { apparition: "apparition .35s ease-out both" },
    },
  },
  plugins: [],
};
