function formatAmount(item) {
  return [item.quantity, item.unit].filter(Boolean).join(" ");
}

export default function RecipeCard({ recipe }) {
  return (
    <article className="recipe">
      {recipe.thumbnail_url && (
        <img className="recipe-hero" src={recipe.thumbnail_url} alt="" />
      )}
      <h2>{recipe.title || "Untitled recipe"}</h2>
      {recipe.source && (
        <p className="source">
          <a href={recipe.source} target="_blank" rel="noreferrer">
            View original reel
          </a>
        </p>
      )}
      <h3>Ingredients</h3>
      <ul className="ingredients">
        {(recipe.ingredients || []).map((item, index) => (
          <li key={`${item.name}-${index}`}>
            <span>{item.name}</span>
            <span className="qty">{formatAmount(item)}</span>
          </li>
        ))}
      </ul>
      <h3>Steps</h3>
      <ol className="steps">
        {(recipe.steps || []).map((step, index) => (
          <li key={index}>{step}</li>
        ))}
      </ol>
    </article>
  );
}
