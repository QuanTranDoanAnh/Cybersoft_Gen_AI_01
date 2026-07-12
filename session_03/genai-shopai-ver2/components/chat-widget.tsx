"use client";

import { Bot, MessageCircle, Plus, Send, Trash2, X } from "lucide-react";
import { FormEvent, useEffect, useRef, useState } from "react";
import { deleteConversation, getConversation, listConversations, sendChatMessage } from "@/utils/api";
import type { AuthUser, ChatMessage, ChatMode, ConversationSummary } from "@/utils/types";

const starterPrompts = [
  "Tôi muốn mua tai nghe dưới 500k",
  "Cái màu đen còn hàng không?",
  "Kiểm tra đơn OD1001",
  "Chính sách đổi trả thế nào?"
];

type ChatWidgetProps = {
  authToken: string | null;
  user: AuthUser | null;
};

function welcomeMessage(mode: ChatMode, hasUser: boolean): ChatMessage[] {
  if (!hasUser) {
    return [
      {
        role: "assistant",
        content: "Bạn đăng nhập hoặc đăng ký trước nhé. Bản v2 sẽ lưu từng cuộc trò chuyện theo tài khoản của bạn."
      }
    ];
  }

  return [
    {
      role: "assistant",
      content:
        mode === "with_context"
          ? "Mình đang ở chế độ nhớ ngữ cảnh. Bạn có thể hỏi nối tiếp bằng các cụm như 'cái đó' hoặc 'màu đen'."
          : "Mình đang ở chế độ không nhớ ngữ cảnh. Mỗi câu hỏi vẫn được lưu, nhưng model chỉ xử lý câu mới nhất."
    }
  ];
}

export function ChatWidget({ authToken, user }: ChatWidgetProps) {
  const [open, setOpen] = useState(false);
  const [mode, setMode] = useState<ChatMode>("with_context");
  const [conversationId, setConversationId] = useState<string>();
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>(welcomeMessage("with_context", false));
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  async function refreshConversations(token = authToken) {
    if (!token) {
      setConversations([]);
      return;
    }

    const response = await listConversations(token);
    setConversations(response.conversations);
  }

  useEffect(() => {
    setConversationId(undefined);
    setMessages(welcomeMessage(mode, Boolean(user)));
    refreshConversations().catch(() => setConversations([]));
  }, [authToken, user?.id]);

  async function submitMessage(message: string) {
    const trimmed = message.trim();
    if (!trimmed || loading) return;

    if (!authToken) {
      setMessages(welcomeMessage(mode, false));
      return;
    }

    setMessages((current) => [...current, { role: "user", content: trimmed }]);
    setInput("");
    setLoading(true);

    try {
      const response = await sendChatMessage(
        {
          message: trimmed,
          mode,
          conversation_id: conversationId
        },
        authToken
      );
      setConversationId(response.conversation_id);
      setMode(response.mode);
      setMessages(response.messages.length ? response.messages : [{ role: "assistant", content: response.reply }]);
      await refreshConversations(authToken);
    } catch (error) {
      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          content: error instanceof Error ? `Lỗi kết nối API: ${error.message}` : "Lỗi kết nối API"
        }
      ]);
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  }

  async function loadConversation(nextConversationId: string) {
    if (!authToken || !nextConversationId) {
      startNewChat();
      return;
    }

    setHistoryLoading(true);
    try {
      const conversation = await getConversation(nextConversationId, authToken);
      setConversationId(conversation.id);
      setMode(conversation.mode);
      setMessages(conversation.messages.length ? conversation.messages : welcomeMessage(conversation.mode, true));
    } catch (error) {
      setMessages([
        {
          role: "assistant",
          content: error instanceof Error ? `Không tải được cuộc trò chuyện: ${error.message}` : "Không tải được cuộc trò chuyện."
        }
      ]);
    } finally {
      setHistoryLoading(false);
    }
  }

  function startNewChat(nextMode = mode) {
    setMode(nextMode);
    setConversationId(undefined);
    setMessages(welcomeMessage(nextMode, Boolean(user)));
    setInput("");
  }

  async function removeCurrentConversation() {
    if (!authToken || !conversationId) return;

    const deletingId = conversationId;
    startNewChat();
    try {
      await deleteConversation(deletingId, authToken);
      await refreshConversations(authToken);
    } catch (error) {
      setMessages([
        {
          role: "assistant",
          content: error instanceof Error ? `Không xoá được cuộc trò chuyện: ${error.message}` : "Không xoá được cuộc trò chuyện."
        }
      ]);
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    submitMessage(input);
  }

  function switchMode(nextMode: ChatMode) {
    startNewChat(nextMode);
  }

  if (!open) {
    return (
      <button
        className="fixed bottom-5 right-5 z-30 inline-flex h-14 w-14 items-center justify-center rounded-full bg-brand-orange text-white shadow-panel transition hover:bg-orange-600"
        onClick={() => setOpen(true)}
        aria-label="Mở chat"
      >
        <MessageCircle className="h-6 w-6" />
      </button>
    );
  }

  return (
    <section className="fixed bottom-4 right-4 z-30 flex h-[min(680px,calc(100vh-32px))] w-[min(420px,calc(100vw-32px))] flex-col overflow-hidden rounded-lg border border-slate-200 bg-white shadow-panel">
      <header className="flex h-16 items-center justify-between border-b border-slate-200 bg-brand-ink px-4 text-white">
        <div className="flex min-w-0 items-center gap-3">
          <div className="grid h-9 w-9 place-items-center rounded-md bg-white/10">
            <Bot className="h-5 w-5" />
          </div>
          <div className="min-w-0">
            <h2 className="truncate text-sm font-bold">ShopAI CSKH v2</h2>
            <p className="truncate text-xs text-slate-300">
              {user ? `${user.display_name} · ${mode === "with_context" ? "Nhớ ngữ cảnh" : "Không nhớ"}` : "Chưa đăng nhập"}
            </p>
          </div>
        </div>
        <button className="rounded-md p-2 text-slate-300 hover:bg-white/10 hover:text-white" onClick={() => setOpen(false)} aria-label="Đóng chat">
          <X className="h-5 w-5" />
        </button>
      </header>

      <div className="grid grid-cols-2 gap-2 border-b border-slate-200 p-3">
        <button
          className={`h-9 rounded-md text-sm font-semibold ${mode === "with_context" ? "bg-brand-orange text-white" : "bg-slate-100 text-slate-700 hover:bg-slate-200"}`}
          onClick={() => switchMode("with_context")}
        >
          Nhớ ngữ cảnh
        </button>
        <button
          className={`h-9 rounded-md text-sm font-semibold ${mode === "without_context" ? "bg-brand-orange text-white" : "bg-slate-100 text-slate-700 hover:bg-slate-200"}`}
          onClick={() => switchMode("without_context")}
        >
          Không nhớ
        </button>
      </div>

      <div className="border-b border-slate-200 p-3">
        <div className="flex gap-2">
          <select
            className="h-10 min-w-0 flex-1 rounded-md border border-slate-200 bg-white px-3 text-sm outline-none focus:border-brand-orange disabled:bg-slate-100"
            value={conversationId || ""}
            onChange={(event) => loadConversation(event.target.value)}
            disabled={!authToken || historyLoading}
          >
            <option value="">Cuộc trò chuyện mới</option>
            {conversations.map((conversation) => (
              <option key={conversation.id} value={conversation.id}>
                {conversation.title}
              </option>
            ))}
          </select>
          <button
            className="grid h-10 w-10 place-items-center rounded-md border border-slate-200 text-slate-700 hover:border-brand-orange hover:text-brand-orange disabled:bg-slate-100 disabled:text-slate-300"
            onClick={() => startNewChat()}
            disabled={!authToken}
            aria-label="Tạo cuộc trò chuyện mới"
          >
            <Plus className="h-4 w-4" />
          </button>
          <button
            className="grid h-10 w-10 place-items-center rounded-md border border-slate-200 text-slate-700 hover:border-rose-300 hover:text-rose-600 disabled:bg-slate-100 disabled:text-slate-300"
            onClick={removeCurrentConversation}
            disabled={!authToken || !conversationId}
            aria-label="Xoá cuộc trò chuyện"
          >
            <Trash2 className="h-4 w-4" />
          </button>
        </div>
      </div>

      <div className="scrollbar-thin flex-1 space-y-3 overflow-y-auto bg-slate-50 px-4 py-4">
        {messages.map((message, index) => (
          <div key={`${message.role}-${index}`} className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}>
            <div
              className={`max-w-[82%] whitespace-pre-line rounded-lg px-3 py-2 text-sm leading-6 ${message.role === "user"
                  ? "bg-brand-orange text-white"
                  : "border border-slate-200 bg-white text-slate-800"
                }`}
            >
              {message.content}
            </div>
          </div>
        ))}
        {loading || historyLoading ? (
          <div className="flex justify-start">
            <div className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-500">
              {historyLoading ? "Đang tải lịch sử..." : "Đang trả lời..."}
            </div>
          </div>
        ) : null}
      </div>

      <div className="border-t border-slate-200 bg-white p-3">
        <div className="mb-3 flex gap-2 overflow-x-auto">
          {starterPrompts.map((prompt) => (
            <button
              key={prompt}
              className="h-8 shrink-0 rounded-md border border-slate-200 px-3 text-xs font-medium text-slate-600 hover:border-brand-orange hover:text-brand-orange disabled:bg-slate-100 disabled:text-slate-300"
              onClick={() => submitMessage(prompt)}
              disabled={!authToken || loading}
            >
              {prompt}
            </button>
          ))}
        </div>
        <form className="flex gap-2" onSubmit={handleSubmit}>
          <input
            ref={inputRef}
            className="h-11 min-w-0 flex-1 rounded-md border border-slate-200 px-3 text-sm outline-none focus:border-brand-orange disabled:bg-slate-100"
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder={authToken ? "Nhập câu hỏi..." : "Đăng nhập để dùng chat có memory"}
            disabled={!authToken}
          />
          <button
            className="grid h-11 w-11 place-items-center rounded-md bg-brand-ink text-white hover:bg-slate-700 disabled:bg-slate-300"
            disabled={loading || !authToken || !input.trim()}
            aria-label="Gửi"
          >
            <Send className="h-4 w-4" />
          </button>
        </form>
      </div>
    </section>
  );
}
