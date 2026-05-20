"use client";
import { useState, useEffect } from "react";

const KEY_CODES = "mpm_favorites";
const KEY_NAMES = "mpm_favorite_names";

export function useFavorites() {
  const [favorites, setFavorites] = useState<string[]>([]);
  const [favoriteNames, setFavoriteNames] = useState<Record<string, string>>({});

  useEffect(() => {
    const codes = localStorage.getItem(KEY_CODES);
    if (codes) setFavorites(JSON.parse(codes));
    const names = localStorage.getItem(KEY_NAMES);
    if (names) setFavoriteNames(JSON.parse(names));
  }, []);

  const toggle = (code: string, name?: string) => {
    setFavorites((prev) => {
      const next = prev.includes(code) ? prev.filter((c) => c !== code) : [...prev, code];
      localStorage.setItem(KEY_CODES, JSON.stringify(next));
      return next;
    });
    setFavoriteNames((prev) => {
      const next = { ...prev };
      if (prev[code]) {
        delete next[code];
      } else if (name) {
        next[code] = name;
      }
      localStorage.setItem(KEY_NAMES, JSON.stringify(next));
      return next;
    });
  };

  const isFavorite = (code: string) => favorites.includes(code);

  return { favorites, favoriteNames, toggle, isFavorite };
}
