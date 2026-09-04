import { Link } from "react-router-dom";

const COVERS = [
  ["#f2c4c0", "#c62828"],
  ["#e8a0a0", "#9b1c1c"],
  ["#f0c9c0", "#b71c1c"],
  ["#d4a0a8", "#7a1f2b"],
  ["#e8b4a8", "#c43c2b"],
  ["#f5d0d0", "#8b2e2e"],
];

function coverFor(id) {
  let hash = 0;
  for (const char of id) hash += char.charCodeAt(0);
  return COVERS[hash % COVERS.length];
}

function initial(title) {
  const letter = (title || "R").trim().charAt(0);
  return letter.toUpperCase();
}

function Cover({ recipe }) {
  if (recipe.thumbnail_url) {
    return (
      <img
        className="gallery-cover-img"
        src={recipe.thumbnail_url}
        alt=""
      />
    );
  }

  const [from, to] = coverFor(recipe.id);
  return (
    <div
      className="gallery-cover"
      style={{ background: `linear-gradient(145deg, ${from}, ${to})` }}
    >
      <span className="gallery-initial">{initial(recipe.title)}</span>
    </div>
  );
}

export default function RecipeGallery({ recipes }) {
  return (
    <section className="gallery-section">
      <h3>Recipes</h3>
      {recipes.length === 0 ? (
        <p className="empty">No recipes yet. Paste a reel above to get started.</p>
      ) : (
        <ul className="gallery">
          {recipes.map((recipe) => (
            <li key={recipe.id}>
              <Link className="gallery-card" to={`/recipes/${recipe.id}`}>
                <Cover recipe={recipe} />
                <div className="gallery-body">
                  <span className="gallery-title">{recipe.title || "Untitled recipe"}</span>
                  <span className="gallery-meta">
                    {(recipe.ingredients || []).length} ingredients
                    {(recipe.steps || []).length ? ` · ${recipe.steps.length} steps` : ""}
                  </span>
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
