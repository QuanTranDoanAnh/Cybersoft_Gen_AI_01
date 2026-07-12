import type {
  AuthResponse,
  AuthUser,
  ChatMode,
  ChatResponse,
  ConversationDetail,
  ConversationListResponse,
  ConversationSummary,
  Order,
  ProductListResponse
} from "./types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

async function request<T>(path: string, options?: RequestInit & { token?: string }): Promise<T> {
  const { token, ...fetchOptions } = options || {};
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...fetchOptions,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(fetchOptions.headers || {})
    }
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed with status ${response.status}`);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  const text = await response.text();
  return (text ? JSON.parse(text) : undefined) as T;
}

export function getProducts(search: string, category: string) {
  const params = new URLSearchParams();
  if (search.trim()) params.set("search", search.trim());
  if (category && category !== "Tất cả") params.set("category", category);
  const query = params.toString();
  return request<ProductListResponse>(`/api/products${query ? `?${query}` : ""}`);
}

export function createOrder(payload: {
  customer_name: string;
  phone: string;
  address: string;
  items: { product_id: string; quantity: number }[];
}) {
  return request<Order>("/api/orders", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function sendChatMessage(payload: {
  message: string;
  mode: ChatMode;
  conversation_id?: string;
}, token: string) {
  return request<ChatResponse>("/api/chat", {
    method: "POST",
    token,
    body: JSON.stringify(payload)
  });
}

export function register(payload: {
  email: string;
  password: string;
  display_name: string;
}) {
  return request<AuthResponse>("/api/auth/register", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function login(payload: {
  email: string;
  password: string;
}) {
  return request<AuthResponse>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function getMe(token: string) {
  return request<AuthUser>("/api/auth/me", { token });
}

export function listConversations(token: string) {
  return request<ConversationListResponse>("/api/conversations", { token });
}

export function getConversation(conversationId: string, token: string) {
  return request<ConversationDetail>(`/api/conversations/${conversationId}`, { token });
}

export function updateConversation(conversationId: string, token: string, payload: {
  title?: string;
  mode?: ChatMode;
}) {
  return request<ConversationSummary>(`/api/conversations/${conversationId}`, {
    method: "PATCH",
    token,
    body: JSON.stringify(payload)
  });
}

export function deleteConversation(conversationId: string, token: string) {
  return request<void>(`/api/conversations/${conversationId}`, {
    method: "DELETE",
    token
  });
}
