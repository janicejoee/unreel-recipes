import { useState } from "react";
import { useAuth } from "./AuthContext.jsx";

export default function AuthPage() {
  const { login, signup } = useAuth();
  const [mode, setMode] = useState("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const creating = mode === "signup";

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      if (creating) await signup(email, password);
      else await login(email, password);
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="auth-page">
      <header className="page-intro">
        <h1>{creating ? "Create your cookbook" : "Welcome back"}</h1>
        <p className="lede">
          {creating
            ? "Make an account to save recipes to your own collection."
            : "Sign in to see the recipes you’ve saved."}
        </p>
      </header>

      <form className="auth-form" onSubmit={handleSubmit}>
        <label>
          Email
          <input
            type="email"
            name="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            autoComplete="email"
            required
          />
        </label>
        <label>
          Password
          <input
            type="password"
            name="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            autoComplete={creating ? "new-password" : "current-password"}
            minLength={6}
            required
          />
        </label>
        <button type="submit" disabled={submitting}>
          {submitting ? "Working…" : creating ? "Create account" : "Sign in"}
        </button>
      </form>

      {error && <p className="error">{error}</p>}

      <p className="auth-switch">
        {creating ? "Already have an account?" : "New here?"}{" "}
        <button
          type="button"
          onClick={() => {
            setError("");
            setMode(creating ? "login" : "signup");
          }}
        >
          {creating ? "Sign in" : "Create an account"}
        </button>
      </p>
    </main>
  );
}
