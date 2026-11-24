import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "./App";
import { effacerSession, enregistrerSession } from "./lib/session";

const SANTE = {
  statut: "ok",
  modeles: { base: true, robuste: true, gardien: true },
  modele_actif: "robuste",
  empreintes_verifiees: true,
  seuils_calibres: true,
  version: "1.0.0",
};
const json = (corps: unknown, status = 200) => Promise.resolve(new Response(JSON.stringify(corps), { status }));

beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn().mockImplementation(() => json(SANTE)));
});
afterEach(() => {
  vi.unstubAllGlobals();
  effacerSession();
});

const connecter = () => enregistrerSession({ jeton: "abc.def", identifiant: "jury", expire_le: Date.now() / 1000 + 3600 });

describe("App", () => {
  it("affiche la page de connexion sans session", () => {
    render(<App />);
    expect(screen.getByLabelText("Mot de passe")).toBeInTheDocument();
    expect(screen.queryByRole("tab")).not.toBeInTheDocument();
  });

  it("ouvre l'application après une connexion réussie", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation((url: string) =>
        url.endsWith("/auth/connexion") ? json({ jeton: "abc.def", identifiant: "jury", expire_le: Date.now() / 1000 + 3600 }) : json(SANTE),
      ),
    );
    render(<App />);
    await userEvent.type(screen.getByLabelText("Identifiant"), "jury");
    await userEvent.type(screen.getByLabelText("Mot de passe"), "secret");
    await userEvent.click(screen.getByRole("button", { name: "Se connecter" }));
    expect(await screen.findByRole("tab", { name: /Analyser une image/ })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByText("jury")).toBeInTheDocument();
  });

  it("affiche l'erreur du serveur si les identifiants sont faux", async () => {
    vi.stubGlobal("fetch", vi.fn().mockImplementation(() => json({ detail: "Identifiant ou mot de passe incorrect.", code: "identifiants_invalides" }, 401)));
    render(<App />);
    await userEvent.type(screen.getByLabelText("Identifiant"), "jury");
    await userEvent.type(screen.getByLabelText("Mot de passe"), "faux");
    await userEvent.click(screen.getByRole("button", { name: "Se connecter" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Identifiant ou mot de passe incorrect.");
  });

  it("revient à la connexion après déconnexion", async () => {
    connecter();
    render(<App />);
    await userEvent.click(screen.getByRole("button", { name: "Se déconnecter" }));
    expect(screen.getByText("Vous êtes déconnecté.")).toBeInTheDocument();
  });

  it("change d'onglet au clavier", async () => {
    connecter();
    render(<App />);
    expect(await screen.findByText(/Modèle robuste, défenses actives/)).toBeInTheDocument();
    screen.getByRole("tab", { name: /Analyser une image/ }).focus();
    await userEvent.keyboard("{ArrowRight}");
    expect(screen.getByRole("tab", { name: /Laboratoire de sécurité/ })).toHaveAttribute("aria-selected", "true");
  });

  it("affiche un bandeau si le serveur est injoignable", async () => {
    connecter();
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    render(<App />);
    expect(await screen.findByRole("alert")).toHaveTextContent(/Serveur indisponible/);
  });
});
