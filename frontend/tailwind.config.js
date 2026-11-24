/** @type {import('tailwindcss').Config} */
// Identité « fiche de contrôle de fruits » : papier blanc, encre vert-noir,
// vert feuille pour « frais », brun meurtri pour « pourri ». Pas d'ombres, angles discrets.
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Schibsted Grotesk"', "ui-sans-serif", "system-ui", "sans-serif"],
      },
      colors: {
        // Gris légèrement verts (remplacent le gris bleuté par défaut de Tailwind).
        slate: {
          50: "#f4f5f1", 100: "#eaece5", 200: "#d9ddd2", 300: "#c3c8bb", 400: "#8f9685", 500: "#5c6355",
          600: "#474d42", 700: "#3b4036", 800: "#272b23", 900: "#1b1e18", 950: "#141711",
        },
        frais: { 50: "#eef4ec", 100: "#dbe8d6", 300: "#9cc58f", 500: "#3d7f36", 600: "#2f6f2a", 700: "#25571f", 900: "#162b12" },
        pourri: { 50: "#f7efe6", 100: "#eedcc8", 300: "#e0a96b", 500: "#a35b1a", 600: "#8a4b14", 700: "#6e3b10", 900: "#2e1a08" },
        // Ancien accent indigo : devient l'encre de l'interface.
        bouclier: { 50: "#f1f3ef", 100: "#e2e6de", 300: "#c9d1c1", 500: "#3c4636", 600: "#1d2419", 700: "#141912", 900: "#0f130d" },
      },
      borderRadius: { lg: "4px", xl: "6px", "2xl": "8px" },
      boxShadow: { sm: "none", DEFAULT: "none", md: "none" },
      animation: { apparition: "none" },
    },
  },
  plugins: [],
};
