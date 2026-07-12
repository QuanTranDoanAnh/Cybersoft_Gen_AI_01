"use client";

import { Minus, Plus, ShoppingBag, Trash2, X } from "lucide-react";
import { useState } from "react";
import { createOrder } from "@/utils/api";
import { formatVnd } from "@/utils/format";
import type { CartItem, Order } from "@/utils/types";

type CartDrawerProps = {
  open: boolean;
  items: CartItem[];
  onClose: () => void;
  onUpdateQuantity: (productId: string, quantity: number) => void;
  onRemove: (productId: string) => void;
  onOrderCreated: (order: Order) => void;
  onClear: () => void;
};

export function CartDrawer({
  open,
  items,
  onClose,
  onUpdateQuantity,
  onRemove,
  onOrderCreated,
  onClear
}: CartDrawerProps) {
  const [customerName, setCustomerName] = useState("Nguyen Van A");
  const [phone, setPhone] = useState("0909009009");
  const [address, setAddress] = useState("123 Nguyen Hue, Quan 1, TP.HCM");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const total = items.reduce((sum, item) => sum + item.product.price * item.quantity, 0);

  async function handleCheckout() {
    if (!items.length) return;
    setSubmitting(true);
    setError("");

    try {
      const order = await createOrder({
        customer_name: customerName,
        phone,
        address,
        items: items.map((item) => ({ product_id: item.product.id, quantity: item.quantity }))
      });
      onOrderCreated(order);
      onClear();
      onClose();
    } catch (checkoutError) {
      setError(checkoutError instanceof Error ? checkoutError.message : "Không thể tạo đơn hàng");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className={`fixed inset-0 z-40 ${open ? "pointer-events-auto" : "pointer-events-none"}`}>
      <div className={`absolute inset-0 bg-slate-950/30 transition-opacity ${open ? "opacity-100" : "opacity-0"}`} onClick={onClose} />
      <aside
        className={`absolute right-0 top-0 flex h-full w-full max-w-md flex-col bg-white shadow-panel transition-transform duration-300 ${open ? "translate-x-0" : "translate-x-full"
          }`}
      >
        <header className="flex h-16 items-center justify-between border-b border-slate-200 px-5">
          <div className="flex items-center gap-2">
            <ShoppingBag className="h-5 w-5 text-brand-orange" />
            <h2 className="text-base font-bold text-slate-900">Giỏ hàng</h2>
          </div>
          <button className="rounded-md p-2 text-slate-500 hover:bg-slate-100" onClick={onClose} aria-label="Đóng giỏ hàng">
            <X className="h-5 w-5" />
          </button>
        </header>

        <div className="flex-1 overflow-y-auto px-5 py-4">
          {items.length ? (
            <div className="space-y-4">
              {items.map((item) => (
                <div key={item.product.id} className="flex gap-3 border-b border-slate-100 pb-4">
                  <img src={item.product.image_url} alt={item.product.name} className="h-20 w-20 rounded-md object-cover" />
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-semibold leading-5 text-slate-900">{item.product.name}</p>
                    <p className="mt-1 text-sm font-bold text-brand-orange">{formatVnd(item.product.price)}</p>
                    <div className="mt-3 flex items-center gap-2">
                      <button
                        className="rounded border border-slate-200 p-1 text-slate-600 hover:bg-slate-50"
                        onClick={() => onUpdateQuantity(item.product.id, item.quantity - 1)}
                        aria-label="Giảm số lượng"
                      >
                        <Minus className="h-4 w-4" />
                      </button>
                      <span className="w-8 text-center text-sm font-semibold">{item.quantity}</span>
                      <button
                        className="rounded border border-slate-200 p-1 text-slate-600 hover:bg-slate-50"
                        onClick={() => onUpdateQuantity(item.product.id, item.quantity + 1)}
                        aria-label="Tăng số lượng"
                      >
                        <Plus className="h-4 w-4" />
                      </button>
                      <button className="ml-auto rounded p-1 text-slate-400 hover:bg-rose-50 hover:text-rose-600" onClick={() => onRemove(item.product.id)} aria-label="Xóa sản phẩm">
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                </div>
              ))}

              <div className="space-y-3 rounded-md border border-slate-200 bg-slate-50 p-4">
                <input className="h-11 w-full rounded-md border border-slate-200 px-3 text-sm outline-none focus:border-brand-orange" value={customerName} onChange={(event) => setCustomerName(event.target.value)} />
                <input className="h-11 w-full rounded-md border border-slate-200 px-3 text-sm outline-none focus:border-brand-orange" value={phone} onChange={(event) => setPhone(event.target.value)} />
                <textarea className="min-h-20 w-full resize-none rounded-md border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-orange" value={address} onChange={(event) => setAddress(event.target.value)} />
              </div>
            </div>
          ) : (
            <div className="flex h-full flex-col items-center justify-center text-center text-slate-500">
              <ShoppingBag className="mb-3 h-10 w-10 text-slate-300" />
              <p className="text-sm">Giỏ hàng đang trống</p>
            </div>
          )}
        </div>

        <footer className="border-t border-slate-200 p-5">
          {error ? <p className="mb-3 rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</p> : null}
          <div className="mb-4 flex items-center justify-between">
            <span className="text-sm text-slate-500">Tổng cộng</span>
            <span className="text-xl font-bold text-slate-900">{formatVnd(total)}</span>
          </div>
          <button
            className="h-11 w-full rounded-md bg-brand-orange px-4 text-sm font-bold text-white transition hover:bg-orange-600 disabled:cursor-not-allowed disabled:bg-slate-300"
            disabled={!items.length || submitting}
            onClick={handleCheckout}
          >
            {submitting ? "Đang tạo đơn..." : "Đặt hàng demo"}
          </button>
        </footer>
      </aside>
    </div>
  );
}

