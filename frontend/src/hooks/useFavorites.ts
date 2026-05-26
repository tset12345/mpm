"use client";
import { useState, useEffect } from "react";
import { api } from "@/lib/api";

export function useFavorites() {
  const [favorites, setFavorites] = useState<string[]>([]);
  const [favoriteNames, setFavoriteNames] = useState<Record<string, string>>({});
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    api.getFavorites()
      .then((res) => {
        setFavorites(res.data.map((f) => f.stock_code));
        setFavoriteNames(Object.fromEntries(res.data.map((f) => [f.stock_code, f.stock_name])));
      })
      .catch(() => {})
      .finally(() => setLoaded(true));
  }, []);

  const toggle = (code: string, name?: string) => {
    if (favorites.includes(code)) {
      setFavorites((prev) => prev.filter((c) => c !== code));
      setFavoriteNames((prev) => { const n = { ...prev }; delete n[code]; return n; });
      api.removeFavorite(code).catch(() => {});
    } else {
      setFavorites((prev) => [...prev, code]);
      if (name) setFavoriteNames((prev) => ({ ...prev, [code]: name }));
      api.addFavorite(code, name ?? code).catch(() => {});
    }
  };

  const isFavorite = (code: string) => favorites.includes(code);

  return { favorites, favoriteNames, toggle, isFavorite, loaded };
}
