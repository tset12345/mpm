"use client";
import { useState, useEffect, useCallback } from "react";
import { api } from "@/lib/api";
import type { Profile } from "@/lib/types";

const STORAGE_KEY = "mpm_selected_profile_id";

export function useProfile() {
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [selectedId, setSelectedIdState] = useState<number | null>(() => {
    if (typeof window === "undefined") return null;
    const v = localStorage.getItem(STORAGE_KEY);
    return v ? parseInt(v, 10) : null;
  });

  const loadProfiles = useCallback(async () => {
    try {
      const res = await api.getProfiles();
      setProfiles(res.data);
    } catch {
      setProfiles([]);
    }
  }, []);

  useEffect(() => { loadProfiles(); }, [loadProfiles]);

  function setSelectedId(id: number | null) {
    setSelectedIdState(id);
    if (id == null) {
      localStorage.removeItem(STORAGE_KEY);
    } else {
      localStorage.setItem(STORAGE_KEY, String(id));
    }
  }

  async function createProfile(name: string, analysis_type: "quant" | "dividend" = "quant"): Promise<Profile> {
    const res = await api.createProfile(name, analysis_type);
    await loadProfiles();
    return res.data;
  }

  async function updateProfile(id: number, body: { name?: string; analysis_type?: "quant" | "dividend" }) {
    await api.updateProfile(id, body);
    await loadProfiles();
  }

  async function deleteProfile(id: number) {
    await api.deleteProfile(id);
    if (selectedId === id) setSelectedId(null);
    await loadProfiles();
  }

  const selectedProfile = profiles.find(p => p.id === selectedId) ?? null;

  return { profiles, selectedId, selectedProfile, setSelectedId, loadProfiles, createProfile, updateProfile, deleteProfile };
}
