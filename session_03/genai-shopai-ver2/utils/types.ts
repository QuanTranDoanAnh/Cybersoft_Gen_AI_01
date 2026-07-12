export type Product = {
  id: string;
  name: string;
  slug: string;
  description: string;
  price: number;
  original_price?: number | null;
  category: string;
  rating: number;
  sold_count: number;
  stock: number;
  image_url: string;
  variants: string[];
  tags: string[];
};

export type ProductListResponse = {
  products: Product[];
  categories: string[];
};

export type CartItem = {
  product: Product;
  quantity: number;
};

export type OrderItem = {
  product_id: string;
  product_name: string;
  quantity: number;
  price: number;
};

export type Order = {
  id: string;
  customer_name: string;
  phone: string;
  address: string;
  status: string;
  total_amount: number;
  items: OrderItem[];
  created_at: string;
};

export type ChatMode = "with_context" | "without_context";

export type ChatMessage = {
  role: "user" | "assistant";
  content: string;
};

export type ChatResponse = {
  conversation_id: string;
  conversation_title: string;
  mode: ChatMode;
  reply: string;
  used_context: boolean;
  messages: ChatMessage[];
};

export type AuthUser = {
  id: string;
  email: string;
  display_name: string;
};

export type AuthResponse = {
  access_token: string;
  token_type: "bearer";
  user: AuthUser;
};

export type ConversationSummary = {
  id: string;
  title: string;
  mode: ChatMode;
  created_at: string;
  updated_at: string;
  message_count: number;
  last_message?: string | null;
};

export type ConversationDetail = ConversationSummary & {
  messages: ChatMessage[];
};

export type ConversationListResponse = {
  conversations: ConversationSummary[];
};
