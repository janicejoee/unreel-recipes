import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { authFetch } from "./api.js";
import RecipeCard from "./RecipeCard.jsx";

export default function RecipePage() {
  const { id } = useParams();
  const [recipe, setRecipe] = useState(null);
  const [error, setError] = useState("");

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

  return (
    <main className="recipe-page">
      <Link to="/" className="back-to-recipes">
        ← Back to recipes
      </Link>
      {error && <p className="error">{error}</p>}
      {!error && !recipe && <p className="status">Loading recipe…</p>}
      {recipe && <RecipeCard recipe={recipe} />}
    </main>
  );
}
