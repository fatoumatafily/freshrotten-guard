import { effacerSession, enregistrerSession } from "../lib/session";
import { ErreurApi, api } from "./client";

const repondre = (statut: number, corps: unknown) =>
  vi.fn().mockResolvedValue(new Response(JSON.stringify(corps), { status: statut, headers: { "Content-Type": "application/json" } }));

afterEach(() => {
  vi.unstubAllGlobals();
  effacerSession();
});

describe("client API", () => {
  it("envoie le jeton de session, jamais de cookie", async () => {
    enregistrerSession({ jeton: "abc.def", identifiant: "jury", expire_le: Date.now() / 1000 + 3600 });
    const f = repondre(200, { statut: "ok" });
    vi.stubGlobal("fetch", f);
    await api.sante();
    const init = (f.mock.calls[0] as [string, RequestInit])[1];
    expect(init.credentials).toBe("omit");
    expect(new Headers(init.headers).get("Authorization")).toBe("Bearer abc.def");
  });

  it("revient à la connexion si le jeton est refusé", async () => {
    enregistrerSession({ jeton: "abc.def", identifiant: "jury", expire_le: Date.now() / 1000 + 3600 });
    const ecouteur = vi.fn();
    window.addEventListener("frg:deconnexion", ecouteur);
    vi.stubGlobal("fetch", repondre(401, { detail: "Authentification requise.", code: "non_authentifie" }));
    await expect(api.metriques()).rejects.toMatchObject({ statut: 401 });
    expect(ecouteur).toHaveBeenCalled();
    expect(sessionStorage.getItem("frg-session")).toBeNull();
    window.removeEventListener("frg:deconnexion", ecouteur);
  });

  it("appelle /api sans en-tête d'authentification hors session", async () => {
    const f = repondre(200, { statut: "ok" });
    vi.stubGlobal("fetch", f);
    await api.sante();
    const [url, init] = f.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("/api/sante");
    expect(init.credentials).toBe("omit");
    expect(new Headers(init.headers).has("Authorization")).toBe(false);
  });

  it("transmet le message et le code d'erreur du serveur", async () => {
    vi.stubGlobal("fetch", repondre(400, { detail: "Fichier invalide.", code: "executable" }));
    const erreur = await api.analyser(new Blob(["x"])).catch((e: unknown) => e);
    expect(erreur).toBeInstanceOf(ErreurApi);
    expect(erreur).toMatchObject({ message: "Fichier invalide.", code: "executable", statut: 400 });
  });

  it("utilise un message par défaut si le corps n'est pas du JSON", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("oups", { status: 429 })));
    await expect(api.sante()).rejects.toMatchObject({ code: "http_429", message: expect.stringMatching(/Trop de requêtes/) });
  });

  it("signale un serveur injoignable", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    await expect(api.sante()).rejects.toMatchObject({ code: "serveur_indisponible", statut: 0 });
  });

  it("n'envoie la cible qu'avec PGD ciblée", async () => {
    const f = repondre(200, {});
    vi.stubGlobal("fetch", f);
    await api.attaquer(new Blob(["x"]), "pgd", 0.03, "boite_blanche", "apple_fresh");
    const corps = (f.mock.calls[0] as [string, RequestInit])[1].body as FormData;
    expect(corps.get("cible")).toBeNull();
    expect(corps.get("epsilon")).toBe("0.0300");
  });
});
