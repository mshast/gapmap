"use client";

import { createContext, useCallback, useContext, useSyncExternalStore, type Dispatch, type PropsWithChildren, type SetStateAction } from "react";
import { initialState, type AppState } from "@/lib/types";

type AppContextValue = {
  state: AppState;
  setState: Dispatch<SetStateAction<AppState>>;
  hydrated: boolean;
};

const AppContext = createContext<AppContextValue | null>(null);
const storageKey = "gapmap.session.v1";
const serverSnapshot = "__gapmap_server_snapshot__";
const listeners = new Set<() => void>();

function getSnapshot() {
  return typeof window === "undefined" ? serverSnapshot : window.localStorage.getItem(storageKey) ?? "";
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  const onStorage = () => listener();
  window.addEventListener("storage", onStorage);
  return () => {
    listeners.delete(listener);
    window.removeEventListener("storage", onStorage);
  };
}

function decodeSnapshot(snapshot: string): AppState {
  if (!snapshot || snapshot === serverSnapshot) return initialState;
  try {
    return { ...initialState, ...JSON.parse(snapshot) as Partial<AppState> };
  } catch {
    return initialState;
  }
}

export function AppStateProvider({ children }: PropsWithChildren) {
  const snapshot = useSyncExternalStore(subscribe, getSnapshot, () => serverSnapshot);
  const state = decodeSnapshot(snapshot);
  const setState = useCallback<Dispatch<SetStateAction<AppState>>>((nextState) => {
    const currentState = decodeSnapshot(getSnapshot());
    const next = typeof nextState === "function" ? nextState(currentState) : nextState;
    window.localStorage.setItem(storageKey, JSON.stringify(next));
    listeners.forEach((listener) => listener());
  }, []);
  const hydrated = snapshot !== serverSnapshot;
  return <AppContext.Provider value={{ state, setState, hydrated }}>{children}</AppContext.Provider>;
}

export function useAppState() {
  const context = useContext(AppContext);
  if (!context) throw new Error("useAppState must be used within AppStateProvider");
  return context;
}