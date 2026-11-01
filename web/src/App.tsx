import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { friendlyChatError, useChat } from "./useChat";
import type { FormEvent } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Activity,
  ArrowDownToLine,
  ArrowRight,
  BookOpen,
  ChevronDown,
  CircleHelp,
  Dna,
  FileUp,
  Fingerprint,
  FlaskConical,
  HeartHandshake,
  History,
  Leaf,
  LoaderCircle,
  LockKeyhole,
  MessageSquare,
  Microscope,
  Plus,
  Settings2,
  ShieldCheck,
  Sparkles,
  X,
} from "lucide-react";
import * as Dialog from "@radix-ui/react-dialog";
import { followJob, loadSession, request, saveSession } from "./api";
import type { Session } from "./api";
import type {
  Answer,
  Dataset,
  Evidence,
  FamilyResult,
  Health,
  Methylation,
  MolecularResult,
  Profile,
  RunEvent,
  Trends,
  Variant,
} from "./types";
import { Button } from "./components/Button";
import { Chart } from "./components/Chart";
import { EvidencePanel } from "./components/EvidencePanel";
import { ImportDialog } from "./components/ImportDialog";
import { ProfileDialog } from "./components/ProfileDialog";
import { ChatList } from "./components/ChatList";
import { BrandMark } from "./components/BrandMark";
import { ActivityChips } from "./components/ActivityChips";
import { DemoExamples } from "./components/DemoExamples";
import { MolecularExplanation } from "./components/MolecularExplanation";
import {
  MethylationReport,
  MethylationTimeline,
} from "./components/MethylationReport";
import {
  EvidenceBadge,
  EVIDENCE_CATEGORIES,
  type EvidenceCategory,
} from "./components/EvidenceBadge";

type Tab = "chat" | "genetics" | "trends" | "family" | "methylation";
const NAV = [
  { id: "chat", title: "Ask Strand", icon: MessageSquare },
  { id: "genetics", title: "Genetic findings", icon: Dna },
  { id: "trends", title: "Health trends", icon: Activity },
  { id: "family", title: "Family planning", icon: HeartHandshake },
  { id: "methylation", title: "Methylation", icon: Fingerprint },
] as const;
const PROMPTS = [
  {
    icon: Dna,
    title: "Could my knee pain be genetic?",
    detail: "Explore a question about your DNA",
  },
  {
    icon: Activity,
    title: "Why is my resting heart rate higher?",
    detail: "Put your measurements in context",
  },
  {
    icon: Leaf,
    title: "What lifestyle changes are supported?",
    detail: "Find a practical starting point",
  },
];
let bootPromise: Promise<Session> | null = null;

function initialSession() {
  const cached = loadSession();
  if (cached && (!cached.demo || cached.demo_source === "synthetic"))
    return Promise.resolve(cached);
  if (!bootPromise)
    bootPromise = (
      cached?.demo_source === "public"
        ? request<Profile[]>("/api/demo/combined-profiles", cached.token, {
            method: "POST",
          }).then((profiles) => ({ ...cached, profiles }))
        : request<Session>("/api/session", undefined, {
            method: "POST",
            body: JSON.stringify({ demo: true }),
          })
    )
      .then((session) => {
        saveSession(session);
        return session;
      })
      .catch((error) => {
        bootPromise = null;
        throw error;
      });
  return bootPromise;
}

export default function App() {
  const client = useQueryClient();
  const [session, setSession] = useState<Session | null>(null),
    [bootError, setBootError] = useState("");
  const [profileId, setProfileId] = useState(""),
    [tab, setTab] = useState<Tab>("chat");
  const [historyOpen, setHistoryOpen] = useState(false);
  const [evidenceOpen, setEvidenceOpen] = useState(false);
  const [focusedEvidence, setFocusedEvidence] = useState<{
    records: Evidence[];
    id: string;
  } | null>(null);
  const [uploadOpen, setUploadOpen] = useState(false),
    [profileOpen, setProfileOpen] = useState(false),
    [settingsOpen, setSettingsOpen] = useState(false);
  const [privateOpen, setPrivateOpen] = useState(false),
    [accessKey, setAccessKey] = useState(""),
    [privateError, setPrivateError] = useState("");
  const bottom = useRef<HTMLDivElement>(null);
  const autoScroll = useRef(true);
  const viewedChat = useRef<string | null>(null);
  const lastMessage = useRef<string | null>(null);
  useEffect(() => {
    let alive = true;
    initialSession()
      .then((value) => {
        if (alive) setSession(value);
      })
      .catch((error) => {
        if (alive) setBootError(error.message);
      });
    return () => {
      alive = false;
    };
  }, []);
  const health = useQuery({
    queryKey: ["health"],
    queryFn: () => request<Health>("/api/health"),
    retry: false,
  });
  const profilesQuery = useQuery({
    queryKey: ["profiles", session?.token],
    queryFn: () => request<Profile[]>("/api/profiles", session!.token),
    enabled: !!session,
  });
  const profiles = profilesQuery.data || session?.profiles || [];
  const profile =
    profiles.find((value) => value.id === profileId) || profiles[0];
  const activeId = profile?.id || "";
  const chat = useChat(session?.token, activeId);
  const { busy, draft: question, setDraft: setQuestion } = chat;
  const datasets = useQuery({
    queryKey: ["datasets", session?.token, activeId],
    queryFn: () =>
      request<Dataset[]>(`/api/profiles/${activeId}/datasets`, session!.token),
    enabled: !!activeId,
  });
  const trends = useQuery({
    queryKey: ["trends", session?.token, activeId],
    queryFn: () =>
      request<Trends>(`/api/profiles/${activeId}/wearables`, session!.token),
    enabled: !!activeId,
  });
  const visibleTurns = chat.messages;
  const latestAnswer = [...visibleTurns]
    .reverse()
    .find((turn) => turn.answer)?.answer;
  const [viewEvidence, setViewEvidence] = useState<Evidence[]>([]);
  const wearableDataset = datasets.data?.find(
    (item) => item.kind === "wearables",
  );
  const trendEvidence: Evidence[] =
    wearableDataset && trends.data?.record_count
      ? [
          {
            id: `wearable-${wearableDataset.id}`,
            category: "measurement",
            title: "Measurements in this wearable profile",
            url: wearableDataset.metadata.source_url || null,
            summary: Object.entries(trends.data.metrics)
              .map(
                ([metric, value]) =>
                  `${metric.replaceAll("_", " ")}: latest ${value.latest.toFixed(1)}; historical median ${value.baseline?.toFixed(1) ?? "not established"} (${value.baseline_days} historical days).`,
              )
              .join(" "),
            limitations: [
              wearableDataset.metadata.limitations,
              ...trends.data.limitations,
            ]
              .filter(Boolean)
              .join(" "),
            context:
              wearableDataset.metadata.date_range ||
              "Recorded dates are shown on the charts.",
            provenance: wearableDataset.metadata.provenance || "uploaded",
          },
        ]
      : [];
  const evidence =
    focusedEvidence?.records ||
    (tab === "chat"
      ? latestAnswer?.evidence || []
      : tab === "trends"
        ? trendEvidence
        : viewEvidence);
  function inspectEvidence(records: Evidence[], id: string) {
    setFocusedEvidence({ records, id });
    if (window.matchMedia("(max-width: 1100px)").matches || tab !== "chat")
      setEvidenceOpen(true);
  }
  const geneticCount = (datasets.data || [])
    .filter((d) => d.kind === "genetics")
    .reduce((sum, d) => sum + d.report.accepted, 0);
  const hasMethylation = (datasets.data || []).some(
    (d) => d.kind === "methylation",
  );
  const hr = trends.data?.metrics.resting_heart_rate;

  function refresh() {
    client.invalidateQueries({
      predicate: (query) => query.queryKey.includes(activeId),
    });
    client.invalidateQueries({ queryKey: ["profiles"] });
  }
  function selectProfile(id: string) {
    setFocusedEvidence(null);
    setProfileId(id);
    setViewEvidence([]);
  }
  function selectTab(value: Tab) {
    setFocusedEvidence(null);
    setTab(value);
    setViewEvidence([]);
  }
  async function privateWorkspace(event: FormEvent) {
    event.preventDefault();
    setPrivateError("");
    try {
      const value = await request<Session>("/api/session", undefined, {
        method: "POST",
        body: JSON.stringify({ demo: false, access_key: accessKey }),
      });
      saveSession(value);
      setSession(value);
      setProfileId("");
      setPrivateOpen(false);
      setProfileOpen(true);
      setTab("chat");
    } catch (error) {
      setPrivateError((error as Error).message);
    }
  }
  function ask(text: string) {
    setFocusedEvidence(null);
    autoScroll.current = true;
    setTab("chat");
    chat.ask(text);
  }
  function selectConversation(id: string) {
    setFocusedEvidence(null);
    autoScroll.current = true;
    chat.select(id);
    setTab("chat");
    setHistoryOpen(false);
  }
  function newChat() {
    setFocusedEvidence(null);
    autoScroll.current = true;
    setTab("chat");
    setHistoryOpen(false);
    chat.newChat();
  }
  useLayoutEffect(() => {
    if (tab !== "chat") {
      viewedChat.current = null;
      return;
    }
    if (chat.loading || !visibleTurns.length) return;
    const lastId = visibleTurns.at(-1)?.id || null;
    const changed =
      viewedChat.current !== chat.conversationId ||
      lastMessage.current !== lastId;
    if (changed || autoScroll.current) {
      const box = bottom.current?.parentElement;
      if (box) box.scrollTop = box.scrollHeight;
    }
    viewedChat.current = chat.conversationId;
    lastMessage.current = lastId;
  }, [chat.messages, chat.conversationId, chat.loading, tab]);

  if (bootError)
    return (
      <div className="connection-page">
        <Dna size={34} />
        <h1>Connect to your workspace</h1>
        <p>{bootError}</p>
        <p>
          Start the API with <code>uv run --all-extras helix-api</code>, then
          refresh.
        </p>
        <Button onClick={() => location.reload()}>Try again</Button>
      </div>
    );
  if (!session)
    return (
      <div className="connection-page">
        <Dna size={34} />
        <h1>Strand</h1>
        <LoaderCircle className="spin" />
        <p>Opening your research workspace…</p>
      </div>
    );

  return (
    <div className={`app-shell ${session.demo ? "is-demo" : ""}`}>
      <aside className="sidebar">
        <a
          className="brand"
          href="#"
          aria-label="Strand home"
          onClick={(event) => {
            event.preventDefault();
            selectTab("chat");
          }}
        >
          <BrandMark />
          <span>
            Strand<small>DNA AGENT</small>
          </span>
        </a>
        <div className="sidebar-scroll">
          <nav aria-label="Main navigation">
            {NAV.map((item, index) => (
              <button
                key={item.id}
                aria-label={
                  item.id === "methylation"
                    ? "Methylation Optional"
                    : item.title
                }
                aria-current={tab === item.id ? "page" : undefined}
                title={item.title}
                className={`nav-item ${tab === item.id ? "active" : ""}`}
                onClick={() => selectTab(item.id)}
              >
                <span className="nav-number">0{index + 1}</span>
                <span className="nav-label">
                  {
                    [
                      "Ask",
                      "Investigate",
                      "Wearables",
                      "Family",
                      "Methylation",
                    ][index]
                  }
                </span>
                {item.id === "methylation" && (
                  <span className="nav-mini">Optional</span>
                )}
              </button>
            ))}
          </nav>
          <div className="sidebar-section-title profile-section-title">
            PROFILE
            <button
              className="icon-button"
              aria-label="Add profile"
              onClick={() =>
                session.demo ? setPrivateOpen(true) : setProfileOpen(true)
              }
            >
              <Plus size={14} />
            </button>
          </div>
          <div
            className="profile-switch"
            title={profile?.name || "Choose profile"}
          >
            <span className="avatar">{profile?.name[0] || "Y"}</span>
            <div>
              <label className="sr-only" htmlFor="profile-selector">
                Active profile
              </label>
              <select
                id="profile-selector"
                value={activeId}
                onChange={(event) => selectProfile(event.target.value)}
              >
                {profiles.map((p) => (
                  <option value={p.id} key={p.id}>
                    {p.name}
                  </option>
                ))}
                {!profiles.length && <option value="">Your profile</option>}
              </select>
              <span>All profiles & source samples</span>
            </div>
            <ChevronDown size={13} />
          </div>
          <div className="sidebar-profiles">
            {profiles
              .filter(
                (p) => p.provenance !== "public_reference" || p.id === activeId,
              )
              .map((p, index) => (
                <button
                  key={p.id}
                  className={`small-profile ${activeId === p.id ? "selected" : ""}`}
                  onClick={() => selectProfile(p.id)}
                >
                  <span className={`small-avatar persona-${index % 2}`}>
                    {p.name[0]}
                  </span>
                  <span className="profile-card-copy">
                    <strong>{p.name.split(" · ")[0]}</strong>
                    <small>
                      {p.provenance === "composite_demo"
                        ? "DNA · wearable"
                        : p.provenance === "synthetic"
                          ? "Synthetic fixture"
                          : p.provenance === "public_reference"
                            ? "Original source"
                            : "Your uploaded data"}
                    </small>
                  </span>
                  <span className="provenance-tag">
                    {p.provenance === "composite_demo"
                      ? "DEMO"
                      : p.provenance === "synthetic"
                        ? "SYNTHETIC"
                        : p.provenance === "public_reference"
                          ? "PUBLIC"
                          : "PRIVATE"}
                  </span>
                </button>
              ))}
          </div>
          <div className="sidebar-section-title chat-history-title">
            YOUR CHATS
            <button
              className="icon-button"
              aria-label="Start a new chat"
              disabled={chat.submitting}
              onClick={newChat}
            >
              <Plus size={14} />
            </button>
          </div>
          <ChatList
            chats={chat.conversations}
            activeId={chat.conversationId}
            onSelect={selectConversation}
          />
        </div>
        <div className="sidebar-bottom">
          <div className="sidebar-evidence-key">
            <div className="eyebrow">EVIDENCE KEY</div>
            {(Object.keys(EVIDENCE_CATEGORIES) as EvidenceCategory[]).map(
              (category) => (
                <EvidenceBadge key={category} category={category} />
              ),
            )}
          </div>
          <button
            className="nav-item settings-link"
            onClick={() => setSettingsOpen(true)}
            aria-label="Workspace settings"
          >
            <Settings2 size={15} />
            <span>Workspace settings</span>
          </button>
        </div>
      </aside>
      <div
        className={`workspace ${tab === "chat" ? "chat-workspace" : ""} ${visibleTurns.length ? "has-chat-messages" : ""}`}
      >
        <header className="topbar">
          <div className="breadcrumb">
            Workspace <span>/</span> {NAV.find((n) => n.id === tab)?.title}
          </div>
          <div className="topbar-actions">
            <Button
              variant="ghost"
              onClick={() => setEvidenceOpen(true)}
              aria-label="Open evidence drawer"
            >
              <BookOpen size={15} />
              <span>Evidence</span>
            </Button>
            <Button
              variant="ghost"
              onClick={() => setHistoryOpen(true)}
              aria-label="Open chat history"
            >
              <History size={15} />
              <span>Chats</span>
            </Button>
            <Button
              variant="secondary"
              onClick={newChat}
              disabled={chat.submitting}
            >
              <Plus size={15} />
              New chat
            </Button>
            <span
              className={`status-pill ${health.data?.providers.chat ? "live" : ""}`}
            >
              <i />
              {health.data?.providers.chat
                ? "Live AI connected"
                : "Evidence library"}
            </span>
            <Button
              variant="secondary"
              onClick={() =>
                session.demo ? setPrivateOpen(true) : setUploadOpen(true)
              }
            >
              <FileUp size={15} /> Add data
            </Button>
          </div>
        </header>
        {session.demo && (
          <div className="demo-ribbon">
            <FlaskConical size={14} />
            <span>
              {profile?.provenance === "composite_demo"
                ? "Combined demo. A fictional person with public-source DNA and wearable data."
                : session.demo_source === "public"
                  ? "Public research data. Original source samples are kept in separate profiles."
                  : "You’re exploring synthetic demo data. No real person’s health is represented."}
            </span>
            <button onClick={() => setPrivateOpen(true)}>
              Use my data <ArrowRight size={13} />
            </button>
          </div>
        )}
        <div
          className={`workspace-columns ${tab !== "chat" ? "full-width-workspace" : ""}`}
        >
          <main className="main-content">
            {(profile?.provenance === "public_reference" ||
              profile?.provenance === "composite_demo") && (
              <details className="profile-source-note">
                <summary>
                  <FlaskConical size={13} />
                  <span>{profile.source_name}</span>
                  <span className="source-disclosure-label">
                    Sources & demo context
                  </span>
                </summary>
                <div>
                  <a href={profile.source_url} target="_blank" rel="noreferrer">
                    <strong>{profile.source_name}</strong> ↗
                  </a>
                  <p>{profile.data_notes}</p>
                  {profile.provenance === "composite_demo" && (
                    <p>
                      <a
                        href="https://datasets.simula.no/pmdata/"
                        target="_blank"
                        rel="noreferrer"
                      >
                        Wearables: PMData p01 ↗
                      </a>
                      {" · "}Ask as {profile.name.split(" · ")[0]}; answers use
                      this demo scenario.
                    </p>
                  )}
                </div>
              </details>
            )}
            {(profilesQuery.error || datasets.error) && (
              <div className="error" role="alert">
                {(profilesQuery.error || datasets.error)?.message}{" "}
                <button
                  onClick={() => {
                    sessionStorage.removeItem("helix.session.v1");
                    location.reload();
                  }}
                >
                  Reconnect
                </button>
              </div>
            )}
            {session.demo && session.demo_source === "public" && (
              <DemoExamples
                profiles={profiles}
                current={profile}
                onChoose={(id, view) => {
                  selectProfile(id);
                  selectTab(view);
                }}
              />
            )}
            {!profile ? (
              <div className="empty-state">
                <Dna size={38} />
                <h1>Start with your DNA.</h1>
                <p>
                  Create a profile and upload a compatible genetic file.
                  Everything else can come later.
                </p>
                <Button onClick={() => setProfileOpen(true)}>
                  <Plus size={16} /> Create your profile
                </Button>
              </div>
            ) : (
              <>
                {tab === "chat" && (
                  <>
                    <section
                      className={`welcome ${visibleTurns.length ? "compact" : ""}`}
                    >
                      <div className="eyebrow">
                        <span className="tiny-line" /> YOUR BIOLOGY, IN CONTEXT
                      </div>
                      <h1>
                        {visibleTurns.length ? (
                          "Let’s follow the evidence."
                        ) : (
                          <>
                            A clearer picture
                            <br />
                            of <em>your biology.</em>
                          </>
                        )}
                      </h1>
                      <p>
                        Connect the dots between your DNA, your daily life,
                        <br className="desktop-break" /> and the questions that
                        matter to you.
                      </p>
                      <div className="welcome-decoration" aria-hidden="true">
                        <Dna size={164} strokeWidth={0.55} />
                        <div className="orbit orbit-one" />
                        <div className="orbit orbit-two" />
                        <span className="orbit-dot one" />
                        <span className="orbit-dot two" />
                      </div>
                    </section>
                    {!visibleTurns.length && !chat.loading && (
                      <>
                        <div className="metrics-grid">
                          <Metric
                            icon={Dna}
                            label="GENETIC DATA"
                            value={
                              geneticCount
                                ? `${geneticCount} calls`
                                : "Not added"
                            }
                            detail={
                              geneticCount
                                ? "Available in this profile"
                                : "Your starting point"
                            }
                          />
                          <Metric
                            icon={Activity}
                            label="RESTING HEART RATE"
                            value={
                              hr?.baseline != null
                                ? `${hr.baseline.toFixed(1)}`
                                : "—"
                            }
                            unit={hr?.baseline != null ? "bpm" : ""}
                            detail={
                              hr?.baseline != null
                                ? "Your historical median"
                                : "Wearable data is optional"
                            }
                          />
                          <Metric
                            icon={Fingerprint}
                            label="METHYLATION"
                            value={hasMethylation ? "Available" : "Optional"}
                            detail={
                              hasMethylation
                                ? "Measured sample data"
                                : "No extra test needed to start"
                            }
                          />
                        </div>
                        <div className="section-line">
                          <span>A GOOD PLACE TO START</span>
                          <span>Ask a question, follow a finding.</span>
                        </div>
                        <div className="prompt-grid">
                          {PROMPTS.map((prompt) => (
                            <button
                              className="prompt-card"
                              key={prompt.title}
                              onClick={() => ask(prompt.title)}
                            >
                              <prompt.icon size={20} strokeWidth={1.5} />
                              <h3>{prompt.title}</h3>
                              <p>{prompt.detail}</p>
                              <ArrowRight size={15} />
                            </button>
                          ))}
                        </div>
                        <div className="how-it-works">
                          <div className="mini-icon">
                            <Microscope size={17} />
                          </div>
                          <div>
                            <strong>An investigation you can inspect.</strong>
                            <p>
                              See the data, the research, and what remains
                              unknown.
                            </p>
                          </div>
                          <BookOpen size={17} />
                        </div>
                      </>
                    )}
                    {chat.title && visibleTurns.length > 0 && (
                      <p
                        className="current-chat-title"
                        aria-label="Current conversation"
                      >
                        {chat.title}
                        <span>Saved in this workspace</span>
                      </p>
                    )}
                    <div
                      className={`conversation ${visibleTurns.length ? "has-messages" : ""}`}
                      aria-live="polite"
                      onScroll={(event) => {
                        const el = event.currentTarget;
                        autoScroll.current =
                          el.scrollHeight - el.scrollTop - el.clientHeight <
                          100;
                      }}
                    >
                      {chat.loading && (
                        <p className="working">
                          Loading your saved conversation…
                        </p>
                      )}
                      {chat.hasMore && (
                        <Button variant="ghost" onClick={chat.loadEarlier}>
                          Load earlier messages
                        </Button>
                      )}
                      {visibleTurns.map((turn) => (
                        <article className="turn" key={turn.id}>
                          <div className="user-question">
                            <span className="user-marker">YOU</span>
                            <p>{turn.question}</p>
                          </div>
                          {turn.events.length > 0 && (
                            <ActivityChips events={turn.events} />
                          )}
                          {turn.events.length > 0 && (
                            <details
                              className="run-timeline"
                              open={!turn.answer && !turn.error}
                            >
                              <summary>
                                <FlaskConical size={14} /> Investigation
                                activity{" "}
                                <span>{turn.events.length} events</span>
                              </summary>
                              {turn.events.map((event) => (
                                <div key={event.id}>
                                  <span
                                    className={`event-dot ${event.kind === "failed" ? "failed" : ""}`}
                                  />
                                  <p>
                                    <strong>{event.agent}</strong>
                                    {event.kind === "failed"
                                      ? friendlyChatError(event.message)
                                      : event.message}
                                  </p>
                                </div>
                              ))}
                            </details>
                          )}
                          {turn.answer ? (
                            <AnswerCard
                              answer={turn.answer}
                              onEvidence={(id) =>
                                inspectEvidence(turn.answer!.evidence, id)
                              }
                            />
                          ) : turn.error ? (
                            <div className="error" role="alert">
                              {friendlyChatError(turn.error)}
                            </div>
                          ) : (
                            <div className="working">
                              <LoaderCircle className="spin" size={16} />{" "}
                              Checking your data and supporting evidence…
                            </div>
                          )}
                          {(turn.error || turn.answer?.notice) &&
                            turn.id === visibleTurns.at(-1)?.id && (
                              <Button
                                variant="ghost"
                                disabled={busy}
                                onClick={() => chat.retry(turn.id)}
                              >
                                Retry answer
                              </Button>
                            )}
                        </article>
                      ))}
                      <div ref={bottom} />
                    </div>
                    {chat.error && (
                      <p className="error" role="alert">
                        {friendlyChatError(chat.error)}
                      </p>
                    )}
                    <div className="composer-dock">
                      <div
                        className="suggested-prompts"
                        aria-label="Suggested follow-up prompts"
                      >
                        {(latestAnswer?.followups.length
                          ? latestAnswer.followups.slice(0, 3)
                          : [
                              "What does my DNA show?",
                              "Explain methylation",
                              "What data would help?",
                            ]
                        ).map((text) => (
                          <button
                            key={text}
                            disabled={busy}
                            onClick={() => ask(text)}
                          >
                            <span>{text}</span>
                            <ArrowRight size={12} />
                          </button>
                        ))}
                      </div>
                      <form
                        className="composer"
                        onSubmit={(event) => {
                          event.preventDefault();
                          ask(question);
                        }}
                      >
                        <div className="composer-main">
                          <Dna size={22} strokeWidth={1.4} />
                          <label className="sr-only" htmlFor="question">
                            Ask a question about your data
                          </label>
                          <textarea
                            id="question"
                            value={question}
                            rows={2}
                            onChange={(event) =>
                              setQuestion(event.target.value)
                            }
                            onKeyDown={(event) => {
                              if (
                                event.key === "Enter" &&
                                !event.shiftKey &&
                                !event.nativeEvent.isComposing
                              ) {
                                event.preventDefault();
                                ask(question);
                              }
                            }}
                            placeholder="Ask about your data…"
                            maxLength={4000}
                          />
                          <button
                            className="send-button"
                            aria-label="Send question"
                            disabled={busy || !question.trim()}
                          >
                            <span>Ask</span>
                          </button>
                        </div>
                        <div className="composer-footer">
                          <span>
                            <LockKeyhole size={11} />{" "}
                            {profile.name.split(" ")[0]}
                            ’s profile{" "}
                            <span className="composer-separator">·</span>{" "}
                            Evidence-backed answers
                          </span>
                          <span>Enter to send</span>
                        </div>
                      </form>
                    </div>
                    <p className="research-note">
                      For research and understanding. Genetic findings and model
                      predictions require appropriate confirmation.
                    </p>
                  </>
                )}
                {tab === "genetics" && (
                  <GeneticsView
                    profile={profile}
                    token={session.token}
                    providers={health.data?.providers}
                    datasets={datasets.data || []}
                    onEvidence={setViewEvidence}
                    onAsk={ask}
                    onUpload={() =>
                      session.demo ? setPrivateOpen(true) : setUploadOpen(true)
                    }
                  />
                )}
                {tab === "trends" && (
                  <TrendsView
                    trends={trends.data}
                    onAsk={() =>
                      ask(
                        "Explain my resting heart rate and sleep trends, and what I can do based on the evidence.",
                      )
                    }
                    onUpload={() =>
                      session.demo ? setPrivateOpen(true) : setUploadOpen(true)
                    }
                  />
                )}
                {tab === "family" && (
                  <FamilyView
                    key={profile.id}
                    profile={profile}
                    profiles={profiles}
                    token={session.token}
                    onEvidence={setViewEvidence}
                    onSelectProfile={selectProfile}
                  />
                )}
                {tab === "methylation" && (
                  <MethylationView
                    profile={profile}
                    token={session.token}
                    onImported={refresh}
                    onAsk={ask}
                    onEvidence={setViewEvidence}
                    onSelectProfile={selectProfile}
                    onUpload={() =>
                      session.demo ? setPrivateOpen(true) : setUploadOpen(true)
                    }
                  />
                )}
              </>
            )}
          </main>
          <EvidencePanel
            evidence={evidence}
            activeId={focusedEvidence?.id}
            onSelect={(id) => setFocusedEvidence({ records: evidence, id })}
          />
        </div>
      </div>
      <Dialog.Root open={evidenceOpen} onOpenChange={setEvidenceOpen}>
        <Dialog.Portal>
          <Dialog.Overlay className="dialog-overlay" />
          <Dialog.Content className="dialog-content evidence-dialog">
            <div className="dialog-heading">
              <Dialog.Title>Evidence drawer</Dialog.Title>
              <Dialog.Close
                className="icon-button"
                aria-label="Close evidence drawer"
              >
                <X size={20} />
              </Dialog.Close>
            </div>
            <Dialog.Description className="sr-only">
              Inspect the sources and limitations behind this answer.
            </Dialog.Description>
            <EvidencePanel
              evidence={evidence}
              activeId={focusedEvidence?.id}
              onSelect={(id) => setFocusedEvidence({ records: evidence, id })}
            />
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
      {profile && (
        <ImportDialog
          profileId={activeId}
          token={session.token}
          onImported={refresh}
          open={uploadOpen}
          onOpenChange={setUploadOpen}
        />
      )}
      <ProfileDialog
        token={session.token}
        open={profileOpen}
        onOpenChange={setProfileOpen}
        onCreated={(p) => {
          setProfileId(p.id);
          client.invalidateQueries({ queryKey: ["profiles"] });
        }}
      />
      <Dialog.Root open={historyOpen} onOpenChange={setHistoryOpen}>
        <Dialog.Portal>
          <Dialog.Overlay className="dialog-overlay" />
          <Dialog.Content className="dialog-content chat-history-dialog">
            <div className="dialog-heading">
              <History size={22} />
              <Dialog.Close
                className="icon-button"
                aria-label="Close chat history"
              >
                <X size={20} />
              </Dialog.Close>
            </div>
            <Dialog.Title>Your chats</Dialog.Title>
            <Dialog.Description>
              Saved conversations for {profile?.name || "this profile"}.
            </Dialog.Description>
            <Button
              variant="secondary"
              onClick={newChat}
              disabled={chat.submitting}
            >
              <Plus size={15} />
              New chat
            </Button>
            <ChatList
              chats={chat.conversations}
              activeId={chat.conversationId}
              onSelect={selectConversation}
            />
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
      <Dialog.Root open={privateOpen} onOpenChange={setPrivateOpen}>
        <Dialog.Portal>
          <Dialog.Overlay className="dialog-overlay" />
          <Dialog.Content className="dialog-content">
            <div className="dialog-heading">
              <div className="icon-tile">
                <LockKeyhole size={22} />
              </div>
              <Dialog.Close
                className="icon-button"
                aria-label="Close private workspace"
              >
                <X size={20} />
              </Dialog.Close>
            </div>
            <Dialog.Title>A workspace for your data</Dialog.Title>
            <Dialog.Description>
              Your personal files will be kept separate from demo datasets. DNA
              is the only starting input; methylation is optional.
            </Dialog.Description>
            <form onSubmit={privateWorkspace}>
              <label>
                Workspace access key
                <input
                  type="password"
                  value={accessKey}
                  onChange={(e) => setAccessKey(e.target.value)}
                  placeholder="Leave empty for local development"
                  autoComplete="off"
                />
              </label>
              {privateError && (
                <p className="error" role="alert">
                  {privateError}
                </p>
              )}
              <Button className="full-width">
                Create private workspace <ArrowRight size={15} />
              </Button>
            </form>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
      <Dialog.Root open={settingsOpen} onOpenChange={setSettingsOpen}>
        <Dialog.Portal>
          <Dialog.Overlay className="dialog-overlay" />
          <Dialog.Content className="dialog-content">
            <div className="dialog-heading">
              <div className="icon-tile">
                <Settings2 size={21} />
              </div>
              <Dialog.Close className="icon-button" aria-label="Close settings">
                <X size={20} />
              </Dialog.Close>
            </div>
            <Dialog.Title>Workspace settings</Dialog.Title>
            <Dialog.Description>
              Know which capabilities are active and control external analysis.
            </Dialog.Description>
            <div className="provider-list">
              {[
                ["Evidence library", true],
                ["Live AI conversation", health.data?.providers.chat],
                ["AlphaGenome predictions", health.data?.providers.alphagenome],
                ["Evo 2 scoring", health.data?.providers.evo2],
              ].map(([label, ready]) => (
                <div key={String(label)}>
                  <span>{label}</span>
                  <span className={`badge ${ready ? "green" : ""}`}>
                    {ready ? "Connected" : "Not configured"}
                  </span>
                </div>
              ))}
            </div>
            <p className="small muted">
              Provider credentials belong in the backend environment. Missing
              services never return simulated scientific results.
            </p>
            {profile && !session.demo && (
              <label className="checkbox-row">
                <input
                  type="checkbox"
                  checked={profile.external_analysis_consent}
                  onChange={async (event) => {
                    try {
                      await request(
                        `/api/profiles/${activeId}`,
                        session.token,
                        {
                          method: "PATCH",
                          body: JSON.stringify({
                            ...profile,
                            external_analysis_consent: event.target.checked,
                          }),
                        },
                      );
                      refresh();
                    } catch (error) {
                      setBootError((error as Error).message);
                    }
                  }}
                />
                <span>
                  Allow selected variants and relevant summaries to be sent to
                  configured external providers.
                </span>
              </label>
            )}
            <div className="notice">
              <ShieldCheck size={17} />
              <span>
                DNA is sufficient to start. A methylation test is never
                required.
              </span>
            </div>
            <Button
              variant="secondary"
              className="full-width"
              onClick={() => {
                sessionStorage.removeItem("helix.session.v1");
                location.reload();
              }}
            >
              Open a fresh demo session
            </Button>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </div>
  );
}

function Metric({
  icon: Icon,
  label,
  value,
  unit,
  detail,
}: {
  icon: typeof Dna;
  label: string;
  value: string;
  unit?: string;
  detail: string;
}) {
  return (
    <div className="metric-card">
      <div className="metric-heading">
        <span>{label}</span>
        <Icon size={16} strokeWidth={1.5} />
      </div>
      <div className="metric-value">
        {value} {unit && <span>{unit}</span>}
      </div>
      <p>{detail}</p>
    </div>
  );
}

function AnswerCard({
  answer,
  onEvidence,
}: {
  answer: Answer;
  onEvidence: (id: string) => void;
}) {
  const cited = new Set(
    [...answer.claims, ...answer.recommendations].flatMap(
      (item) => item.evidence_ids,
    ),
  );
  function references(ids: string[]) {
    return ids.map((id) => {
      const index = answer.evidence.findIndex((item) => item.id === id);
      return index < 0 ? null : (
        <button
          className="citation-ref"
          key={id}
          onClick={() => onEvidence(id)}
          title={answer.evidence[index].title}
          aria-label={`Inspect source E${index + 1}: ${answer.evidence[index].title}`}
        >
          E{index + 1}
        </button>
      );
    });
  }
  function download() {
    const blob = new Blob([JSON.stringify(answer, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "strand-evidence-report.json";
    link.click();
    URL.revokeObjectURL(url);
  }
  return (
    <div className="answer-card">
      <div className="answer-heading">
        <span className="eyebrow">
          {answer.mode === "live" ? "REVIEWED ANSWER" : "EVIDENCE LIBRARY"}
        </span>
        <span className="badge">
          {answer.mode === "live"
            ? "Reviewed AI answer"
            : "Evidence-library answer"}
        </span>
        <button
          className="icon-button"
          aria-label="Download evidence report"
          onClick={download}
        >
          <ArrowDownToLine size={16} />
        </button>
      </div>
      <h2>{answer.title}</h2>
      {answer.notice && (
        <p className="notice answer-notice" role="status">
          {answer.notice}
        </p>
      )}
      {answer.response.split("\n\n").map((paragraph, i) => (
        <p key={i}>{paragraph}</p>
      ))}
      {cited.size > 0 && (
        <div className="answer-sources">
          <span className="eyebrow">SUPPORTING SOURCES</span>
          {references([...cited])}
        </div>
      )}
      {answer.claims.length > 0 && (
        <details className="claims-details">
          <summary>
            See the evidence behind {answer.claims.length} claims
          </summary>
          {answer.claims.map((claim, index) => (
            <p key={index}>
              {claim.text} {references(claim.evidence_ids)}
            </p>
          ))}
        </details>
      )}
      <div className="answer-detail-grid">
        {answer.recommendations.length > 0 && (
          <div className="recommendations">
            <div className="eyebrow">SUGGESTED ACTION</div>
            {answer.recommendations.map((rec, index) => (
              <div className="recommendation" key={index}>
                <span>{String(index + 1).padStart(2, "0")}</span>
                <div>
                  <h3>
                    {rec.action} {references(rec.evidence_ids)}
                  </h3>
                  <p>{rec.reason}</p>
                  <p className="track-outcome">Track: {rec.outcome_to_track}</p>
                  <span className="badge">
                    Based on {rec.personalization_basis.replaceAll("_", " ")}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
        {answer.unknowns.length > 0 && (
          <details className="unknowns" open>
            <summary>WHAT THIS CANNOT TELL YOU</summary>
            <ul>
              {answer.unknowns.map((value) => (
                <li key={value}>{value}</li>
              ))}
            </ul>
          </details>
        )}
      </div>
    </div>
  );
}

function ViewHeading({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow: string;
  title: string;
  description: string;
  action?: React.ReactNode;
}) {
  return (
    <header className="view-heading">
      <div className="eyebrow">{eyebrow}</div>
      <h1>{title}</h1>
      <p>{description}</p>
      {action}
    </header>
  );
}

function GeneticsView({
  profile,
  token,
  providers,
  datasets,
  onEvidence,
  onUpload,
  onAsk,
}: {
  profile: Profile;
  token: string;
  providers?: Health["providers"];
  datasets: Dataset[];
  onEvidence: (value: Evidence[]) => void;
  onUpload: () => void;
  onAsk: (question: string) => void;
}) {
  const panelRef = useRef<HTMLDivElement>(null);
  const runGeneration = useRef(0);
  const [search, setSearch] = useState(""),
    [selected, setSelected] = useState<Variant | null>(null),
    [model, setModel] = useState("alphagenome"),
    [context, setContext] = useState("EFO:0001187");
  const [result, setResult] = useState<MolecularResult | null>(null),
    [events, setEvents] = useState<RunEvent[]>([]),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const variants = useQuery({
    queryKey: ["variants", token, profile.id, search],
    queryFn: () =>
      request<Variant[]>(
        `/api/profiles/${profile.id}/variants?search=${encodeURIComponent(search)}`,
        token,
      ),
  });
  const contexts = useQuery({
    queryKey: ["scientific-contexts", token],
    queryFn: () =>
      request<{
        contexts: { id: string; name: string; outputs: string[] }[];
        configured: boolean;
      }>("/api/scientific-contexts", token),
    enabled: !!providers?.alphagenome,
    staleTime: 60 * 60 * 1000,
    retry: false,
  });
  const supportedContexts = contexts.data?.contexts ?? [];
  const contextAvailable = supportedContexts.some(
    (item) => item.id === context,
  );
  useEffect(() => {
    if (supportedContexts.length && !contextAvailable)
      setContext(supportedContexts[0].id);
  }, [contexts.data, contextAvailable]);
  useEffect(() => {
    runGeneration.current += 1;
    setSelected(null);
    setResult(null);
    setError("");
    setEvents([]);
    setBusy(false);
    return () => {
      runGeneration.current += 1;
    };
  }, [profile.id]);
  useLayoutEffect(() => {
    if (selected) {
      panelRef.current?.scrollIntoView({ block: "start" });
      panelRef.current?.focus({ preventScroll: true });
    }
  }, [selected]);
  async function investigate() {
    const identity = selected?.investigation_id || selected?.rsid;
    if (!identity) return;
    const generation = ++runGeneration.current;
    setBusy(true);
    setError("");
    setResult(null);
    setEvents([]);
    try {
      const { job_id } = await request<{ job_id: string }>(
        "/api/investigations",
        token,
        {
          method: "POST",
          body: JSON.stringify({
            profile_id: profile.id,
            variant_id: identity,
            model,
            context,
          }),
        },
      );
      const value = await followJob<MolecularResult>(
        job_id,
        token,
        (updates) => {
          if (generation === runGeneration.current) setEvents(updates);
        },
      );
      if (generation !== runGeneration.current) return;
      setResult(value);
      onEvidence([
        {
          id: job_id,
          category: "prediction",
          title: `${value.provider}: ${identity}`,
          url: null,
          summary: `Reference versus alternative predictions. Execution: ${value.execution}. Context: ${value.context_name || context}.`,
          limitations: value.limitations.join(" "),
          context: value.context_name || context,
          provenance: "model",
        },
      ]);
    } catch (err) {
      if (generation === runGeneration.current)
        setError((err as Error).message);
    } finally {
      if (generation === runGeneration.current) setBusy(false);
    }
  }
  return (
    <>
      <ViewHeading
        eyebrow="THE INHERITED LAYER"
        title="Your genetic findings"
        description="Inspect actual calls, then investigate a selected variant. An association is never a diagnosis."
        action={
          <Button variant="secondary" onClick={onUpload}>
            <FileUp size={15} /> Import genetic data
          </Button>
        }
      />
      <div className="panel">
        <div className="panel-header">
          <h2>Measured calls</h2>
          <label className="sr-only" htmlFor="variant-search">
            Search variants
          </label>
          <input
            id="variant-search"
            className="search-input"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search rsID or chromosome:position"
          />
        </div>
        {variants.isLoading ? (
          <p className="muted">Loading calls…</p>
        ) : (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Variant</th>
                  <th>Position</th>
                  <th>Call</th>
                  <th>Assembly</th>
                  <th>Analysis</th>
                </tr>
              </thead>
              <tbody>
                {variants.data?.map((variant, i) => (
                  <tr
                    key={`${variant.chrom}:${variant.pos}:${variant.rsid}:${i}`}
                  >
                    <td>
                      <strong>
                        {variant.rsid ||
                          `chr${variant.chrom}:${variant.pos.toLocaleString()} ${variant.ref || "?"}>${variant.alt || "?"}`}
                      </strong>
                      {!variant.rsid && (
                        <small className="variant-id-note">
                          No rsID supplied in this file
                        </small>
                      )}
                    </td>
                    <td>
                      chr{variant.chrom}:{variant.pos.toLocaleString()}
                    </td>
                    <td>
                      <span className="allele">
                        {variant.allele1 || "?"}/{variant.allele2 || "?"}
                      </span>
                    </td>
                    <td>{variant.build}</td>
                    <td>
                      {variant.investigation?.eligible === false && (
                        <span className="badge variant-status">
                          {variant.investigation.label}
                        </span>
                      )}
                      <button
                        className="text-link"
                        disabled={busy}
                        aria-label={`${variant.investigation?.eligible === false ? "View details for" : "Investigate"} ${variant.rsid || `chr${variant.chrom}:${variant.pos}`}`}
                        aria-controls="molecular-investigation"
                        onClick={() => {
                          setSelected(variant);
                          setResult(null);
                          setError("");
                          setEvents([]);
                          panelRef.current?.scrollIntoView({ block: "start" });
                        }}
                      >
                        {variant.investigation?.eligible === false ? (
                          <>
                            Details <ArrowRight size={13} />
                          </>
                        ) : (
                          <>
                            Investigate <ArrowRight size={13} />
                          </>
                        )}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!variants.data?.length && (
              <p className="empty-inline">
                No matching calls. Upload a compatible file or change the
                search.
              </p>
            )}
          </div>
        )}
      </div>
      {datasets
        .filter((d) => d.kind === "genetics")
        .map((dataset) => (
          <details className="import-report" key={dataset.id}>
            <summary>
              <ShieldCheck size={14} /> {dataset.filename} ·{" "}
              {dataset.report.accepted} accepted calls
            </summary>
            <p>
              {dataset.report.missing} missing calls · {dataset.report.excluded}{" "}
              excluded records
            </p>
            <ul>
              {dataset.report.warnings.map((warning) => (
                <li key={warning}>{warning}</li>
              ))}
            </ul>
          </details>
        ))}
      {selected && (
        <div
          className="panel investigation-panel"
          id="molecular-investigation"
          ref={panelRef}
          tabIndex={-1}
          role="region"
          aria-labelledby="investigation-title"
        >
          <div className="eyebrow">
            <Microscope size={14} /> MOLECULAR INVESTIGATION
          </div>
          <h2 id="investigation-title">
            {selected.rsid ||
              `chr${selected.chrom}:${selected.pos.toLocaleString()} ${selected.ref || "?"}>${selected.alt || "?"}`}
          </h2>
          {!selected.rsid && (
            <p className="small muted">
              This file supplied no rsID. The comparison uses the uploaded
              GRCh38 coordinates and alleles, with the reference checked before
              prediction.
            </p>
          )}
          {selected.investigation?.eligible === false && (
            <p className="notice eligibility-notice" role="status">
              {selected.investigation.reason}
            </p>
          )}
          <p>
            Compare a reference sequence with the observed alternative allele in
            an explicitly selected research context.
          </p>
          {selected.rsid === "rs143383" && (
            <div className="notice report-intro">
              <strong>Why investigate GDF5?</strong>
              <p>
                Published experiments connect this variant to how GDF5 is
                regulated in cartilage. This run asks whether changing the DNA
                letter changes a model prediction in the selected cells. It
                cannot determine the cause of knee pain.
              </p>
              <a
                href="https://pmc.ncbi.nlm.nih.gov/articles/PMC4099533/"
                target="_blank"
                rel="noreferrer"
              >
                Read the experimental evidence ↗
              </a>
            </div>
          )}
          <div className="form-grid">
            <label>
              Model
              <select
                value={model}
                disabled={busy}
                onChange={(e) => setModel(e.target.value)}
              >
                <option value="alphagenome">
                  AlphaGenome · regulatory tracks
                </option>
                <option value="evo2">Evo 2 · sequence scoring</option>
              </select>
            </label>
            {model === "alphagenome" && (
              <label>
                Research context
                <select
                  value={context}
                  onChange={(e) => setContext(e.target.value)}
                  disabled={busy || !supportedContexts.length}
                >
                  {!supportedContexts.length && (
                    <option value="">
                      {contexts.isFetching
                        ? "Loading supported contexts…"
                        : "Contexts unavailable"}
                    </option>
                  )}
                  {supportedContexts.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.name} · {item.outputs.join(" / ")}
                    </option>
                  ))}
                </select>
              </label>
            )}
          </div>
          <p className="notice small">
            {model === "alphagenome"
              ? "These are reference cell contexts, not your current tissues. A liver-cell prediction cannot explain cartilage biology. The service verifies track availability without substituting tissues."
              : "Evo 2 compares sequence likelihood without a selected tissue context. The score is not a disease probability, gene-expression direction or measurement of your methylation."}
          </p>
          <Button
            onClick={investigate}
            disabled={
              busy ||
              selected.investigation?.eligible === false ||
              !(model === "alphagenome"
                ? providers?.alphagenome && contextAvailable
                : providers?.evo2)
            }
          >
            {busy ? (
              <LoaderCircle size={15} className="spin" />
            ) : (
              <FlaskConical size={15} />
            )}
            {busy ? "Running investigation…" : "Run molecular investigation"}
          </Button>
          {!(model === "alphagenome"
            ? providers?.alphagenome
            : providers?.evo2) && (
            <p className="small muted">
              This provider is not configured. No prediction has been run.
            </p>
          )}
          {events
            .filter((event) => event.kind !== "failed")
            .map((event) => (
              <p className="small muted" key={event.id}>
                {event.agent}: {event.message}
              </p>
            ))}
          {model === "alphagenome" && contexts.error && (
            <p className="error" role="alert">
              {contexts.error.message}
            </p>
          )}
          {error && (
            <p className="error" role="alert">
              {error}
            </p>
          )}
          {result && (
            <>
              <div className="result-meta">
                <span className="badge green">{result.execution}</span>
                <span>{result.elapsed_seconds}s</span>
                <span>{result.context_name}</span>
              </div>
              <MolecularExplanation result={result} onAsk={onAsk} />
              <h3>Explore the model signals</h3>
              <p className="small muted">
                Purple is the reference sequence; pink is the alternative.
                Overlapping curves mean similar plotted predictions. Peak height
                alone is not the effect of the variant.
              </p>
              {result.tracks?.map((track, i) => (
                <div key={i}>
                  <h3>
                    {track.modality}: {track.name}
                  </h3>
                  <Chart
                    label="Reference versus alternative molecular prediction"
                    data={[
                      {
                        x: track.x,
                        y: track.reference,
                        type: "scatter",
                        mode: "lines",
                        name: "Reference",
                        line: { color: "#4338ca" },
                      },
                      {
                        x: track.x,
                        y: track.alternate,
                        type: "scatter",
                        mode: "lines",
                        name: "Alternative",
                        line: { color: "#be185d" },
                      },
                    ]}
                    layout={{
                      showlegend: true,
                      shapes: result.variant.pos
                        ? [
                            {
                              type: "line",
                              x0: result.variant.pos,
                              x1: result.variant.pos,
                              y0: 0,
                              y1: 1,
                              yref: "paper",
                              line: { color: "#6d6a7c", dash: "dot" },
                            },
                          ]
                        : [],
                      xaxis: {
                        title: {
                          text: "Genomic position · dotted line marks your selected variant",
                        },
                      },
                      yaxis: { title: { text: track.units } },
                    }}
                  />
                </div>
              ))}
              {result.delta !== undefined && (
                <div className="metric-value">
                  Δ {result.delta.toPrecision(4)}
                  <p className="small muted">
                    Sequence likelihood difference, not disease risk
                  </p>
                </div>
              )}
              <ul className="small muted">
                {result.limitations.map((text) => (
                  <li key={text}>{text}</li>
                ))}
              </ul>
            </>
          )}
        </div>
      )}
    </>
  );
}

function TrendsView({
  trends,
  onAsk,
  onUpload,
}: {
  trends?: Trends;
  onAsk: () => void;
  onUpload: () => void;
}) {
  const metricLabels: Record<string, [string, string, string]> = {
    resting_heart_rate: ["Resting heart rate", "bpm", "#1b1a2e"],
    sleep_duration: ["Sleep duration", "minutes", "#4338ca"],
    steps: ["Daily steps", "steps", "#b45309"],
  };
  return (
    <>
      <ViewHeading
        eyebrow="THE EVERYDAY LAYER"
        title="Your patterns over time"
        description="Compare measurements with your own historical baseline. Keep inherited context separate from measured change."
        action={
          <Button variant="secondary" onClick={onUpload}>
            <FileUp size={15} /> Import wearable CSV
          </Button>
        }
      />
      {!trends?.record_count ? (
        <div className="empty-state">
          <Activity size={32} />
          <h2>Add a little everyday context.</h2>
          <p>
            Wearable data is optional. Import measurements to explore your own
            trends.
          </p>
        </div>
      ) : (
        <>
          <div className="wearable-grid">
            {Object.entries(metricLabels).map(
              ([metric, [label, unit, color]]) => {
                const values = trends.daily.filter(
                  (row) => row.metric === metric,
                );
                const summary = trends.metrics[metric];
                return values.length ? (
                  <div
                    className={`panel wearable-panel wearable-${metric}`}
                    key={metric}
                  >
                    <div className="panel-header">
                      <div>
                        <div className="eyebrow">{label.toUpperCase()}</div>
                        <h2>
                          {summary.latest.toFixed(metric === "steps" ? 0 : 1)}{" "}
                          <span className="muted small">{unit}</span>
                        </h2>
                      </div>
                      <div className="small muted">
                        {summary.baseline !== null
                          ? `Historical median ${summary.baseline.toFixed(1)} · ${summary.baseline_days} days`
                          : "At least 7 historical days needed"}
                      </div>
                    </div>
                    <Chart
                      label={`${label} over time`}
                      data={[
                        {
                          x: values.map((row) => row.day),
                          y: values.map((row) => row.value),
                          type:
                            metric === "resting_heart_rate" ? "scatter" : "bar",
                          mode: "lines+markers",
                          line: { color, width: 2 },
                          marker: { size: 5, color },
                          fill: "none",
                          fillcolor: `${color}0d`,
                        },
                      ]}
                      layout={
                        summary.baseline !== null
                          ? {
                              shapes: [
                                {
                                  type: "line",
                                  xref: "paper",
                                  x0: 0,
                                  x1: 1,
                                  y0: summary.baseline,
                                  y1: summary.baseline,
                                  line: {
                                    color: "#0f766e",
                                    dash: "dot",
                                    width: 1,
                                  },
                                },
                              ],
                            }
                          : {}
                      }
                    />
                  </div>
                ) : null;
              },
            )}
          </div>
          <div className="notice">
            <CircleHelp size={17} />
            <span>
              Patterns can suggest useful questions. They do not establish
              cause, and DNA does not automatically explain a high heart rate.
            </span>
          </div>
          <Button onClick={onAsk}>
            <Sparkles size={15} /> Help me understand these patterns
          </Button>
        </>
      )}
    </>
  );
}

function FamilyView({
  profile,
  profiles,
  token,
  onEvidence,
  onSelectProfile,
}: {
  profile: Profile;
  profiles: Profile[];
  token: string;
  onEvidence: (value: Evidence[]) => void;
  onSelectProfile: (id: string) => void;
}) {
  const [partnerId, setPartnerId] = useState("");
  const hasDNA = (p: Profile) => (p.data_coverage?.genetic_calls ?? 0) > 0;
  const carrierExample = profiles.find(
    (p) => p.public_dataset_key === "family-na12043",
  );
  const partner =
    profiles.find(
      (p) => p.id === partnerId && p.id !== profile.id && hasDNA(p),
    ) ||
    profiles.find(
      (p) =>
        p.public_dataset_key === profile.recommended_partner_key &&
        p.id !== profile.id &&
        hasDNA(p),
    ) ||
    profiles.find((p) => p.id !== profile.id && hasDNA(p));
  const comparison = useQuery({
    queryKey: ["family", token, profile.id, partner?.id],
    queryFn: () =>
      request<FamilyResult>("/api/family-comparisons", token, {
        method: "POST",
        body: JSON.stringify({ profile_a: profile.id, profile_b: partner!.id }),
      }),
    enabled: !!partner && hasDNA(profile),
  });
  useEffect(() => {
    onEvidence(comparison.data?.evidence || []);
  }, [comparison.data, onEvidence]);
  return (
    <>
      <ViewHeading
        eyebrow="THE NEXT GENERATION"
        title="Understand inheritance together"
        description="Compare two profiles for specifically supported recessive alleles. This is a conditional inheritance tool, not a compatibility score."
      />
      {carrierExample &&
        profile.public_dataset_key !== "family-na12043" &&
        profile.public_dataset_key !== "family-na20332" && (
          <div className="notice report-intro">
            <strong>Try a covered family example</strong>
            <p>
              NA12043 and NA20332 have actual G/A calls at the supported PAH
              allele. Their hypothetical pairing demonstrates the conditional
              inheritance calculation.
            </p>
            <Button
              variant="secondary"
              onClick={() => onSelectProfile(carrierExample.id)}
            >
              Use measured carrier example <ArrowRight size={14} />
            </Button>
          </div>
        )}
      {!hasDNA(profile) && (
        <p className="notice">
          This profile has no genetic data. Choose a DNA profile to compare
          inheritance; wearable or methylation measurements do not supply
          genotypes.
        </p>
      )}
      <p className="small muted">
        Only profiles with genetic data can be selected. Unmeasured alleles are
        not negative results.
      </p>
      {profile.demo_scenario === "family" && (
        <p className="notice">
          Hypothetical pairing of two separate public reference samples; no real
          couple or pregnancy is represented.
        </p>
      )}
      <div className="couple-picker">
        <div>
          <span className="avatar">{profile.name[0]}</span>
          <strong>{profile.name}</strong>
        </div>
        <HeartHandshake size={25} />
        <div>
          <span className="avatar partner-avatar">
            {partner?.name[0] || "?"}
          </span>
          <label className="sr-only" htmlFor="partner">
            Partner profile
          </label>
          <select
            id="partner"
            value={partner?.id || ""}
            onChange={(e) => setPartnerId(e.target.value)}
          >
            {profiles
              .filter((p) => p.id !== profile.id)
              .map((p) => (
                <option value={p.id} key={p.id} disabled={!hasDNA(p)}>
                  {p.name}
                  {!hasDNA(p) ? " · no DNA" : ""}
                </option>
              ))}
          </select>
        </div>
      </div>
      {!partner && (
        <div className="notice">
          Create a second profile and upload their genetic data to compare.
        </div>
      )}
      {comparison.error && <p className="error">{comparison.error.message}</p>}
      {comparison.data && (
        <>
          <div className="scope-note">
            <ShieldCheck size={16} />
            <span>{comparison.data.scope}</span>
          </div>
          {comparison.data.conditions.every(
            (c) => !c.parent_a.genotype && !c.parent_b.genotype,
          ) && (
            <div className="notice report-intro">
              <strong>
                These files do not cover the supported family alleles.
              </strong>
              <p>
                No carrier status or offspring probability can be inferred.
                Choose the measured carrier example above, or add genetic
                results that include these sites.
              </p>
            </div>
          )}
          {comparison.data.conditions
            .filter((c) => c.parent_a.genotype || c.parent_b.genotype)
            .map((condition) => (
              <div className="panel family-card" key={condition.gene}>
                <div className="panel-header">
                  <div>
                    <span className="eyebrow">
                      {condition.gene} · {condition.rsid}
                    </span>
                    <h2>{condition.condition}</h2>
                  </div>
                  <span
                    className={`badge ${condition.affected_genotype_probability !== null ? "amber" : ""}`}
                  >
                    {condition.affected_genotype_probability !== null
                      ? "Shared assessed allele"
                      : "Limited assessment"}
                  </span>
                </div>
                <div className="parent-status">
                  <div>
                    <span>{profile.name}</span>
                    <strong>{condition.parent_a.genotype || "Unknown"}</strong>
                    <p>{condition.parent_a.status.replaceAll("_", " ")}</p>
                  </div>
                  <div>
                    <span>{partner?.name}</span>
                    <strong>{condition.parent_b.genotype || "Unknown"}</strong>
                    <p>{condition.parent_b.status.replaceAll("_", " ")}</p>
                  </div>
                </div>
                {condition.affected_genotype_probability !== null && (
                  <>
                    <div
                      className="inheritance-grid"
                      aria-label="Conditional inheritance under the assessed recessive model"
                    >
                      {["A/A", "A/a", "a/A", "a/a"].map((genotype) => (
                        <div key={genotype}>
                          {genotype}
                          <small>25%</small>
                        </div>
                      ))}
                    </div>
                    <div className="inheritance-bars">
                      <span className="inheritance-reference" />
                      <span className="inheritance-carrier" />
                      <span className="inheritance-carrier" />
                      <span className="inheritance-affected" />
                    </div>
                    <div className="inheritance-legend">
                      <span>25% two reference alleles</span>
                      <span>50% one assessed allele</span>
                      <strong>25% two assessed alleles</strong>
                    </div>
                  </>
                )}
                <p className="small muted">{condition.explanation}</p>
              </div>
            ))}
          {comparison.data.conditions.some(
            (c) => !c.parent_a.genotype && !c.parent_b.genotype,
          ) && (
            <details className="import-report">
              <summary>
                {
                  comparison.data.conditions.filter(
                    (c) => !c.parent_a.genotype && !c.parent_b.genotype,
                  ).length
                }{" "}
                conditions are not covered by these files
              </summary>
              <p>
                No genotype was supplied at these specific alleles. They remain
                unassessed, rather than negative.
              </p>
              <ul>
                {comparison.data.conditions
                  .filter((c) => !c.parent_a.genotype && !c.parent_b.genotype)
                  .map((c) => (
                    <li key={c.gene}>
                      {c.condition} · {c.gene} · {c.rsid}
                    </li>
                  ))}
              </ul>
            </details>
          )}
          <p className="research-note">
            Confirm important raw-data findings with an appropriate clinical
            service before reproductive decisions. No individual child’s health
            is predicted.
          </p>
        </>
      )}
    </>
  );
}

function MethylationView({
  profile,
  token,
  onEvidence,
  onImported,
  onAsk,
  onUpload,
  onSelectProfile,
}: {
  profile: Profile;
  token: string;
  onEvidence: (value: Evidence[]) => void;
  onImported: () => void;
  onAsk: (question: string) => void;
  onUpload: () => void;
  onSelectProfile: (id: string) => void;
}) {
  const client = useQueryClient(),
    [error, setError] = useState("");
  const data = useQuery({
    queryKey: ["methylation", token, profile.id],
    queryFn: () =>
      request<Methylation>(`/api/profiles/${profile.id}/methylation`, token),
  });
  useEffect(() => {
    onEvidence(data.data?.evidence || []);
  }, [data.data, onEvidence]);
  async function sample() {
    try {
      await request(`/api/profiles/${profile.id}/demo-methylation`, token, {
        method: "POST",
      });
      client.invalidateQueries({ queryKey: ["methylation"] });
      onImported();
    } catch (err) {
      setError((err as Error).message);
    }
  }
  async function bloodDemo() {
    try {
      const value = await request<{ profile: Profile }>(
        "/api/demo/methylation-report",
        token,
        { method: "POST" },
      );
      await client.invalidateQueries({ queryKey: ["profiles"] });
      onSelectProfile(value.profile.id);
    } catch (err) {
      setError((err as Error).message);
    }
  }
  return (
    <>
      <ViewHeading
        eyebrow="AN OPTIONAL LAYER"
        title="Measured methylation"
        description="Turn measured methylation into an understandable report, check what your sample supports, and compare compatible repeat tests. This layer is optional."
      />
      <div className="notice report-intro">
        <strong>What you get</strong>
        <p>
          A published blood methylation-age estimate when input checks pass, an
          explanation of its limits, and a record you can compare with a future
          test. DNA sequencing alone cannot supply these measurements.
        </p>
        <Button variant="secondary" onClick={bloodDemo}>
          Explore a public blood report <ArrowRight size={14} />
        </Button>
        <p className="small muted">
          Opens a separate real GEO blood sample, with its own source identity.
          It is not matched to the demo DNA or wearables.
        </p>
      </div>
      {data.isPending && (
        <p className="muted">Checking sample coverage and report inputs…</p>
      )}
      {data.error && (
        <p className="error" role="alert">
          {data.error.message}
        </p>
      )}
      {!!data.data?.comparisons.length && (
        <MethylationTimeline
          comparisons={data.data.comparisons}
          samples={data.data.samples}
        />
      )}
      {!data.data?.samples.length ? (
        <div className="optional-empty">
          <div className="optional-illustration">
            <Fingerprint size={86} strokeWidth={0.7} />
          </div>
          <span className="badge">ENTIRELY OPTIONAL</span>
          <h2>DNA is enough to start.</h2>
          <p>
            Methylation measurements can add another layer of context if you
            already have them. DNA-based predictions do not measure your current
            epigenome.
          </p>
          <div className="inline-actions">
            <Button variant="secondary" onClick={onUpload}>
              <Plus size={15} /> Add an existing sample
            </Button>
            {profile.provenance === "synthetic" && (
              <Button variant="ghost" onClick={sample}>
                Explore a synthetic sample <ArrowRight size={14} />
              </Button>
            )}
            {(profile.public_dataset_key === "hg002" ||
              profile.genetic_sample_key === "hg002") && (
              <Button variant="ghost" onClick={sample}>
                Explore HG002 public methylation <ArrowRight size={14} />
              </Button>
            )}
          </div>
        </div>
      ) : (
        data.data.samples.map((sample) => {
          const probes = sample.probes.slice(0, 60);
          return (
            <div className="panel" key={sample.dataset_id}>
              <div className="panel-header">
                <div>
                  <span className="eyebrow">
                    {sample.metadata.provenance === "synthetic"
                      ? "SYNTHETIC SAMPLE"
                      : sample.metadata.provenance === "public_reference"
                        ? "PUBLIC MEASUREMENT"
                        : "UPLOADED MEASUREMENT"}
                  </span>
                  <h2>{sample.metadata.tissue}</h2>
                  <p className="small muted">
                    {sample.metadata.assay} · {sample.metadata.collected_at} ·{" "}
                    {sample.report.accepted.toLocaleString()}{" "}
                    {sample.metadata.provenance === "public_reference"
                      ? "sites"
                      : "probes"}
                  </p>
                </div>
                <EvidenceBadge category="measured" />
              </div>
              <MethylationReport sample={sample} onAsk={onAsk} />
              <div className="sample-metadata">
                {[
                  ["Tissue", sample.metadata.tissue],
                  ["Assay", sample.metadata.assay],
                  ["Assembly", sample.metadata.build],
                  [
                    "Collected",
                    sample.metadata.collection_year
                      ? `${sample.metadata.collection_year} (year only)`
                      : sample.metadata.collected_at || "Not reported",
                  ],
                ].map(([label, value]) => (
                  <div key={label}>
                    <span className="eyebrow">{label}</span>
                    <strong>{value}</strong>
                  </div>
                ))}
              </div>
              {sample.metadata.source_url && (
                <p className="small">
                  <a
                    href={sample.metadata.source_url}
                    target="_blank"
                    rel="noreferrer"
                  >
                    {sample.metadata.source_name} ↗
                  </a>
                  <br />
                  {sample.metadata.selection}
                  <br />
                  {sample.metadata.limitations}
                </p>
              )}
              <div className="methylation-meaning">
                <div>
                  <div className="eyebrow">WHAT DOES THIS MEAN?</div>
                  <p>
                    Beta describes the measured methylation fraction at each
                    assayed site. Higher or lower values are not automatically
                    healthy or unhealthy.
                  </p>
                </div>
                <div>
                  <div className="eyebrow">WHAT CAN THIS SAMPLE SUPPORT?</div>
                  <p>
                    {sample.metadata.tissue.toLowerCase().includes("cell line")
                      ? "This regional cell-line sample demonstrates measured methylation near GDF5. It cannot provide a personal aging score, cartilage assessment or a lifestyle prescription."
                      : "These are sample-specific measurements. A personal report needs a validated model for this tissue and assay, coverage of its required sites and quality-control information."}
                  </p>
                </div>
                <Button
                  variant="secondary"
                  onClick={() =>
                    onAsk(
                      "Explain my measured methylation results. What does beta mean, what can this exact sample tell me alongside my DNA, and what additional data is needed for a useful personal report?",
                    )
                  }
                >
                  <MessageSquare size={14} />
                  Explain this sample
                </Button>
              </div>
              <Chart
                label="Measured site methylation beta values"
                data={[
                  {
                    type: "scatter",
                    mode: "lines",
                    x: probes.flatMap((p) => [
                      p.pos ?? p.cpg_id,
                      p.pos ?? p.cpg_id,
                      null,
                    ]),
                    y: probes.flatMap((p) => [0, p.beta, null]),
                    line: { color: "#0f766e45", width: 1 },
                    hoverinfo: "skip",
                  },
                  {
                    type: "scatter",
                    mode: "markers",
                    x: probes.map((p) => p.pos ?? p.cpg_id),
                    y: probes.map((p) => p.beta),
                    text: probes.map((p) => p.cpg_id),
                    marker: {
                      color: "#0f766e",
                      size: 6,
                    },
                    hovertemplate: "%{text}<br>Beta %{y:.3f}<extra></extra>",
                  },
                ]}
                layout={{
                  yaxis: {
                    range: [0, 1],
                    title: { text: "Methylation beta value" },
                  },
                  xaxis: { showticklabels: false },
                }}
              />
              <p className="small muted">
                Showing {probes.length} of {sample.report.accepted} measured
                sites. The table previews the first{" "}
                {Math.min(12, probes.length)}.
              </p>
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>Probe</th>
                      <th>Position</th>
                      <th>Beta value</th>
                      <th aria-label="Methylation level" />
                    </tr>
                  </thead>
                  <tbody>
                    {probes.slice(0, 12).map((p) => (
                      <tr key={p.cpg_id}>
                        <td>{p.cpg_id}</td>
                        <td>{p.pos?.toLocaleString() || "Not supplied"}</td>
                        <td>{p.beta.toFixed(3)}</td>
                        <td>
                          <span className="beta-bar">
                            <i style={{ width: `${p.beta * 100}%` }} />
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          );
        })
      )}
      {error && <p className="error">{error}</p>}
      {!!data.data?.samples.length && !data.data.comparisons.length && (
        <MethylationTimeline
          comparisons={data.data.comparisons || []}
          samples={data.data.samples}
        />
      )}
      <div className="notice">
        <CircleHelp size={17} />
        <span>
          These values describe the sampled tissue. A research methylation-age
          estimate does not diagnose disease or establish a personalized
          lifestyle prescription.
        </span>
      </div>
    </>
  );
}
