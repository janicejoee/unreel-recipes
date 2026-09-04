import { Link } from "react-router-dom";
import { useAuth } from "./AuthContext.jsx";

export default function Navbar() {
  const { user, logout } = useAuth();

  return (
    <header className="site-nav">
      <div className="site-nav-inner">
        <Link to="/" className="site-nav-brand">
          <span className="site-nav-name">Unreel</span>
          <span className="site-nav-tagline">Recipes from reels.</span>
        </Link>
        {user && (
          <div className="site-nav-account">
            <span className="site-nav-email">{user.email}</span>
            <button type="button" className="site-nav-logout" onClick={logout}>
              Log out
            </button>
          </div>
        )}
      </div>
    </header>
  );
}
