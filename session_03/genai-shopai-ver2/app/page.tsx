"use client";

import { Bot, Filter, Search, ShieldCheck, ShoppingCart, SlidersHorizontal, Sparkles, Truck, X } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { AuthPanel } from "@/components/auth-panel";
import { CartDrawer } from "@/components/cart-drawer";
import { ChatWidget } from "@/components/chat-widget";
import { ProductCard } from "@/components/product-card";
import { getMe, getProducts } from "@/utils/api";
import { formatVnd } from "@/utils/format";
import type { AuthResponse, AuthUser, CartItem, Order, Product } from "@/utils/types";

export default function HomePage() {
  const [products, setProducts] = useState<Product[]>([]);
  const [categories, setCategories] = useState<string[]>(["Tất cả"]);
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("Tất cả");
  const [cartOpen, setCartOpen] = useState(false);
  const [cartItems, setCartItems] = useState<CartItem[]>([]);
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(null);
  const [lastOrder, setLastOrder] = useState<Order | null>(null);
  const [authToken, setAuthToken] = useState<string | null>(null);
  const [authUser, setAuthUser] = useState<AuthUser | null>(null);
  const [authReady, setAuthReady] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const savedToken = window.localStorage.getItem("shopai_token");
    if (!savedToken) {
      setAuthReady(true);
      return;
    }

    setAuthToken(savedToken);
    getMe(savedToken)
      .then(setAuthUser)
      .catch(() => {
        window.localStorage.removeItem("shopai_token");
        setAuthToken(null);
        setAuthUser(null);
      })
      .finally(() => {
        setAuthReady(true);
      });
  }, []);

  useEffect(() => {
    if (!authUser) {
      setProducts([]);
      setCategories(["Tất cả"]);
      setLoading(false);
      setError("");
      return;
    }

    let ignore = false;
    setLoading(true);
    setError("");

    getProducts(search, category)
      .then((response) => {
        if (ignore) return;
        setProducts(response.products);
        setCategories(response.categories);
      })
      .catch((loadError) => {
        if (ignore) return;
        setError(loadError instanceof Error ? loadError.message : "Không tải được sản phẩm");
      })
      .finally(() => {
        if (!ignore) setLoading(false);
      });

    return () => {
      ignore = true;
    };
  }, [authUser, search, category]);

  const cartQuantity = cartItems.reduce((sum, item) => sum + item.quantity, 0);
  const cartTotal = cartItems.reduce((sum, item) => sum + item.product.price * item.quantity, 0);

  const featuredTags = useMemo(() => ["Tai nghe dưới 500k", "Đồ đi làm", "Bán chạy", "Giao nhanh"], []);

  function addToCart(product: Product) {
    setCartItems((current) => {
      const existing = current.find((item) => item.product.id === product.id);
      if (existing) {
        return current.map((item) =>
          item.product.id === product.id ? { ...item, quantity: Math.min(item.quantity + 1, product.stock) } : item
        );
      }
      return [...current, { product, quantity: 1 }];
    });
    setCartOpen(true);
  }

  function updateQuantity(productId: string, quantity: number) {
    setCartItems((current) =>
      current
        .map((item) => (item.product.id === productId ? { ...item, quantity: Math.max(0, Math.min(quantity, item.product.stock)) } : item))
        .filter((item) => item.quantity > 0)
    );
  }

  function removeItem(productId: string) {
    setCartItems((current) => current.filter((item) => item.product.id !== productId));
  }

  function handleAuthenticated(response: AuthResponse) {
    window.localStorage.setItem("shopai_token", response.access_token);
    setAuthToken(response.access_token);
    setAuthUser(response.user);
    setAuthReady(true);
  }

  function handleLogout() {
    window.localStorage.removeItem("shopai_token");
    setAuthToken(null);
    setAuthUser(null);
    setCartItems([]);
    setCartOpen(false);
    setSelectedProduct(null);
    setLastOrder(null);
    setSearch("");
    setCategory("Tất cả");
  }

  if (!authReady) {
    return (
      <main className="grid min-h-screen place-items-center bg-brand-soft px-4">
        <div className="flex items-center gap-3 rounded-lg border border-slate-200 bg-white px-5 py-4 text-sm font-bold text-slate-700 shadow-sm">
          <Bot className="h-5 w-5 text-brand-orange" />
          Đang kiểm tra phiên đăng nhập...
        </div>
      </main>
    );
  }

  if (!authUser) {
    return (
      <main className="min-h-screen bg-brand-soft">
        <section className="mx-auto grid min-h-screen max-w-6xl gap-8 px-4 py-8 lg:grid-cols-[1.1fr_0.9fr] lg:items-center">
          <div>
            <div className="mb-5 inline-flex items-center gap-2 rounded-md bg-orange-50 px-3 py-2 text-sm font-bold text-brand-orange">
              <ShieldCheck className="h-4 w-4" />
              ShopAI Assistant v2
            </div>
            <h1 className="max-w-3xl text-4xl font-extrabold leading-tight text-slate-950 md:text-5xl">
              Đăng nhập để vào nền tảng ShopAI.
            </h1>
            <p className="mt-4 max-w-2xl text-sm leading-6 text-slate-600">
              Tài khoản giúp ShopAI lưu từng cuộc trò chuyện, mở lại lịch sử tư vấn và giữ ngữ cảnh riêng cho bạn.
            </p>
            <div className="mt-6 grid max-w-2xl gap-3 sm:grid-cols-3">
              <div className="rounded-lg border border-slate-200 bg-white p-4">
                <p className="text-sm font-bold text-slate-950">Account</p>
                <p className="mt-1 text-sm leading-5 text-slate-500">Đăng ký hoặc đăng nhập bằng email.</p>
              </div>
              <div className="rounded-lg border border-slate-200 bg-white p-4">
                <p className="text-sm font-bold text-slate-950">Memory</p>
                <p className="mt-1 text-sm leading-5 text-slate-500">Context được tách theo từng user.</p>
              </div>
              <div className="rounded-lg border border-slate-200 bg-white p-4">
                <p className="text-sm font-bold text-slate-950">LangChain</p>
                <p className="mt-1 text-sm leading-5 text-slate-500">Chat history chạy qua chain riêng.</p>
              </div>
            </div>
          </div>

          <div className="mx-auto w-full max-w-md">
            <AuthPanel user={null} onAuthenticated={handleAuthenticated} onLogout={handleLogout} />
          </div>
        </section>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-brand-soft pb-24">
      <header className="sticky top-0 z-20 border-b border-orange-200 bg-white/95 backdrop-blur">
        <div className="mx-auto flex max-w-7xl flex-col gap-4 px-4 py-4 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex items-center justify-between gap-4">
            <div>
              <p className="text-xs font-bold uppercase text-brand-orange">ShopAI Assistant</p>
              <h1 className="text-2xl font-extrabold text-slate-950">Shopee-style AI Commerce</h1>
            </div>
            <button
              className="relative inline-flex h-11 w-11 items-center justify-center rounded-md bg-brand-ink text-white lg:hidden"
              onClick={() => setCartOpen(true)}
              aria-label="Mở giỏ hàng"
            >
              <ShoppingCart className="h-5 w-5" />
              {cartQuantity > 0 ? (
                <span className="absolute -right-1 -top-1 grid h-5 min-w-5 place-items-center rounded-full bg-brand-orange px-1 text-xs font-bold">
                  {cartQuantity}
                </span>
              ) : null}
            </button>
          </div>

          <div className="flex flex-1 flex-col gap-3 lg:max-w-3xl lg:flex-row">
            <label className="relative flex-1">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
              <input
                className="h-11 w-full rounded-md border border-slate-200 bg-slate-50 pl-10 pr-3 text-sm outline-none focus:border-brand-orange focus:bg-white"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Tìm tai nghe, balo, mỹ phẩm..."
              />
            </label>
            <button
              className="hidden h-11 items-center justify-center gap-2 rounded-md bg-brand-ink px-4 text-sm font-bold text-white hover:bg-slate-700 lg:inline-flex"
              onClick={() => setCartOpen(true)}
            >
              <ShoppingCart className="h-4 w-4" />
              Giỏ hàng ({cartQuantity})
            </button>
          </div>
        </div>
      </header>

      <section className="border-b border-slate-200 bg-white">
        <div className="mx-auto grid max-w-7xl gap-6 px-4 py-6 lg:grid-cols-[1.3fr_0.7fr] lg:items-center">
          <div>
            <div className="mb-4 inline-flex items-center gap-2 rounded-md bg-orange-50 px-3 py-2 text-sm font-semibold text-brand-orange">
              <Sparkles className="h-4 w-4" />
              AI hỗ trợ tư vấn và chăm sóc khách hàng
            </div>
            <h2 className="max-w-3xl text-3xl font-extrabold leading-tight text-slate-950 md:text-4xl">
              Marketplace mini để demo chatbot bán hàng có nhớ ngữ cảnh.
            </h2>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-600">
              Hỏi bot về sản phẩm, giá, tồn kho, chính sách và mã đơn demo. Đổi chế độ trong chat để thấy khác biệt giữa tư vấn có context và không có context.
            </p>
            <div className="mt-5 flex flex-wrap gap-2">
              {featuredTags.map((tag) => (
                <button
                  key={tag}
                  className="rounded-md border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-700 hover:border-brand-orange hover:text-brand-orange"
                  onClick={() => setSearch(tag.replace("Đồ đi làm", "balo").replace("Bán chạy", "").replace("Giao nhanh", "tai nghe").replace("Tai nghe dưới 500k", "tai nghe dưới 500k"))}
                >
                  {tag}
                </button>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="col-span-2">
              <AuthPanel user={authUser} onAuthenticated={handleAuthenticated} onLogout={handleLogout} />
            </div>
            <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
              <p className="text-sm text-slate-500">Sản phẩm demo</p>
              <p className="mt-2 text-2xl font-extrabold text-slate-950">{products.length}</p>
            </div>
            <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
              <p className="text-sm text-slate-500">Giá trị giỏ</p>
              <p className="mt-2 text-2xl font-extrabold text-slate-950">{formatVnd(cartTotal)}</p>
            </div>
            <div className="col-span-2 flex items-center gap-3 rounded-lg border border-teal-100 bg-teal-50 p-4">
              <Truck className="h-6 w-6 text-brand-teal" />
              <p className="text-sm font-semibold leading-6 text-teal-900">Đơn từ 499.000đ được miễn phí vận chuyển tiêu chuẩn.</p>
            </div>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-4 py-6">
        {lastOrder ? (
          <div className="mb-5 flex flex-col gap-3 rounded-lg border border-teal-200 bg-teal-50 p-4 md:flex-row md:items-center md:justify-between">
            <div>
              <p className="text-sm font-bold text-teal-900">Đã tạo đơn {lastOrder.id}</p>
              <p className="mt-1 text-sm text-teal-800">
                Trạng thái: {lastOrder.status}. Bạn có thể hỏi bot: "Kiểm tra đơn {lastOrder.id}".
              </p>
            </div>
            <button className="self-start rounded-md p-2 text-teal-700 hover:bg-teal-100 md:self-auto" onClick={() => setLastOrder(null)} aria-label="Ẩn thông báo đơn hàng">
              <X className="h-4 w-4" />
            </button>
          </div>
        ) : null}

        <div className="mb-5 flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="flex items-center gap-2 text-sm font-bold text-slate-500">
              <Filter className="h-4 w-4" />
              Danh mục
            </p>
            <div className="mt-3 flex gap-2 overflow-x-auto">
              {categories.map((item) => (
                <button
                  key={item}
                  className={`h-9 shrink-0 rounded-md px-3 text-sm font-semibold ${category === item ? "bg-brand-orange text-white" : "border border-slate-200 bg-white text-slate-700 hover:border-brand-orange hover:text-brand-orange"
                    }`}
                  onClick={() => setCategory(item)}
                >
                  {item}
                </button>
              ))}
            </div>
          </div>
          <div className="inline-flex items-center gap-2 rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-500">
            <SlidersHorizontal className="h-4 w-4" />
            Sắp xếp: liên quan nhất
          </div>
        </div>

        {error ? <div className="rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">{error}</div> : null}

        {loading ? (
          <div className="grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
            {Array.from({ length: 10 }).map((_, index) => (
              <div key={index} className="h-80 animate-pulse rounded-lg bg-white" />
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
            {products.map((product) => (
              <ProductCard key={product.id} product={product} onAddToCart={addToCart} onOpen={setSelectedProduct} />
            ))}
          </div>
        )}
      </section>

      {selectedProduct ? (
        <div className="fixed inset-0 z-30 grid place-items-center bg-slate-950/40 px-4 py-8" onClick={() => setSelectedProduct(null)}>
          <article className="grid max-h-[90vh] w-full max-w-4xl overflow-hidden rounded-lg bg-white shadow-panel md:grid-cols-2" onClick={(event) => event.stopPropagation()}>
            <div className="min-h-80 bg-slate-100">
              <img src={selectedProduct.image_url} alt={selectedProduct.name} className="h-full w-full object-cover" />
            </div>
            <div className="flex max-h-[90vh] flex-col overflow-y-auto p-6">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-sm font-bold text-brand-orange">{selectedProduct.category}</p>
                  <h3 className="mt-2 text-2xl font-extrabold leading-tight text-slate-950">{selectedProduct.name}</h3>
                </div>
                <button className="rounded-md p-2 text-slate-500 hover:bg-slate-100" onClick={() => setSelectedProduct(null)} aria-label="Đóng chi tiết sản phẩm">
                  <X className="h-5 w-5" />
                </button>
              </div>

              <p className="mt-4 text-3xl font-extrabold text-brand-orange">{formatVnd(selectedProduct.price)}</p>
              <p className="mt-4 text-sm leading-6 text-slate-600">{selectedProduct.description}</p>

              <div className="mt-5 grid grid-cols-3 gap-3">
                <div className="rounded-md bg-slate-50 p-3">
                  <p className="text-xs text-slate-500">Đánh giá</p>
                  <p className="mt-1 font-bold text-slate-900">{selectedProduct.rating}/5</p>
                </div>
                <div className="rounded-md bg-slate-50 p-3">
                  <p className="text-xs text-slate-500">Đã bán</p>
                  <p className="mt-1 font-bold text-slate-900">{selectedProduct.sold_count.toLocaleString("vi-VN")}</p>
                </div>
                <div className="rounded-md bg-slate-50 p-3">
                  <p className="text-xs text-slate-500">Tồn kho</p>
                  <p className="mt-1 font-bold text-slate-900">{selectedProduct.stock}</p>
                </div>
              </div>

              <div className="mt-5">
                <p className="text-sm font-bold text-slate-900">Màu sắc / phiên bản</p>
                <div className="mt-2 flex flex-wrap gap-2">
                  {selectedProduct.variants.map((variant) => (
                    <span key={variant} className="rounded-md border border-slate-200 px-3 py-2 text-sm text-slate-700">
                      {variant}
                    </span>
                  ))}
                </div>
              </div>

              <button
                className="mt-auto h-12 rounded-md bg-brand-orange px-4 text-sm font-bold text-white hover:bg-orange-600"
                onClick={() => addToCart(selectedProduct)}
              >
                Thêm vào giỏ
              </button>
            </div>
          </article>
        </div>
      ) : null}

      <CartDrawer
        open={cartOpen}
        items={cartItems}
        onClose={() => setCartOpen(false)}
        onUpdateQuantity={updateQuantity}
        onRemove={removeItem}
        onOrderCreated={setLastOrder}
        onClear={() => setCartItems([])}
      />
      <ChatWidget authToken={authToken} user={authUser} />
    </main>
  );
}
