"use client";

import { useEffect, useState } from "react";

import { apiGet } from "@/lib/api";
import type { User } from "@/lib/types";

// The shell and profile page both need /me. Keep one in-flight request and a
// small in-memory user cache so client-side navigation does not refetch the
// same identity. A hard reload/logout starts a fresh module instance.
let cachedUser: User | null = null;
let inflightUser: Promise<User> | null = null;

async function loadUser(): Promise<User> {
  if (cachedUser) return cachedUser;
  if (!inflightUser) {
    inflightUser = apiGet<{ user: User }>("/me")
      .then((data) => {
        cachedUser = data.user;
        return data.user;
      })
      .finally(() => {
        inflightUser = null;
      });
  }
  return inflightUser;
}

export function useMe(enabled = true) {
  const [user, setUser] = useState<User | null>(cachedUser);
  const [loading, setLoading] = useState(enabled && !cachedUser);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!enabled) return;
    let alive = true;
    if (cachedUser) {
      setUser(cachedUser);
      setLoading(false);
      return;
    }
    setLoading(true);
    loadUser()
      .then((nextUser) => {
        if (!alive) return;
        setUser(nextUser);
        setError(null);
      })
      .catch((err: Error) => {
        if (!alive) return;
        setError(err.message);
      })
      .finally(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [enabled]);

  useEffect(() => {
    function onUserUpdated(event: Event) {
      const detail = (event as CustomEvent<User>).detail;
      if (detail) {
        cachedUser = detail;
        setUser(detail);
      }
    }
    window.addEventListener("ap:user-updated", onUserUpdated);
    return () => window.removeEventListener("ap:user-updated", onUserUpdated);
  }, []);

  return { user, loading, error };
}
