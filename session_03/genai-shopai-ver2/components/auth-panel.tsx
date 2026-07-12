"use client";

import { LogIn, LogOut, ShieldCheck, UserPlus } from "lucide-react";
import { FormEvent, useState } from "react";
import { login, register } from "@/utils/api";
import type { AuthResponse, AuthUser } from "@/utils/types";

type AuthPanelProps = {
  user: AuthUser | null;
  onAuthenticated: (response: AuthResponse) => void;
  onLogout: () => void;
};

export function AuthPanel({ user, onAuthenticated, onLogout }: AuthPanelProps) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function submitAuth() {
    if (loading || !email.trim() || !password.trim()) return;

    setLoading(true);
    setError("");

    try {
      const response =
        mode === "register"
          ? await register({
            email,
            password,
            display_name: displayName || email.split("@")[0]
          })
          : await login({ email, password });
      onAuthenticated(response);
    } catch (authError) {
      setError(authError instanceof Error ? authError.message : "Không thể đăng nhập.");
    } finally {
      setLoading(false);
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    submitAuth();
  }

  if (user) {
    return (
      <section className="rounded-lg border border-teal-100 bg-teal-50 p-4">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <p className="flex items-center gap-2 text-sm font-bold text-teal-900">
              <ShieldCheck className="h-4 w-4" />
              Đang lưu memory theo tài khoản
            </p>
            <p className="mt-1 truncate text-sm text-teal-800">
              {user.display_name} · {user.email}
            </p>
          </div>
          <button
            className="inline-flex h-9 shrink-0 items-center gap-2 rounded-md border border-teal-200 bg-white px-3 text-sm font-bold text-teal-800 hover:bg-teal-100"
            onClick={onLogout}
          >
            <LogOut className="h-4 w-4" />
            Thoát
          </button>
        </div>
      </section>
    );
  }

  return (
    <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div className="mb-4 flex gap-2">
        <button
          className={`inline-flex h-9 flex-1 items-center justify-center gap-2 rounded-md text-sm font-bold ${mode === "login" ? "bg-brand-ink text-white" : "bg-slate-100 text-slate-700 hover:bg-slate-200"
            }`}
          onClick={() => setMode("login")}
          type="button"
        >
          <LogIn className="h-4 w-4" />
          Đăng nhập
        </button>
        <button
          className={`inline-flex h-9 flex-1 items-center justify-center gap-2 rounded-md text-sm font-bold ${mode === "register" ? "bg-brand-orange text-white" : "bg-slate-100 text-slate-700 hover:bg-slate-200"
            }`}
          onClick={() => setMode("register")}
          type="button"
        >
          <UserPlus className="h-4 w-4" />
          Đăng ký
        </button>
      </div>

      <form className="space-y-3" onSubmit={handleSubmit}>
        {mode === "register" ? (
          <input
            className="h-10 w-full rounded-md border border-slate-200 px-3 text-sm outline-none focus:border-brand-orange"
            value={displayName}
            onChange={(event) => setDisplayName(event.target.value)}
            placeholder="Tên hiển thị"
          />
        ) : null}
        <input
          className="h-10 w-full rounded-md border border-slate-200 px-3 text-sm outline-none focus:border-brand-orange"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          placeholder="Email"
          type="email"
        />
        <input
          className="h-10 w-full rounded-md border border-slate-200 px-3 text-sm outline-none focus:border-brand-orange"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          placeholder="Mật khẩu"
          type="password"
        />
        {error ? <p className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</p> : null}
        <button
          className="h-10 w-full rounded-md bg-brand-orange text-sm font-bold text-white hover:bg-orange-600 disabled:bg-slate-300"
          disabled={loading || !email.trim() || !password.trim()}
          onClick={submitAuth}
          type="button"
        >
          {loading ? "Đang xử lý..." : mode === "login" ? "Đăng nhập" : "Tạo tài khoản"}
        </button>
      </form>
    </section>
  );
}
