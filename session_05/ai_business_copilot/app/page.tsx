"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  AlertTriangle, ArrowUpRight, BarChart3, Bell, Bot, BriefcaseBusiness, CalendarDays, CheckCircle2, ChevronRight,
  CircleDollarSign, Clock3, Command, Eye, EyeOff, LayoutDashboard, ListTodo, Loader2, LockKeyhole, LogOut, Menu, MessageSquareText,
  Search, Send, ShieldCheck, Sparkles, Target, TrendingUp, UserRound, UsersRound, X,
} from "lucide-react";
import { api } from "@/lib/api";
import { AuditLog, BusinessTask, CopilotResponse, Customer, DashboardMetrics, NotificationItem, OperationsReport, SessionUser, TaskStatus, View, Visualization } from "@/lib/types";
import { Bar, BarChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

const money = (value: number) => new Intl.NumberFormat("vi-VN", { notation: "compact", maximumFractionDigits: 1 }).format(value) + " ₫";
const fullMoney = (value: number) => new Intl.NumberFormat("vi-VN").format(value) + " ₫";
const statusLabel = { active: "Đang hoạt động", at_risk: "Cần chú ý", lead: "Tiềm năng" };
const statusClass = { active: "pill green", at_risk: "pill amber", lead: "pill blue" };

const demoMetrics: DashboardMetrics = { revenue: 1_050_000_000, active_customers: 2, at_risk_customers: 2, open_tasks: 4, overdue_tasks: 1, pipeline_value: 1_680_000_000 };

export default function Home() {
  const [session, setSession] = useState<SessionUser | null | undefined>(undefined);
  const [view, setView] = useState<View>("overview");
  const [metrics, setMetrics] = useState<DashboardMetrics>(demoMetrics);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [tasks, setTasks] = useState<BusinessTask[]>([]);
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [report, setReport] = useState<OperationsReport>();
  const [audits, setAudits] = useState<AuditLog[]>([]);
  const [mobileNav, setMobileNav] = useState(false);
  const [connected, setConnected] = useState(true);

  const loadData = useCallback(async () => {
    try {
      const auditRequest = session && ["admin", "manager"].includes(session.role) ? api.auditLogs() : Promise.resolve([]);
      const [metricData, customerData, taskData, notificationData, reportData, auditData] = await Promise.all([api.dashboard(), api.customers(), api.tasks(), api.notifications(), api.operationsReport(), auditRequest]);
      setMetrics(metricData); setCustomers(customerData); setTasks(taskData); setNotifications(notificationData); setReport(reportData); setAudits(auditData); setConnected(true);
    } catch { setConnected(false); }
  }, [session]);

  useEffect(() => { api.me().then(setSession).catch(() => setSession(null)); }, []);
  useEffect(() => { if (session) loadData(); }, [loadData, session]);

  const navigate = (next: View) => { setView(next); setMobileNav(false); };
  const titles = { overview: ["Tổng quan", "Theo dõi sức khỏe doanh nghiệp trong một màn hình."], customers: ["Khách hàng", "Quản lý quan hệ và phát hiện cơ hội tăng trưởng."], tasks: ["Công việc", "Điều phối ưu tiên của đội ngũ theo thời gian thực."], reports: ["Báo cáo", "Phân tích danh mục khách hàng và hiệu suất vận hành."], activity: ["Hoạt động", "Theo dõi thông báo và lịch sử thay đổi trong hệ thống."], copilot: ["AI Copilot", "Hỏi dữ liệu, tìm insight và đề xuất hành động."] };

  if (session === undefined) return <div className="auth-loading"><div className="brand-mark"><Command size={22}/></div><Loader2 className="spin" size={22}/></div>;
  if (session === null) return <LoginScreen onLogin={setSession}/>;

  return (
    <div className="app-shell">
      <Sidebar view={view} navigate={navigate} open={mobileNav} close={() => setMobileNav(false)} session={session} onLogout={async () => { await api.logout(); setSession(null); }} />
      <main className="main-content">
        <header className="topbar">
          <button className="icon-button mobile-menu" onClick={() => setMobileNav(true)} aria-label="Mở menu"><Menu size={20} /></button>
          <div><p className="eyebrow">ORBIT WORKSPACE</p><h1>{titles[view][0]}</h1><p className="subtitle">{titles[view][1]}</p></div>
          <div className="top-actions"><button className="search-button"><Search size={17} /><span>Tìm kiếm</span><kbd>⌘ K</kbd></button><div className="avatar">{session.full_name.split(" ").slice(-2).map(part => part[0]).join("").toUpperCase()}</div></div>
        </header>
        {!connected && <div className="offline-banner"><AlertTriangle size={16}/> Backend chưa kết nối — đang hiển thị giao diện demo. Chạy FastAPI ở cổng 8000.</div>}
        {view === "overview" && <Overview metrics={metrics} customers={customers} tasks={tasks} goCopilot={() => navigate("copilot")} />}
        {view === "customers" && <Customers customers={customers} />}
        {view === "tasks" && <Tasks tasks={tasks} setTasks={setTasks} />}
        {view === "reports" && <Reports report={report} />}
        {view === "activity" && <Activity notifications={notifications} audits={audits} />}
        {view === "copilot" && <Copilot canApprove={["admin", "manager"].includes(session.role)} onTaskCreated={(task) => setTasks(current => [...current, task])} />}
      </main>
    </div>
  );
}

function LoginScreen({ onLogin }: { onLogin: (user: SessionUser) => void }) {
  const [email, setEmail] = useState("admin@orbit.local");
  const [password, setPassword] = useState("Orbit@2026");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const submit = async (event: React.FormEvent) => {
    event.preventDefault(); setError(""); setLoading(true);
    try { onLogin(await api.login(email, password)); }
    catch { setError("Email hoặc mật khẩu không đúng."); }
    finally { setLoading(false); }
  };
  return <main className="login-page"><section className="login-brand"><div className="login-brand-content"><div className="brand login-logo"><div className="brand-mark"><Command size={21}/></div><div><strong>Orbit</strong><span>BUSINESS OS</span></div></div><span className="hero-kicker"><Sparkles size={14}/> AI BUSINESS COPILOT</span><h1>Điều hành doanh nghiệp<br/>trong một không gian.</h1><p>Theo dõi khách hàng, công việc, báo cáo và ra quyết định cùng AI Copilot.</p><div className="login-features"><span><CheckCircle2 size={16}/> Dữ liệu vận hành tập trung</span><span><CheckCircle2 size={16}/> Phân quyền theo vai trò</span><span><CheckCircle2 size={16}/> Hành động AI có phê duyệt</span></div></div><div className="login-orbit"><i/><i/><div><Bot size={34}/></div></div></section><section className="login-form-side"><form className="login-card" onSubmit={submit}><div className="login-lock"><LockKeyhole size={22}/></div><span className="eyebrow">WELCOME BACK</span><h2>Đăng nhập vào Orbit</h2><p>Sử dụng tài khoản được quản trị viên cung cấp.</p><label><span>Email công việc</span><input type="email" autoComplete="email" value={email} onChange={event => setEmail(event.target.value)} required/></label><label><span>Mật khẩu</span><div className="password-field"><input type={showPassword ? "text" : "password"} autoComplete="current-password" value={password} onChange={event => setPassword(event.target.value)} required/><button type="button" onClick={() => setShowPassword(value => !value)} aria-label={showPassword ? "Ẩn mật khẩu" : "Hiện mật khẩu"}>{showPassword ? <EyeOff size={17}/> : <Eye size={17}/>}</button></div></label>{error && <p className="login-error"><AlertTriangle size={15}/>{error}</p>}<button className="login-submit" disabled={loading}>{loading ? <Loader2 className="spin" size={18}/> : <LockKeyhole size={17}/>} Đăng nhập</button><div className="demo-accounts"><strong>Tài khoản demo</strong><span>admin@orbit.local · Orbit@2026</span><span>manager / sales / viewer @orbit.local dùng cùng mật khẩu</span></div></form></section></main>;
}

function Sidebar({ view, navigate, open, close, session, onLogout }: { view: View; navigate: (view: View) => void; open: boolean; close: () => void; session: SessionUser; onLogout: () => void }) {
  const items: { id: View; label: string; icon: typeof LayoutDashboard }[] = [
    { id: "overview", label: "Tổng quan", icon: LayoutDashboard }, { id: "customers", label: "Khách hàng", icon: UsersRound },
    { id: "tasks", label: "Công việc", icon: ListTodo }, { id: "reports", label: "Báo cáo", icon: BarChart3 },
    { id: "activity", label: "Hoạt động", icon: Bell }, { id: "copilot", label: "AI Copilot", icon: Sparkles },
  ];
  return <><aside className={`sidebar ${open ? "open" : ""}`}>
    <div className="brand"><div className="brand-mark"><Command size={20}/></div><div><strong>Orbit</strong><span>Business OS</span></div><button className="sidebar-close" onClick={close}><X size={18}/></button></div>
    <nav><p className="nav-heading">WORKSPACE</p>{items.map(({ id, label, icon: Icon }) => <button key={id} onClick={() => navigate(id)} className={view === id ? "active" : ""}><Icon size={18}/><span>{label}</span>{id === "copilot" && <em>AI</em>}</button>)}</nav>
    <div className="sidebar-spacer"/><div className="upgrade-card"><div className="glow"/><Bot size={22}/><strong>Copilot đã sẵn sàng</strong><span>Phân tích dữ liệu và hành động nhanh hơn.</span><button onClick={() => navigate("copilot")}>Bắt đầu <ChevronRight size={15}/></button></div>
    <button className="profile" onClick={onLogout} title="Đăng xuất"><div className="avatar small">{session.full_name.split(" ").slice(-2).map(part => part[0]).join("").toUpperCase()}</div><div><strong>{session.full_name}</strong><span>{session.role}</span></div><LogOut size={16}/></button>
  </aside>{open && <button className="sidebar-overlay" onClick={close} aria-label="Đóng menu"/>}</>;
}

function Overview({ metrics, customers, tasks, goCopilot }: { metrics: DashboardMetrics; customers: Customer[]; tasks: BusinessTask[]; goCopilot: () => void }) {
  const recentCustomers = customers.slice(0, 4);
  const activeTasks = tasks.filter(t => t.status !== "done").slice(0, 4);
  return <div className="page-grid">
    <section className="hero-card"><div><span className="hero-kicker"><Sparkles size={14}/> AI BUSINESS COPILOT</span><h2>Chào buổi sáng, Việt.</h2><p>Doanh nghiệp đang vận hành ổn định. Có <strong>{metrics.at_risk_customers} khách hàng</strong> cần chú ý và <strong>{metrics.overdue_tasks} công việc</strong> quá hạn.</p><button className="primary-button" onClick={goCopilot}><MessageSquareText size={17}/> Hỏi Copilot</button></div><div className="orbit-visual"><div className="ring ring-one"/><div className="ring ring-two"/><div className="core"><Bot size={30}/></div></div></section>
    <section className="metric-grid">
      <Metric icon={CircleDollarSign} label="Doanh thu đang quản lý" value={money(metrics.revenue)} trend="+12,4%" tone="violet" />
      <Metric icon={Target} label="Giá trị pipeline" value={money(metrics.pipeline_value)} trend="+8,2%" tone="blue" />
      <Metric icon={UsersRound} label="Khách hàng hoạt động" value={String(metrics.active_customers)} trend="+2 tháng này" tone="green" />
      <Metric icon={ListTodo} label="Công việc đang mở" value={String(metrics.open_tasks)} trend={`${metrics.overdue_tasks} quá hạn`} tone="amber" />
    </section>
    <section className="panel wide"><PanelHeader title="Khách hàng gần đây" subtitle="Tình trạng quan hệ khách hàng" action="Xem tất cả"/>
      <div className="customer-list">{recentCustomers.length ? recentCustomers.map(c => <div className="customer-row" key={c.id}><div className="company-avatar">{c.company.slice(0,2).toUpperCase()}</div><div className="customer-main"><strong>{c.company}</strong><span>{c.name} · {c.owner}</span></div><span className={statusClass[c.status]}>{statusLabel[c.status]}</span><div className="customer-value"><strong>{money(c.value)}</strong><span>Giá trị</span></div><ChevronRight size={17}/></div>) : <Empty text="Kết nối backend để tải khách hàng"/>}</div>
    </section>
    <section className="panel"><PanelHeader title="Ưu tiên hôm nay" subtitle="Các việc cần hành động"/>
      <div className="priority-list">{activeTasks.length ? activeTasks.map(task => <div className="priority-item" key={task.id}><span className={`priority-dot ${task.priority}`}/><div><strong>{task.title}</strong><span>{task.assignee} · {new Date(task.due_date).toLocaleDateString("vi-VN")}</span></div><ArrowUpRight size={16}/></div>) : <Empty text="Chưa có công việc"/>}</div>
    </section>
  </div>;
}

function Metric({ icon: Icon, label, value, trend, tone }: { icon: typeof Target; label: string; value: string; trend: string; tone: string }) {
  return <article className="metric-card"><div className={`metric-icon ${tone}`}><Icon size={20}/></div><p>{label}</p><div className="metric-value"><strong>{value}</strong><span className={tone === "amber" ? "warning" : "positive"}>{tone !== "amber" && <TrendingUp size={13}/>} {trend}</span></div></article>;
}

function PanelHeader({ title, subtitle, action }: { title: string; subtitle: string; action?: string }) { return <div className="panel-header"><div><h3>{title}</h3><p>{subtitle}</p></div>{action && <button>{action}<ChevronRight size={15}/></button>}</div>; }
function Empty({ text }: { text: string }) { return <div className="empty"><BriefcaseBusiness size={25}/><span>{text}</span></div>; }

function Customers({ customers }: { customers: Customer[] }) {
  const [query, setQuery] = useState("");
  const filtered = customers.filter(c => `${c.name} ${c.company} ${c.email}`.toLowerCase().includes(query.toLowerCase()));
  return <section className="panel page-panel"><div className="section-toolbar"><div className="field-search"><Search size={17}/><input value={query} onChange={e => setQuery(e.target.value)} placeholder="Tìm tên, công ty hoặc email..."/></div><button className="primary-button"><UsersRound size={17}/> Thêm khách hàng</button></div>
    <div className="table-wrap"><table><thead><tr><th>Khách hàng</th><th>Trạng thái</th><th>Giá trị</th><th>Liên hệ gần nhất</th><th>Phụ trách</th></tr></thead><tbody>{filtered.map(c => <tr key={c.id}><td><div className="table-person"><div className="company-avatar">{c.company.slice(0,2).toUpperCase()}</div><div><strong>{c.company}</strong><span>{c.name} · {c.email}</span></div></div></td><td><span className={statusClass[c.status]}>{statusLabel[c.status]}</span></td><td><strong>{fullMoney(c.value)}</strong></td><td>{new Date(c.last_contact).toLocaleDateString("vi-VN")}</td><td>{c.owner}</td></tr>)}</tbody></table>{!filtered.length && <Empty text="Không tìm thấy khách hàng"/>}</div>
  </section>;
}

function Tasks({ tasks, setTasks }: { tasks: BusinessTask[]; setTasks: (tasks: BusinessTask[]) => void }) {
  const columns: { id: TaskStatus; title: string }[] = [{ id: "todo", title: "Cần làm" }, { id: "in_progress", title: "Đang thực hiện" }, { id: "done", title: "Hoàn thành" }];
  const move = async (task: BusinessTask, status: TaskStatus) => { const previous = tasks; setTasks(tasks.map(t => t.id === task.id ? { ...t, status } : t)); try { await api.updateTask(task.id, status); } catch { setTasks(previous); } };
  return <div className="kanban">{columns.map(column => <section className="kanban-column" key={column.id}><header><div><span className={`column-dot ${column.id}`}/><strong>{column.title}</strong></div><em>{tasks.filter(t => t.status === column.id).length}</em></header><div className="task-stack">{tasks.filter(t => t.status === column.id).map(task => <article className="task-card" key={task.id}><div className="task-top"><span className={`priority-label ${task.priority}`}>{task.priority}</span><Clock3 size={15}/></div><h3>{task.title}</h3><p>{task.description || "Chưa có mô tả chi tiết."}</p><div className="task-footer"><span><UserRound size={14}/>{task.assignee}</span><span>{new Date(task.due_date).toLocaleDateString("vi-VN")}</span></div><div className="move-actions">{columns.filter(c => c.id !== column.id).map(c => <button key={c.id} onClick={() => move(task, c.id)}>{c.title}</button>)}</div></article>)}</div></section>)}</div>;
}

function Reports({ report }: { report?: OperationsReport }) {
  if (!report) return <section className="panel page-panel"><Empty text="Chưa có dữ liệu báo cáo"/></section>;
  const customerLabels: Record<string, string> = { active: "Đang hoạt động", at_risk: "Cần chú ý", lead: "Tiềm năng" };
  const taskLabels: Record<string, string> = { todo: "Cần làm", in_progress: "Đang thực hiện", done: "Hoàn thành" };
  const maxPortfolio = Math.max(...report.owner_performance.map(item => item.portfolio_value), 1);
  return <div className="reports-grid">
    <section className="panel report-card"><PanelHeader title="Sức khỏe khách hàng" subtitle="Phân bổ theo trạng thái"/><div className="distribution">{Object.entries(report.customer_distribution).map(([key, value]) => <div key={key}><div className={`donut-value ${key}`}>{value}</div><span>{customerLabels[key]}</span></div>)}</div></section>
    <section className="panel report-card"><PanelHeader title="Tiến độ công việc" subtitle="Phân bổ theo trạng thái"/><div className="distribution">{Object.entries(report.task_distribution).map(([key, value]) => <div key={key}><div className={`donut-value ${key}`}>{value}</div><span>{taskLabels[key]}</span></div>)}</div></section>
    <section className="panel owner-report"><PanelHeader title="Danh mục theo nhân viên" subtitle="Giá trị khách hàng đang phụ trách"/>{report.owner_performance.map(item => <div className="owner-row" key={item.owner}><div><strong>{item.owner}</strong><span>{item.customers} khách hàng</span></div><div className="owner-bar"><i style={{ width: `${item.portfolio_value / maxPortfolio * 100}%` }}/></div><strong>{money(item.portfolio_value)}</strong></div>)}</section>
  </div>;
}

function Activity({ notifications, audits }: { notifications: NotificationItem[]; audits: AuditLog[] }) {
  return <div className="activity-grid"><section className="panel"><PanelHeader title="Trung tâm thông báo" subtitle={`${notifications.filter(item => !item.is_read).length} thông báo chưa đọc`}/><div className="activity-list">{notifications.map(item => <div className="notification-row" key={item.id}><div className={`activity-icon ${item.level}`}><Bell size={16}/></div><div><strong>{item.title}</strong><p>{item.message}</p><span>{new Date(item.created_at).toLocaleString("vi-VN")}</span></div></div>)}</div></section><section className="panel"><PanelHeader title="Audit log" subtitle="Lịch sử thay đổi có thể kiểm chứng"/><div className="activity-list">{audits.map(item => <div className="notification-row" key={item.id}><div className="activity-icon audit"><ShieldCheck size={16}/></div><div><strong>{item.action}</strong><p>{item.actor} · {item.entity_type}</p><span>{new Date(item.created_at).toLocaleString("vi-VN")}</span></div></div>)}</div></section></div>;
}

function Copilot({ onTaskCreated, canApprove }: { onTaskCreated: (task: BusinessTask) => void; canApprove: boolean }) {
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [approvalToReview, setApprovalToReview] = useState<CopilotResponse["approval"]>();
  const [history, setHistory] = useState<{ role: "user" | "assistant"; text: string; response?: CopilotResponse }[]>([
    { role: "assistant", text: "Chào Việt! Tôi có thể phân tích KPI, tìm khách hàng lâu chưa liên hệ hoặc kiểm tra công việc quá hạn. Bạn muốn bắt đầu từ đâu?" },
  ]);
  const suggestions = ["Tóm tắt tình hình doanh nghiệp", "Khách hàng nào chưa liên hệ 30 ngày?", "Có công việc nào quá hạn?", "Tìm trên web tin mới về AI CRM"];
  const send = async (text = message) => { if (!text.trim() || loading) return; setMessage(""); setHistory(h => [...h, { role: "user", text }]); setLoading(true); try { const response = await api.copilot(text); setHistory(h => [...h, { role: "assistant", text: response.answer, response }]); } catch (error) { const detail = error instanceof Error ? error.message : "Lỗi không xác định"; setHistory(h => [...h, { role: "assistant", text: `Không thể xử lý yêu cầu: ${detail}` }]); } finally { setLoading(false); } };
  return <div className="copilot-layout"><section className="chat-panel"><div className="chat-heading"><div className="copilot-icon"><Sparkles size={20}/></div><div><strong>Orbit Copilot</strong><span><i/> Sẵn sàng hỗ trợ</span></div></div><div className="messages">{history.map((item, index) => <div className={`message ${item.role}`} key={index}>{item.role === "assistant" && <div className="bot-avatar"><Bot size={17}/></div>}<div className="bubble"><p>{item.text}</p>{item.response?.visualizations?.length ? <div className="chat-visualizations">{item.response.visualizations.map((visualization, chartIndex) => <VisualizationRenderer key={`${visualization.title}-${chartIndex}`} visualization={visualization}/>)}</div> : null}{item.response?.traces?.length ? <details><summary><Command size={14}/> Đã dùng {item.response.traces.length} công cụ</summary>{item.response.traces.map((trace, i) => <code key={i}>{trace.tool}({JSON.stringify(trace.arguments)})</code>)}</details> : null}{item.response?.approval && <div className="approval"><AlertTriangle size={17}/><div><strong>{canApprove ? "Cần phê duyệt" : "Chờ quản lý phê duyệt"}</strong><span>{item.response.approval.reason}</span></div>{canApprove && <button onClick={() => setApprovalToReview(item.response?.approval)}>Kiểm tra</button>}</div>}</div></div>)}{loading && <div className="message assistant"><div className="bot-avatar"><Bot size={17}/></div><div className="bubble typing"><i/><i/><i/></div></div>}</div><div className="suggestions">{suggestions.map(s => <button key={s} onClick={() => send(s)}>{s}</button>)}</div><div className="composer"><textarea value={message} onChange={e => setMessage(e.target.value)} onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }} placeholder="Hỏi Copilot về doanh nghiệp của bạn..."/><button onClick={() => send()} disabled={loading || !message.trim()} aria-label="Gửi"><Send size={18}/></button><span>Enter để gửi · Shift + Enter xuống dòng</span></div></section>
    {approvalToReview && <ApprovalModal approval={approvalToReview} onClose={() => setApprovalToReview(undefined)} onApproved={(task) => { onTaskCreated(task); setApprovalToReview(undefined); setHistory(h => [...h, { role: "assistant", text: `Đã phê duyệt và tạo công việc “${task.title}”. Bạn có thể xem công việc mới trong bảng Kanban.` }]); }} onRejected={() => { setApprovalToReview(undefined); setHistory(h => [...h, { role: "assistant", text: "Đã từ chối đề xuất. Không có dữ liệu nào được thay đổi." }]); }}/>} 
  </div>;
}

const CHART_COLORS = ["#6c4ff8", "#35a873", "#e7a23c", "#4a8bd8", "#d9586a"];

function VisualizationRenderer({ visualization }: { visualization: Visualization }) {
  const formatValue = (value: number, unit?: string) => unit === "VND" ? money(value) : new Intl.NumberFormat("vi-VN").format(value);
  if (visualization.type === "kpi") return <section className="chat-chart"><header><BarChart3 size={16}/><div><strong>{visualization.title}</strong>{visualization.description && <span>{visualization.description}</span>}</div></header><div className="chat-kpis">{visualization.data.map(item => <div key={item.label}><span>{item.label}</span><strong>{formatValue(item.value, item.unit ?? visualization.unit)}</strong></div>)}</div></section>;
  if (visualization.type === "donut") return <section className="chat-chart"><header><BarChart3 size={16}/><div><strong>{visualization.title}</strong>{visualization.description && <span>{visualization.description}</span>}</div></header><div className="donut-layout"><ResponsiveContainer width="55%" height={180}><PieChart><Pie data={visualization.data} dataKey="value" nameKey="label" innerRadius={48} outerRadius={72} paddingAngle={3}>{visualization.data.map((_, index) => <Cell key={index} fill={CHART_COLORS[index % CHART_COLORS.length]}/>)}</Pie><Tooltip formatter={(value) => formatValue(Number(value), visualization.unit)}/></PieChart></ResponsiveContainer><div className="chart-legend">{visualization.data.map((item, index) => <div key={item.label}><i style={{background:CHART_COLORS[index % CHART_COLORS.length]}}/><span>{item.label}</span><strong>{formatValue(item.value, visualization.unit)}</strong></div>)}</div></div></section>;
  return <section className="chat-chart"><header><BarChart3 size={16}/><div><strong>{visualization.title}</strong>{visualization.description && <span>{visualization.description}</span>}</div></header><ResponsiveContainer width="100%" height={220}><BarChart data={visualization.data} margin={{top:12,right:8,left:4,bottom:4}}><CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#ece9f1"/><XAxis dataKey="label" tick={{fontSize:10}} axisLine={false} tickLine={false}/><YAxis tick={{fontSize:9}} axisLine={false} tickLine={false} tickFormatter={(value) => visualization.unit === "VND" ? `${Math.round(value/1_000_000)}tr` : String(value)}/><Tooltip formatter={(value) => formatValue(Number(value), visualization.unit)}/><Bar dataKey="value" fill="#6c4ff8" radius={[6,6,0,0]}/></BarChart></ResponsiveContainer></section>;
}

function ApprovalModal({ approval, onClose, onApproved, onRejected }: {
  approval: NonNullable<CopilotResponse["approval"]>;
  onClose: () => void;
  onApproved: (task: BusinessTask) => void;
  onRejected: () => void;
}) {
  const initial = approval.payload;
  const [title, setTitle] = useState(String(initial.title ?? "Follow-up khách hàng"));
  const [description, setDescription] = useState(String(initial.description ?? ""));
  const [assignee, setAssignee] = useState(String(initial.assignee ?? ""));
  const [dueDate, setDueDate] = useState(String(initial.due_date ?? ""));
  const [priority, setPriority] = useState(String(initial.priority ?? "high"));
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const today = new Date().toISOString().slice(0, 10);
  const dateIsPast = Boolean(dueDate && dueDate < today);

  const approve = async () => {
    setError("");
    if (!title.trim() || !description.trim() || !assignee.trim() || !dueDate) { setError("Vui lòng điền đầy đủ thông tin trước khi phê duyệt."); return; }
    if (dateIsPast) { setError("Hạn hoàn thành không được nằm trong quá khứ."); return; }
    setSubmitting(true);
    try {
      const response = await api.executeApproval(approval.action, {
        ...initial, title: title.trim(), description: description.trim(), assignee: assignee.trim(), due_date: dueDate, priority,
      });
      onApproved(response.task);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Không thể tạo công việc.");
    } finally { setSubmitting(false); }
  };

  return <div className="modal-backdrop" role="presentation" onMouseDown={event => { if (event.target === event.currentTarget) onClose(); }}>
    <section className="approval-modal" role="dialog" aria-modal="true" aria-labelledby="approval-title">
      <header><div className="modal-icon"><CheckCircle2 size={22}/></div><div><span>APPROVAL REQUEST</span><h2 id="approval-title">Kiểm tra đề xuất công việc</h2><p>Xác nhận thông tin trước khi ghi vào hệ thống.</p></div><button className="modal-close" onClick={onClose} aria-label="Đóng"><X size={19}/></button></header>
      {dateIsPast && <div className="date-warning"><AlertTriangle size={17}/><div><strong>Deadline đã ở trong quá khứ</strong><span>Hãy chọn một ngày từ hôm nay trở đi trước khi phê duyệt.</span></div></div>}
      <div className="approval-form">
        <label><span>Tiêu đề công việc</span><input value={title} onChange={e => setTitle(e.target.value)}/></label>
        <label><span>Nội dung follow-up</span><textarea value={description} onChange={e => setDescription(e.target.value)} rows={4}/></label>
        <div className="form-row"><label><span>Người phụ trách</span><input value={assignee} onChange={e => setAssignee(e.target.value)}/></label><label><span>Mức ưu tiên</span><select value={priority} onChange={e => setPriority(e.target.value)}><option value="medium">Trung bình</option><option value="high">Cao</option><option value="urgent">Khẩn cấp</option></select></label></div>
        <label><span><CalendarDays size={14}/> Hạn hoàn thành</span><input type="date" min={today} value={dueDate} onChange={e => setDueDate(e.target.value)}/></label>
        <div className="approval-customer"><span>Khách hàng</span><strong>{String(initial.customer_name ?? initial.company ?? initial.customer_id ?? "Không xác định")}</strong></div>
        {error && <p className="form-error"><AlertTriangle size={15}/>{error}</p>}
      </div>
      <footer><button className="reject-button" onClick={onRejected} disabled={submitting}>Từ chối</button><div><button className="secondary-button" onClick={onClose} disabled={submitting}>Để sau</button><button className="approve-button" onClick={approve} disabled={submitting || dateIsPast}>{submitting ? <Loader2 className="spin" size={17}/> : <CheckCircle2 size={17}/>} Phê duyệt & tạo task</button></div></footer>
    </section>
  </div>;
}
