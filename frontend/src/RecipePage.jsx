import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { authFetch, deleteRecipe } from "./api.js";
import RecipeCard from "./RecipeCard.jsx";

export default function RecipePage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [recipe, setRecipe] = useState(null);
  const [error, setError] = useState("");
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    setRecipe(null);
    setError("");
    authFetch(`/recipes/${id}`, { headers: { Accept: "application/json" } })
      .then((response) => {
        if (response.status === 404) throw new Error("Recipe not found.");
        if (!response.ok) throw new Error("Could not load this recipe.");
        return response.json();
      })
      .then(setRecipe)
      .catch((err) => setError(err.message));
  }, [id]);

  async function handleDelete() {
    const label = recipe?.title || "this recipe";
    if (!window.confirm(`Delete “${label}”? This cannot be undone.`)) return;

    setDeleting(true);
    setError("");
    try {
      await deleteRecipe(id);
      navigate("/");
    } catch (err) {
      setError(err.message);
      setDeleting(false);
    }
  }

  return (
    <main className="recipe-page">
      <div className="recipe-page-nav">
        <Link to="/" className="back-to-recipes">
          ← Back to recipes
        </Link>
        {recipe && (
          <button
            type="button"
            className="delete-recipe"
            onClick={handleDelete}
            disabled={deleting}
          >
            {deleting ? "Deleting…" : "Delete recipe"}
          </button>
        )}
      </div>
      {error && <p className="error">{error}</p>}
      {!error && !recipe && <p className="status">Loading recipe…</p>}
      {recipe && <RecipeCard recipe={recipe} />}
    </main>
  );
}
