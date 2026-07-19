"use client";

import type { FormEvent } from "react";
import { useCallback, useEffect, useMemo, useState } from "react";
import type { LucideIcon } from "lucide-react";
import {
  AlertTriangle,
  BarChart3,
  BriefcaseBusiness,
  CheckCircle2,
  Database,
  Download,
  FileText,
  History,
  LayoutDashboard,
  LockKeyhole,
  LogOut,
  Mail,
  RefreshCw,
  ShieldCheck,
  SlidersHorizontal,
  UploadCloud,
  UserPlus,
  Users,
  XCircle
} from "lucide-react";
import {
  fetchAnalysis,
  fetchAnalyses,
  fetchCVProfiles,
  fetchDashboard,
  fetchJDProfiles,
  fetchMe,
  login,
  rankCandidates,
  register,
  type RankingEngine
} from "@/lib/api";
import type {
  AnalysisDetail,
  AnalysisListItem,
  AuthResponse,
  CandidateScore,
  CVProfileListItem,
  DashboardResponse,
  JDProfileListItem,
  RankingResponse,
  Recommendation,
  RequirementStatus,
  UserResponse
} from "@/lib/types";

const acceptedFiles = ".txt,.md,.pdf,.docx";
const tokenStorageKey = "cv_ranking_platform_token";

type ViewKey = "dashboard" | "new-ranking" | "analyses" | "jds" | "cvs";
type AuthMode = "login" | "register";

const navItems: Array<{ key: ViewKey; label: string; icon: LucideIcon }> = [
  { key: "dashboard", label: "Dashboard", icon: LayoutDashboard },
  { key: "new-ranking", label: "Phân tích mới", icon: SlidersHorizontal },
  { key: "analyses", label: "Các phân tích", icon: History },
  { key: "jds", label: "Hồ sơ JD", icon: BriefcaseBusiness },
  { key: "cvs", label: "Hồ sơ CV", icon: Users }
];

function recommendationLabel(value: Recommendation | string) {
  const labels: Record<string, string> = {
    strong_match: "Strong match",
    match: "Match",
    potential: "Potential",
    weak_match: "Weak match",
    not_match: "Not match"
  };
  return labels[value] ?? value;
}

function recommendationClass(value: Recommendation | string) {
  if (value === "strong_match" || value === "match") {
    return "border-emerald-200 bg-emerald-50 text-emerald-700";
  }
  if (value === "potential") {
    return "border-blue-200 bg-blue-50 text-blue-700";
  }
  if (value === "weak_match") {
    return "border-amber-200 bg-amber-50 text-amber-700";
  }
  return "border-rose-200 bg-rose-50 text-rose-700";
}

function statusClass(value: RequirementStatus) {
  if (value === "met") return "border-emerald-200 bg-emerald-50 text-emerald-700";
  if (value === "partial") return "border-amber-200 bg-amber-50 text-amber-700";
  return "border-rose-200 bg-rose-50 text-rose-700";
}

function scoreColor(score: number) {
  if (score >= 75) return "text-emerald-700";
  if (score >= 60) return "text-blue-700";
  if (score >= 40) return "text-amber-700";
  return "text-rose-700";
}

function formatFiles(files: File[]) {
  if (!files.length) return "No files selected";
  if (files.length === 1) return files[0].name;
  return `${files.length} files selected`;
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("vi-VN", {
    dateStyle: "medium",
    timeStyle: "short"
  }).format(new Date(value));
}

function formatPercent(value: number) {
  return `${Math.round(value * 100)}%`;
}

function downloadText(fileName: string, content: string, type: string) {
  const url = URL.createObjectURL(new Blob([content], { type }));
  const link = document.createElement("a");
  link.href = url;
  link.download = fileName;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function buildCsv(candidates: CandidateScore[]) {
  const header = ["rank", "candidate", "file", "score", "recommendation", "qualified", "missing_requirements"];
  const rows = candidates.map((candidate, index) => [
    index + 1,
    candidate.candidate_name,
    candidate.file_name,
    candidate.overall_score,
    recommendationLabel(candidate.recommendation),
    candidate.qualified ? "yes" : "no",
    candidate.missing_requirements.join("; ")
  ]);
  return [header, ...rows]
    .map((row) => row.map((value) => `"${String(value).replaceAll('"', '""')}"`).join(","))
    .join("\n");
}

function FilePicker({
  title,
  multiple,
  files,
  onChange
}: {
  title: string;
  multiple?: boolean;
  files: File[];
  onChange: (files: File[]) => void;
}) {
  return (
    <label className="panel flex min-h-28 cursor-pointer flex-col justify-between gap-4 p-4 transition hover:border-teal/50">
      <div className="flex items-center justify-between gap-3">
        <div className="flex min-w-0 items-center gap-3">
          <span className="inline-flex h-9 w-9 items-center justify-center rounded-md bg-teal/10 text-teal">
            <UploadCloud size={18} />
          </span>
          <div className="min-w-0">
            <div className="text-sm font-bold text-ink">{title}</div>
            <div className="text-xs text-muted">TXT, MD, PDF, DOCX</div>
          </div>
        </div>
        <span className="button-secondary h-9 shrink-0">Choose</span>
      </div>
      <div className="truncate text-sm font-medium text-ink">{formatFiles(files)}</div>
      <input
        className="sr-only"
        type="file"
        accept={acceptedFiles}
        multiple={multiple}
        onChange={(event) => onChange(Array.from(event.currentTarget.files ?? []))}
      />
    </label>
  );
}

function EmptyState({ title, text }: { title: string; text: string }) {
  return (
    <section className="panel p-6">
      <h2 className="text-lg font-bold text-ink">{title}</h2>
      <p className="mt-1 text-sm text-muted">{text}</p>
    </section>
  );
}

function MetricCard({
  title,
  value,
  detail,
  icon: Icon
}: {
  title: string;
  value: string | number;
  detail: string;
  icon: LucideIcon;
}) {
  return (
    <div className="panel p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-xs font-bold uppercase tracking-wide text-muted">{title}</div>
          <div className="mt-2 text-3xl font-bold text-ink">{value}</div>
          <div className="mt-1 text-xs text-muted">{detail}</div>
        </div>
        <span className="inline-flex h-10 w-10 items-center justify-center rounded-md bg-teal/10 text-teal">
          <Icon size={19} />
        </span>
      </div>
    </div>
  );
}

function HorizontalBars({
  title,
  data,
  labelMap
}: {
  title: string;
  data: Record<string, number>;
  labelMap?: Record<string, string>;
}) {
  const entries = Object.entries(data).filter(([, value]) => value > 0);
  const max = Math.max(1, ...entries.map(([, value]) => value));

  return (
    <section className="panel p-4">
      <h3 className="font-bold text-ink">{title}</h3>
      <div className="mt-4 space-y-3">
        {entries.length ? (
          entries.map(([key, value]) => (
            <div key={key}>
              <div className="mb-1 flex items-center justify-between gap-3 text-sm">
                <span className="font-medium text-ink">{labelMap?.[key] ?? recommendationLabel(key)}</span>
                <span className="text-muted">{value}</span>
              </div>
              <div className="h-2 rounded-full bg-slate-100">
                <div className="h-2 rounded-full bg-teal" style={{ width: `${Math.max(8, (value / max) * 100)}%` }} />
              </div>
            </div>
          ))
        ) : (
          <div className="text-sm text-muted">Chưa có dữ liệu.</div>
        )}
      </div>
    </section>
  );
}

function JobProfilePanel({ data }: { data: RankingResponse }) {
  const job = data.job_profile;
  return (
    <section className="panel p-4">
      <div className="mb-4 flex items-center gap-2">
        <BriefcaseBusiness size={18} className="text-teal" />
        <h2 className="text-lg font-bold text-ink">Job profile</h2>
      </div>
      <div className="grid gap-4 lg:grid-cols-[1fr_1fr_0.8fr]">
        <div>
          <div className="text-xs font-bold uppercase tracking-wide text-muted">Role</div>
          <div className="mt-1 text-base font-semibold text-ink">{job.title}</div>
          <div className="mt-3 flex flex-wrap gap-2">
            {job.required_skills.map((skill) => (
              <span key={skill} className="status-pill border-teal/20 bg-teal/10 text-teal">
                {skill}
              </span>
            ))}
          </div>
        </div>
        <div>
          <div className="text-xs font-bold uppercase tracking-wide text-muted">Must-have from JD</div>
          <ul className="mt-2 space-y-1.5 text-sm text-ink">
            {job.must_have_requirements.map((item) => (
              <li key={item} className="break-words">
                {item}
              </li>
            ))}
          </ul>
        </div>
        <div>
          <div className="text-xs font-bold uppercase tracking-wide text-muted">Preferred</div>
          <ul className="mt-2 space-y-1.5 text-sm text-ink">
            {job.nice_to_have_requirements.length ? (
              job.nice_to_have_requirements.map((item) => (
                <li key={item} className="break-words">
                  {item}
                </li>
              ))
            ) : (
              <li className="text-muted">None detected</li>
            )}
          </ul>
        </div>
      </div>
    </section>
  );
}

function RankingTable({
  candidates,
  selectedIndex,
  onSelect
}: {
  candidates: CandidateScore[];
  selectedIndex: number;
  onSelect: (index: number) => void;
}) {
  return (
    <section className="panel overflow-hidden">
      <div className="flex items-center justify-between gap-3 border-b border-line px-4 py-3">
        <div className="flex items-center gap-2">
          <BarChart3 size={18} className="text-teal" />
          <h2 className="text-lg font-bold text-ink">Candidate ranking</h2>
        </div>
        <button
          className="button-secondary"
          onClick={() => downloadText("candidate-ranking.csv", buildCsv(candidates), "text/csv")}
          type="button"
        >
          <Download size={16} />
          CSV
        </button>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[820px] text-left text-sm">
          <thead className="bg-slate-50 text-xs uppercase tracking-wide text-muted">
            <tr>
              <th className="px-4 py-3">Rank</th>
              <th className="px-4 py-3">Candidate</th>
              <th className="px-4 py-3">Score</th>
              <th className="px-4 py-3">Recommendation</th>
              <th className="px-4 py-3">Qualified</th>
              <th className="px-4 py-3">Risk</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {candidates.map((candidate, index) => (
              <tr
                key={`${candidate.file_name}-${candidate.candidate_name}`}
                className={index === selectedIndex ? "bg-teal/5" : "bg-white"}
              >
                <td className="px-4 py-3 font-bold text-ink">#{index + 1}</td>
                <td className="px-4 py-3">
                  <button
                    className="text-left font-semibold text-ink hover:text-teal"
                    onClick={() => onSelect(index)}
                    type="button"
                  >
                    {candidate.candidate_name}
                  </button>
                  <div className="max-w-[280px] truncate text-xs text-muted">{candidate.file_name}</div>
                </td>
                <td className={`px-4 py-3 text-lg font-bold ${scoreColor(candidate.overall_score)}`}>
                  {candidate.overall_score.toFixed(1)}
                </td>
                <td className="px-4 py-3">
                  <span className={`status-pill ${recommendationClass(candidate.recommendation)}`}>
                    {recommendationLabel(candidate.recommendation)}
                  </span>
                </td>
                <td className="px-4 py-3">
                  {candidate.qualified ? (
                    <span className="inline-flex items-center gap-1 text-emerald-700">
                      <CheckCircle2 size={16} /> Yes
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1 text-rose-700">
                      <XCircle size={16} /> Review
                    </span>
                  )}
                </td>
                <td className="max-w-[320px] px-4 py-3 text-muted">
                  <span className="line-clamp-2">{candidate.risks[0] ?? "No major risk detected"}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function CandidateDetail({ candidate }: { candidate: CandidateScore }) {
  return (
    <section className="space-y-4">
      <div className="panel overflow-hidden">
        <div className="border-b border-line px-4 py-3">
          <h2 className="text-lg font-bold text-ink">{candidate.candidate_name}</h2>
          <p className="mt-1 text-sm text-muted">{candidate.summary}</p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[760px] text-left text-sm">
            <thead className="bg-slate-50 text-xs uppercase tracking-wide text-muted">
              <tr>
                <th className="px-4 py-3">Criterion</th>
                <th className="px-4 py-3">Points</th>
                <th className="px-4 py-3">Reason</th>
                <th className="px-4 py-3">Evidence</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {candidate.criterion_scores.map((score) => (
                <tr key={score.name}>
                  <td className="px-4 py-3 font-semibold text-ink">{score.name}</td>
                  <td className="whitespace-nowrap px-4 py-3 font-bold text-ink">
                    {score.awarded_points}/{score.max_points}
                  </td>
                  <td className="px-4 py-3 text-muted">{score.reason}</td>
                  <td className="px-4 py-3 text-muted">{score.evidence[0] ?? "No direct evidence"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="panel p-4">
        <div className="mb-3 flex items-center gap-2">
          <ShieldCheck size={18} className="text-teal" />
          <h3 className="font-bold text-ink">Must-have checks</h3>
        </div>
        <div className="grid gap-3 md:grid-cols-2">
          {candidate.must_have_checks.map((check) => (
            <div key={check.requirement} className="rounded-md border border-line p-3">
              <div className="flex items-center justify-between gap-3">
                <span className="text-sm font-semibold text-ink">{check.requirement}</span>
                <span className={`status-pill ${statusClass(check.status)}`}>{check.status}</span>
              </div>
              <div className="mt-2 text-sm text-muted">{check.evidence || "No direct evidence"}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function RankingResults({
  ranking,
  selectedIndex,
  onSelectCandidate
}: {
  ranking: RankingResponse;
  selectedIndex: number;
  onSelectCandidate: (index: number) => void;
}) {
  const selectedCandidate = ranking.candidates[selectedIndex] ?? ranking.candidates[0] ?? null;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <span className="status-pill border-teal/20 bg-teal/10 text-teal">Engine: {ranking.engine}</span>
        {ranking.model ? (
          <span className="status-pill border-blue-200 bg-blue-50 text-blue-700">Model: {ranking.model}</span>
        ) : null}
        <span className="status-pill border-slate-200 bg-slate-50 text-muted">
          Generated: {formatDate(ranking.generated_at)}
        </span>
      </div>
      <JobProfilePanel data={ranking} />
      <RankingTable candidates={ranking.candidates} selectedIndex={selectedIndex} onSelect={onSelectCandidate} />
      {selectedCandidate ? <CandidateDetail candidate={selectedCandidate} /> : null}
      {selectedCandidate ? (
        <section className="grid gap-4 lg:grid-cols-2">
          <div className="panel p-4">
            <div className="mb-3 flex items-center gap-2">
              <AlertTriangle size={18} className="text-coral" />
              <h3 className="font-bold text-ink">Risks</h3>
            </div>
            <ul className="space-y-2 text-sm text-muted">
              {(selectedCandidate.risks.length ? selectedCandidate.risks : ["No major risk detected"]).map((item) => (
                <li key={item} className="break-words">
                  {item}
                </li>
              ))}
            </ul>
          </div>
          <div className="panel p-4">
            <div className="mb-3 flex items-center gap-2">
              <FileText size={18} className="text-teal" />
              <h3 className="font-bold text-ink">Interview questions</h3>
            </div>
            <ul className="space-y-2 text-sm text-muted">
              {selectedCandidate.interview_questions.map((item) => (
                <li key={item} className="break-words">
                  {item}
                </li>
              ))}
            </ul>
          </div>
        </section>
      ) : null}
      <section className="panel overflow-hidden">
        <div className="flex items-center justify-between gap-3 border-b border-line px-4 py-3">
          <h2 className="font-bold text-ink">Structured JSON</h2>
          <button
            className="button-secondary"
            onClick={() => downloadText("ranking-result.json", JSON.stringify(ranking, null, 2), "application/json")}
            type="button"
          >
            <Download size={16} />
            JSON
          </button>
        </div>
        <pre className="max-h-[620px] overflow-auto p-4 text-xs leading-relaxed text-ink">
          {JSON.stringify(ranking, null, 2)}
        </pre>
      </section>
    </div>
  );
}

function AuthView({ onAuthenticated }: { onAuthenticated: (auth: AuthResponse) => void }) {
  const [mode, setMode] = useState<AuthMode>("login");
  const [fullName, setFullName] = useState("HR Manager");
  const [email, setEmail] = useState("demo@company.com");
  const [password, setPassword] = useState("demo1234");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsLoading(true);
    setError(null);
    try {
      const response =
        mode === "login"
          ? await login({ email, password })
          : await register({ email, password, full_name: fullName });
      onAuthenticated(response);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Authentication failed.");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center px-4 py-8">
      <section className="panel w-full max-w-md p-6">
        <div className="flex items-center gap-3">
          <span className="inline-flex h-11 w-11 items-center justify-center rounded-md bg-teal text-white">
            <ShieldCheck size={22} />
          </span>
          <div>
            <div className="text-sm font-bold text-teal">CV Ranking Platform</div>
            <h1 className="text-2xl font-bold text-ink">{mode === "login" ? "Đăng nhập" : "Đăng ký"}</h1>
          </div>
        </div>

        <div className="mt-6 grid grid-cols-2 rounded-md border border-line bg-slate-50 p-1">
          {(["login", "register"] as AuthMode[]).map((item) => (
            <button
              key={item}
              className={`focus-ring h-9 rounded text-sm font-bold ${
                mode === item ? "bg-white text-teal shadow-sm" : "text-muted hover:text-ink"
              }`}
              onClick={() => setMode(item)}
              type="button"
            >
              {item === "login" ? "Đăng nhập" : "Đăng ký"}
            </button>
          ))}
        </div>

        <form className="mt-5 space-y-4" onSubmit={handleSubmit}>
          {mode === "register" ? (
            <label className="block">
              <span className="text-xs font-bold uppercase tracking-wide text-muted">Full name</span>
              <div className="mt-1 flex items-center gap-2 rounded-md border border-line bg-white px-3">
                <UserPlus size={16} className="text-muted" />
                <input
                  className="focus-ring h-10 w-full border-0 bg-transparent text-sm text-ink outline-none"
                  onChange={(event) => setFullName(event.target.value)}
                  value={fullName}
                />
              </div>
            </label>
          ) : null}

          <label className="block">
            <span className="text-xs font-bold uppercase tracking-wide text-muted">Email</span>
            <div className="mt-1 flex items-center gap-2 rounded-md border border-line bg-white px-3">
              <Mail size={16} className="text-muted" />
              <input
                className="focus-ring h-10 w-full border-0 bg-transparent text-sm text-ink outline-none"
                onChange={(event) => setEmail(event.target.value)}
                type="email"
                value={email}
              />
            </div>
          </label>

          <label className="block">
            <span className="text-xs font-bold uppercase tracking-wide text-muted">Password</span>
            <div className="mt-1 flex items-center gap-2 rounded-md border border-line bg-white px-3">
              <LockKeyhole size={16} className="text-muted" />
              <input
                className="focus-ring h-10 w-full border-0 bg-transparent text-sm text-ink outline-none"
                onChange={(event) => setPassword(event.target.value)}
                type="password"
                value={password}
              />
            </div>
          </label>

          {error ? (
            <div className="rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-sm font-semibold text-rose-700">
              {error}
            </div>
          ) : null}

          <button className="button-primary w-full" disabled={isLoading} type="submit">
            {isLoading ? <RefreshCw className="animate-spin" size={16} /> : <ShieldCheck size={16} />}
            {mode === "login" ? "Đăng nhập" : "Tạo tài khoản"}
          </button>
        </form>
      </section>
    </main>
  );
}

function DashboardView({
  dashboard,
  isLoading,
  onOpenAnalysis
}: {
  dashboard: DashboardResponse | null;
  isLoading: boolean;
  onOpenAnalysis: (analysisId: string) => void;
}) {
  if (!dashboard) {
    return <EmptyState title={isLoading ? "Đang tải dashboard" : "Chưa có dữ liệu"} text="Chạy một phân tích để tạo dữ liệu dashboard." />;
  }

  return (
    <div className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard title="Analyses" value={dashboard.total_analyses} detail="Lượt ranking đã hoàn tất" icon={History} />
        <MetricCard title="Candidates" value={dashboard.total_candidates} detail="CV đã được chấm" icon={Users} />
        <MetricCard title="Qualified rate" value={formatPercent(dashboard.qualified_rate)} detail="Ứng viên qua ngưỡng" icon={CheckCircle2} />
        <MetricCard title="Avg score" value={dashboard.average_score.toFixed(1)} detail="Điểm trung bình toàn hệ thống" icon={BarChart3} />
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard title="JD profiles" value={dashboard.total_jds} detail="JD đã upload" icon={BriefcaseBusiness} />
        <MetricCard title="CV profiles" value={dashboard.total_cvs} detail="CV đã upload" icon={FileText} />
        <MetricCard title="Engine OpenAI" value={dashboard.engine_counts.openai ?? 0} detail="Phân tích dùng LLM" icon={ShieldCheck} />
        <MetricCard title="Engine heuristic" value={dashboard.engine_counts.heuristic ?? 0} detail="Phân tích demo/offline" icon={Database} />
      </div>

      <div className="grid gap-4 xl:grid-cols-3">
        <HorizontalBars title="Score distribution" data={dashboard.score_buckets} />
        <HorizontalBars title="Recommendation mix" data={dashboard.recommendation_counts} />
        <HorizontalBars
          title="Engine usage"
          data={dashboard.engine_counts}
          labelMap={{ openai: "OpenAI", heuristic: "Heuristic" }}
        />
      </div>

      <section className="panel overflow-hidden">
        <div className="border-b border-line px-4 py-3">
          <h2 className="font-bold text-ink">Recent analyses</h2>
        </div>
        {dashboard.recent_analyses.length ? (
          <div className="divide-y divide-line">
            {dashboard.recent_analyses.map((analysis) => (
              <button
                key={analysis.id}
                className="flex w-full flex-col gap-2 px-4 py-3 text-left transition hover:bg-slate-50 md:flex-row md:items-center md:justify-between"
                onClick={() => onOpenAnalysis(analysis.id)}
                type="button"
              >
                <div>
                  <div className="font-semibold text-ink">{analysis.title}</div>
                  <div className="text-sm text-muted">{formatDate(analysis.created_at)}</div>
                </div>
                <div className="flex flex-wrap gap-2">
                  <span className="status-pill border-slate-200 bg-slate-50 text-muted">{analysis.candidate_count} CVs</span>
                  <span className="status-pill border-teal/20 bg-teal/10 text-teal">
                    Avg {analysis.average_score.toFixed(1)}
                  </span>
                </div>
              </button>
            ))}
          </div>
        ) : (
          <div className="p-4 text-sm text-muted">Chưa có phân tích nào.</div>
        )}
      </section>
    </div>
  );
}

function NewRankingView({
  ranking,
  selectedIndex,
  onSelectCandidate,
  onRank,
  isLoading,
  error
}: {
  ranking: RankingResponse | null;
  selectedIndex: number;
  onSelectCandidate: (index: number) => void;
  onRank: (input: {
    jdFiles: File[];
    cvFiles: File[];
    engine: RankingEngine;
    model: string;
    analysisTitle: string;
  }) => void;
  isLoading: boolean;
  error: string | null;
}) {
  const [jdFiles, setJdFiles] = useState<File[]>([]);
  const [cvFiles, setCvFiles] = useState<File[]>([]);
  const [analysisTitle, setAnalysisTitle] = useState("Backend Engineer Screening");
  const [engine, setEngine] = useState<RankingEngine>("openai");
  const [model, setModel] = useState("gpt-5-mini");

  const stats = useMemo(() => {
    const candidates = ranking?.candidates ?? [];
    const qualified = candidates.filter((candidate) => candidate.qualified).length;
    const average = candidates.length
      ? candidates.reduce((sum, candidate) => sum + candidate.overall_score, 0) / candidates.length
      : 0;
    return { total: candidates.length, qualified, average };
  }, [ranking]);

  return (
    <div className="space-y-4">
      <section className="grid gap-4 lg:grid-cols-[0.85fr_1.15fr_0.85fr] lg:items-stretch">
        <div className="panel p-4">
          <label className="block">
            <span className="text-xs font-bold uppercase tracking-wide text-muted">Analysis title</span>
            <input
              className="focus-ring mt-2 h-10 w-full rounded-md border border-line px-3 text-sm text-ink"
              onChange={(event) => setAnalysisTitle(event.target.value)}
              value={analysisTitle}
            />
          </label>
          <div className="mt-4 grid grid-cols-3 gap-2">
            <div className="rounded-md border border-line bg-slate-50 px-3 py-2">
              <div className="text-xs font-bold uppercase text-muted">CVs</div>
              <div className="text-xl font-bold text-ink">{stats.total}</div>
            </div>
            <div className="rounded-md border border-line bg-slate-50 px-3 py-2">
              <div className="text-xs font-bold uppercase text-muted">Qualified</div>
              <div className="text-xl font-bold text-teal">{stats.qualified}</div>
            </div>
            <div className="rounded-md border border-line bg-slate-50 px-3 py-2">
              <div className="text-xs font-bold uppercase text-muted">Avg</div>
              <div className="text-xl font-bold text-ink">{stats.average.toFixed(1)}</div>
            </div>
          </div>
        </div>

        <div className="grid gap-4">
          <FilePicker title="Upload JD" files={jdFiles} onChange={(files) => setJdFiles(files.slice(0, 1))} />
          <FilePicker title="Upload CVs" files={cvFiles} multiple onChange={setCvFiles} />
        </div>

        <div className="panel flex flex-col justify-between gap-3 p-4">
          <div>
            <div className="text-sm font-bold text-ink">Run ranking</div>
            <div className="mt-1 text-xs text-muted">FastAPI + {engine === "openai" ? "OpenAI structured output" : "heuristic scorer"}</div>
            <div className="mt-3 grid grid-cols-2 rounded-md border border-line bg-slate-50 p-1">
              {(["openai", "heuristic"] as RankingEngine[]).map((item) => (
                <button
                  key={item}
                  className={`focus-ring h-8 rounded text-xs font-bold ${
                    engine === item ? "bg-white text-teal shadow-sm" : "text-muted hover:text-ink"
                  }`}
                  onClick={() => setEngine(item)}
                  type="button"
                >
                  {item === "openai" ? "OpenAI" : "Heuristic"}
                </button>
              ))}
            </div>
            <input
              className="focus-ring mt-3 h-9 w-full rounded-md border border-line px-3 text-sm text-ink disabled:bg-slate-100 disabled:text-muted"
              disabled={engine !== "openai"}
              onChange={(event) => setModel(event.target.value)}
              value={model}
            />
          </div>
          <button
            className="button-primary w-full"
            disabled={isLoading}
            onClick={() => onRank({ jdFiles, cvFiles, engine, model, analysisTitle })}
            type="button"
          >
            {isLoading ? <RefreshCw className="animate-spin" size={16} /> : <BarChart3 size={16} />}
            {isLoading ? "Ranking" : "Rank CVs"}
          </button>
        </div>
      </section>

      {error ? (
        <div className="panel flex items-start gap-3 border-rose-200 bg-rose-50 p-4 text-rose-700">
          <AlertTriangle size={18} className="mt-0.5" />
          <div className="text-sm font-semibold">{error}</div>
        </div>
      ) : null}

      {ranking ? (
        <RankingResults ranking={ranking} selectedIndex={selectedIndex} onSelectCandidate={onSelectCandidate} />
      ) : (
        <EmptyState title="No ranking yet" text="Upload một JD và danh sách CV, sau đó chạy ranking." />
      )}
    </div>
  );
}

function AnalysesView({
  analyses,
  selectedAnalysis,
  isDetailLoading,
  selectedIndex,
  onOpenAnalysis,
  onSelectCandidate
}: {
  analyses: AnalysisListItem[];
  selectedAnalysis: AnalysisDetail | null;
  isDetailLoading: boolean;
  selectedIndex: number;
  onOpenAnalysis: (analysisId: string) => void;
  onSelectCandidate: (index: number) => void;
}) {
  return (
    <div className="space-y-4">
      <section className="panel overflow-hidden">
        <div className="border-b border-line px-4 py-3">
          <h2 className="font-bold text-ink">Các phân tích</h2>
        </div>
        {analyses.length ? (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[820px] text-left text-sm">
              <thead className="bg-slate-50 text-xs uppercase tracking-wide text-muted">
                <tr>
                  <th className="px-4 py-3">Title</th>
                  <th className="px-4 py-3">Engine</th>
                  <th className="px-4 py-3">CVs</th>
                  <th className="px-4 py-3">Qualified</th>
                  <th className="px-4 py-3">Avg score</th>
                  <th className="px-4 py-3">Created</th>
                  <th className="px-4 py-3">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {analyses.map((analysis) => (
                  <tr key={analysis.id}>
                    <td className="px-4 py-3 font-semibold text-ink">{analysis.title}</td>
                    <td className="px-4 py-3 text-muted">{analysis.engine}</td>
                    <td className="px-4 py-3 text-muted">{analysis.candidate_count}</td>
                    <td className="px-4 py-3 text-muted">{analysis.qualified_count}</td>
                    <td className="px-4 py-3 font-bold text-ink">{analysis.average_score.toFixed(1)}</td>
                    <td className="px-4 py-3 text-muted">{formatDate(analysis.created_at)}</td>
                    <td className="px-4 py-3">
                      <button className="button-secondary h-9" onClick={() => onOpenAnalysis(analysis.id)} type="button">
                        Open
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="p-4 text-sm text-muted">Chưa có phân tích nào.</div>
        )}
      </section>

      {isDetailLoading ? (
        <div className="panel flex items-center gap-2 p-4 text-sm font-semibold text-muted">
          <RefreshCw className="animate-spin" size={16} />
          Đang tải chi tiết phân tích
        </div>
      ) : null}

      {selectedAnalysis ? (
        <RankingResults
          ranking={selectedAnalysis.result}
          selectedIndex={selectedIndex}
          onSelectCandidate={onSelectCandidate}
        />
      ) : null}
    </div>
  );
}

function JDLibraryView({ profiles }: { profiles: JDProfileListItem[] }) {
  return (
    <section className="panel overflow-hidden">
      <div className="border-b border-line px-4 py-3">
        <h2 className="font-bold text-ink">Quản lý hồ sơ JD</h2>
      </div>
      {profiles.length ? (
        <div className="grid gap-4 p-4 xl:grid-cols-2">
          {profiles.map((profile) => (
            <article key={profile.id} className="rounded-md border border-line bg-white p-4">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <h3 className="font-bold text-ink">{profile.title}</h3>
                  <p className="mt-1 text-sm text-muted">{profile.file_name}</p>
                </div>
                <span className="status-pill border-teal/20 bg-teal/10 text-teal">{profile.must_have_count} must-have</span>
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                {profile.required_skills.length ? (
                  profile.required_skills.slice(0, 8).map((skill) => (
                    <span key={skill} className="status-pill border-slate-200 bg-slate-50 text-muted">
                      {skill}
                    </span>
                  ))
                ) : (
                  <span className="text-sm text-muted">No skill detected</span>
                )}
              </div>
              <div className="mt-3 text-xs font-semibold uppercase tracking-wide text-muted">{formatDate(profile.created_at)}</div>
            </article>
          ))}
        </div>
      ) : (
        <div className="p-4 text-sm text-muted">JD upload trong phân tích mới sẽ xuất hiện tại đây.</div>
      )}
    </section>
  );
}

function CVLibraryView({ profiles }: { profiles: CVProfileListItem[] }) {
  return (
    <section className="panel overflow-hidden">
      <div className="border-b border-line px-4 py-3">
        <h2 className="font-bold text-ink">Quản lý hồ sơ CV</h2>
      </div>
      {profiles.length ? (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[720px] text-left text-sm">
            <thead className="bg-slate-50 text-xs uppercase tracking-wide text-muted">
              <tr>
                <th className="px-4 py-3">Candidate</th>
                <th className="px-4 py-3">File</th>
                <th className="px-4 py-3">Uploaded</th>
                <th className="px-4 py-3">Storage</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {profiles.map((profile) => (
                <tr key={profile.id}>
                  <td className="px-4 py-3 font-semibold text-ink">{profile.candidate_name}</td>
                  <td className="px-4 py-3 text-muted">{profile.file_name}</td>
                  <td className="px-4 py-3 text-muted">{formatDate(profile.created_at)}</td>
                  <td className="px-4 py-3">
                    <span className="status-pill border-slate-200 bg-slate-50 text-muted">Database text</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="p-4 text-sm text-muted">CV upload trong phân tích mới sẽ xuất hiện tại đây.</div>
      )}
    </section>
  );
}

export default function Home() {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<UserResponse | null>(null);
  const [activeView, setActiveView] = useState<ViewKey>("dashboard");
  const [isBooting, setIsBooting] = useState(true);
  const [isWorkspaceLoading, setIsWorkspaceLoading] = useState(false);
  const [workspaceError, setWorkspaceError] = useState<string | null>(null);

  const [dashboard, setDashboard] = useState<DashboardResponse | null>(null);
  const [analyses, setAnalyses] = useState<AnalysisListItem[]>([]);
  const [jdProfiles, setJDProfiles] = useState<JDProfileListItem[]>([]);
  const [cvProfiles, setCVProfiles] = useState<CVProfileListItem[]>([]);
  const [selectedAnalysis, setSelectedAnalysis] = useState<AnalysisDetail | null>(null);
  const [isDetailLoading, setIsDetailLoading] = useState(false);

  const [ranking, setRanking] = useState<RankingResponse | null>(null);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [isRanking, setIsRanking] = useState(false);
  const [rankingError, setRankingError] = useState<string | null>(null);

  const pageTitle = useMemo(() => {
    return navItems.find((item) => item.key === activeView)?.label ?? "Dashboard";
  }, [activeView]);

  const loadWorkspace = useCallback(async (activeToken: string) => {
    setIsWorkspaceLoading(true);
    setWorkspaceError(null);
    try {
      const [dashboardData, analysesData, jdData, cvData] = await Promise.all([
        fetchDashboard(activeToken),
        fetchAnalyses(activeToken),
        fetchJDProfiles(activeToken),
        fetchCVProfiles(activeToken)
      ]);
      setDashboard(dashboardData);
      setAnalyses(analysesData);
      setJDProfiles(jdData);
      setCVProfiles(cvData);
    } catch (requestError) {
      setWorkspaceError(requestError instanceof Error ? requestError.message : "Could not load workspace data.");
    } finally {
      setIsWorkspaceLoading(false);
    }
  }, []);

  useEffect(() => {
    const storedToken = window.localStorage.getItem(tokenStorageKey);
    if (!storedToken) {
      setIsBooting(false);
      return;
    }

    fetchMe(storedToken)
      .then((profile) => {
        setToken(storedToken);
        setUser(profile);
      })
      .catch(() => {
        window.localStorage.removeItem(tokenStorageKey);
      })
      .finally(() => setIsBooting(false));
  }, []);

  useEffect(() => {
    if (token) {
      void loadWorkspace(token);
    }
  }, [loadWorkspace, token]);

  function handleAuthenticated(auth: AuthResponse) {
    window.localStorage.setItem(tokenStorageKey, auth.access_token);
    setToken(auth.access_token);
    setUser(auth.user);
    setActiveView("dashboard");
  }

  function handleLogout() {
    window.localStorage.removeItem(tokenStorageKey);
    setToken(null);
    setUser(null);
    setDashboard(null);
    setAnalyses([]);
    setJDProfiles([]);
    setCVProfiles([]);
    setSelectedAnalysis(null);
    setRanking(null);
    setSelectedIndex(0);
  }

  async function handleOpenAnalysis(analysisId: string) {
    if (!token) return;
    setActiveView("analyses");
    setIsDetailLoading(true);
    setWorkspaceError(null);
    try {
      const detail = await fetchAnalysis(token, analysisId);
      setSelectedAnalysis(detail);
      setSelectedIndex(0);
    } catch (requestError) {
      setWorkspaceError(requestError instanceof Error ? requestError.message : "Could not load analysis detail.");
    } finally {
      setIsDetailLoading(false);
    }
  }

  async function handleRank(input: {
    jdFiles: File[];
    cvFiles: File[];
    engine: RankingEngine;
    model: string;
    analysisTitle: string;
  }) {
    if (!token) return;

    const jd = input.jdFiles[0];
    if (!jd || !input.cvFiles.length) {
      setRankingError("Upload one JD and at least one CV.");
      return;
    }

    setIsRanking(true);
    setRankingError(null);
    try {
      const response = await rankCandidates({
        token,
        jd,
        cvs: input.cvFiles,
        engine: input.engine,
        model: input.engine === "openai" ? input.model : undefined,
        analysisTitle: input.analysisTitle || undefined
      });
      setRanking(response);
      setSelectedAnalysis(null);
      setSelectedIndex(0);
      void loadWorkspace(token);
    } catch (requestError) {
      setRanking(null);
      setRankingError(requestError instanceof Error ? requestError.message : "Could not rank candidates.");
    } finally {
      setIsRanking(false);
    }
  }

  if (isBooting) {
    return (
      <main className="flex min-h-screen items-center justify-center">
        <div className="panel flex items-center gap-3 p-4 text-sm font-semibold text-muted">
          <RefreshCw className="animate-spin" size={16} />
          Loading workspace
        </div>
      </main>
    );
  }

  if (!token || !user) {
    return <AuthView onAuthenticated={handleAuthenticated} />;
  }

  return (
    <div className="min-h-screen bg-canvas">
      <div className="mx-auto flex w-full max-w-[1500px] flex-col gap-4 px-4 py-4 lg:flex-row lg:gap-6 lg:px-6">
        <aside className="panel h-fit shrink-0 p-3 lg:sticky lg:top-4 lg:w-64">
          <div className="flex items-center gap-3 px-2 py-2">
            <span className="inline-flex h-10 w-10 items-center justify-center rounded-md bg-teal text-white">
              <ShieldCheck size={21} />
            </span>
            <div>
              <div className="text-sm font-bold text-ink">CV Ranker</div>
              <div className="text-xs text-muted">Recruiting workspace</div>
            </div>
          </div>

          <nav className="mt-4 grid gap-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const active = activeView === item.key;
              return (
                <button
                  key={item.key}
                  className={`focus-ring flex h-10 items-center gap-3 rounded-md px-3 text-left text-sm font-semibold transition ${
                    active ? "bg-teal text-white" : "text-muted hover:bg-slate-50 hover:text-ink"
                  }`}
                  onClick={() => setActiveView(item.key)}
                  type="button"
                >
                  <Icon size={17} />
                  {item.label}
                </button>
              );
            })}
          </nav>

          <div className="mt-5 rounded-md border border-line bg-slate-50 p-3">
            <div className="text-sm font-bold text-ink">{user.full_name}</div>
            <div className="mt-1 truncate text-xs text-muted">{user.email}</div>
            <button className="button-secondary mt-3 h-9 w-full" onClick={handleLogout} type="button">
              <LogOut size={15} />
              Logout
            </button>
          </div>
        </aside>

        <main className="min-w-0 flex-1 space-y-4 pb-8">
          <header className="flex flex-col gap-3 border-b border-line pb-4 md:flex-row md:items-end md:justify-between">
            <div>
              <div className="flex items-center gap-2 text-sm font-bold text-teal">
                <SlidersHorizontal size={16} />
                CV Ranking Platform
              </div>
              <h1 className="mt-2 text-3xl font-bold tracking-normal text-ink">{pageTitle}</h1>
            </div>
            <button
              className="button-secondary w-fit"
              disabled={isWorkspaceLoading}
              onClick={() => token && loadWorkspace(token)}
              type="button"
            >
              <RefreshCw className={isWorkspaceLoading ? "animate-spin" : ""} size={16} />
              Refresh
            </button>
          </header>

          {workspaceError ? (
            <div className="panel flex items-start gap-3 border-rose-200 bg-rose-50 p-4 text-rose-700">
              <AlertTriangle size={18} className="mt-0.5" />
              <div className="text-sm font-semibold">{workspaceError}</div>
            </div>
          ) : null}

          {activeView === "dashboard" ? (
            <DashboardView dashboard={dashboard} isLoading={isWorkspaceLoading} onOpenAnalysis={handleOpenAnalysis} />
          ) : null}

          {activeView === "new-ranking" ? (
            <NewRankingView
              ranking={ranking}
              selectedIndex={selectedIndex}
              onSelectCandidate={setSelectedIndex}
              onRank={handleRank}
              isLoading={isRanking}
              error={rankingError}
            />
          ) : null}

          {activeView === "analyses" ? (
            <AnalysesView
              analyses={analyses}
              selectedAnalysis={selectedAnalysis}
              isDetailLoading={isDetailLoading}
              selectedIndex={selectedIndex}
              onOpenAnalysis={handleOpenAnalysis}
              onSelectCandidate={setSelectedIndex}
            />
          ) : null}

          {activeView === "jds" ? <JDLibraryView profiles={jdProfiles} /> : null}

          {activeView === "cvs" ? <CVLibraryView profiles={cvProfiles} /> : null}
        </main>
      </div>
    </div>
  );
}
