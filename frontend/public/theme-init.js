// Applique le thème avant le premier rendu (évite le flash). Fichier séparé : compatible CSP stricte.
try {
  var t = localStorage.getItem("frg-theme");
  if (t === "dark" || (!t && window.matchMedia("(prefers-color-scheme: dark)").matches)) {
    document.documentElement.classList.add("dark");
  }
} catch (e) {
  /* stockage indisponible : thème clair par défaut */
}
