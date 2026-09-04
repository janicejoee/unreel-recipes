import { Link } from "react-router-dom";

const COVERS = [
  ["#e2b48a", "#c45c26"],
  ["#c5d4b0", "#5d7a45"],
  ["#d7c4e8", "#6b5480"],
  ["#f0c9a0", "#b56a2b"],
  ["#f2c4c0", "#a34d4a"],
  ["#c5d8e8", "#4a6a82"],
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
