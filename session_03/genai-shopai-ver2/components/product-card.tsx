"use client";

import { ShoppingCart, Star } from "lucide-react";
import type { Product } from "@/utils/types";
import { formatVnd } from "@/utils/format";

type ProductCardProps = {
  product: Product;
  onAddToCart: (product: Product) => void;
  onOpen: (product: Product) => void;
};

export function ProductCard({ product, onAddToCart, onOpen }: ProductCardProps) {
  const discount =
    product.original_price && product.original_price > product.price
      ? Math.round((1 - product.price / product.original_price) * 100)
      : 0;

  return (
    <article className="flex h-full flex-col overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm transition hover:-translate-y-0.5 hover:border-brand-orange/40 hover:shadow-md">
      <button className="relative block aspect-square bg-slate-100 text-left" onClick={() => onOpen(product)}>
        <img src={product.image_url} alt={product.name} className="h-full w-full object-cover" />
        {discount > 0 ? (
          <span className="absolute left-2 top-2 rounded bg-brand-orange px-2 py-1 text-xs font-semibold text-white">
            -{discount}%
          </span>
        ) : null}
      </button>

      <div className="flex flex-1 flex-col gap-3 p-3">
        <button className="min-h-11 text-left text-sm font-semibold leading-5 text-slate-900 line-clamp-2" onClick={() => onOpen(product)}>
          {product.name}
        </button>
        <p className="text-xs leading-5 text-slate-500 line-clamp-2">{product.description}</p>

        <div className="mt-auto space-y-2">
          <div className="flex items-end gap-2">
            <span className="text-base font-bold text-brand-orange">{formatVnd(product.price)}</span>
            {product.original_price ? (
              <span className="text-xs text-slate-400 line-through">{formatVnd(product.original_price)}</span>
            ) : null}
          </div>

          <div className="flex items-center justify-between text-xs text-slate-500">
            <span className="inline-flex items-center gap-1">
              <Star className="h-3.5 w-3.5 fill-amber-400 text-amber-400" />
              {product.rating}
            </span>
            <span>Đã bán {product.sold_count.toLocaleString("vi-VN")}</span>
          </div>

          <button
            className="inline-flex h-10 w-full items-center justify-center gap-2 rounded-md bg-brand-ink px-3 text-sm font-semibold text-white transition hover:bg-slate-700"
            onClick={() => onAddToCart(product)}
          >
            <ShoppingCart className="h-4 w-4" />
            Thêm vào giỏ
          </button>
        </div>
      </div>
    </article>
  );
}

