import { useEffect, useState } from "react";
import { Navigate, Route, Routes, useNavigate } from "react-router-dom";
import { authFetch } from "./api.js";
import { useAuth } from "./AuthContext.jsx";
import AuthPage from "./AuthPage.jsx";
import Navbar from "./Navbar.jsx";
import RecipeGallery from "./RecipeGallery.jsx";
import RecipePage from "./RecipePage.jsx";

async function readExtractStream(response, onEvent) {
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";
    for (const line of lines) {
      if (!line.trim()) continue;
      onEvent(JSON.parse(line));
    }
  }

  if (buffer.trim()) {
    onEvent(JSON.parse(buffer));
  }
}

function Home() {
  const navigate = useNavigate();
  const [url, setUrl] = useState("");
  const [recipes, setRecipes] = useState([]);
  const [error, setError] = useState("");
  const [status, setStatus] = useState("");

  useEffect(() => {
    authFetch("/recipes", { headers: { Accept: "application/json" } })
      .then((response) => {
        if (!response.ok) throw new Error("Could not load saved recipes.");
        return response.json();
      })
      .then(setRecipes)
      .catch((err) => setError(err.message));
  }, []);

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setStatus("Starting…");

    try {
      const response = await authFetch("/extract", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: url.trim() }),
      });

      const contentType = response.headers.get("content-type") || "";
      if (!contentType.includes("ndjson")) {
        const data = await response.json();
        throw new Error(data.error || "Could not extract a recipe from that reel.");
      }

      await readExtractStream(response, (event) => {
        if (event.type === "status") {
          setStatus(event.message);
        } else if (event.type === "recipe") {
          navigate(`/recipes/${event.recipe.id}`);
        } else if (event.type === "error") {
          throw new Error(event.error || "Could not extract a recipe from that reel.");
        }
      });
    } catch (err) {
      setError(err.message);
    } finally {
      setStatus("");
    }
  }

  const loading = Boolean(status);

  return (
    <main>
      <header className="page-intro">
        <p className="lede">Recipes from reels.</p>
      </header>

      <form onSubmit={handleSubmit}>
        <input
          type="url"
          name="url"
          value={url}
          onChange={(event) => setUrl(event.target.value)}
          placeholder="https://www.instagram.com/reel/..."
          autoComplete="off"
          required
        />
        <button type="submit" disabled={loading}>
          {loading ? "Working…" : "Get recipe"}
        </button>
      </form>

      {status && <p className="status">{status}</p>}
      {error && <p className="error">{error}</p>}

      <RecipeGallery recipes={recipes} />
    </main>
  );
}

export default function App() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <>
        <Navbar />
        <main>
          <p className="status">Loading…</p>
        </main>
      </>
    );
  }

  if (!user) {
    return (
      <>
        <Navbar />
        <AuthPage />
      </>
    );
  }

  return (
    <>
      <Navbar />
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/recipes/:id" element={<RecipePage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </>
  );
}
