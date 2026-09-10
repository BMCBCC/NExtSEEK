import type { Turn } from "./types/api";
import type { DebugData } from "./types/chat";

/**
 * The Debug Output state for a chat that has just been loaded.
 *
 * `debugData` is otherwise written only by the live progress handlers, so
 * nothing reset it when the user switched chats: the panel kept showing the
 * pipeline of the last turn the user had *run*, and the JSON button downloaded
 * that turn's bundle from whichever session happened to be current.
 *
 * The panel is anchored to the newest turn of the chat on screen, which is the
 * one whose reply is at the bottom of the transcript. An empty chat clears it
 * outright, so a new chat starts with an empty panel and disabled buttons.
 */
export function debugForTurns(turns: Turn[]): DebugData {
  const last = turns.length > 0 ? turns[turns.length - 1] : null;
  if (!last) {
    return { entries: [], bundleId: null, query: "" };
  }

  // The server records no per-entry time; the turn's own timestamp stands in,
  // matching what hydrateFromTurns does for the per-message entries.
  const ts = last.ts ? new Date(last.ts) : new Date();

  return {
    entries: (last.debug_entries ?? []).map((e) => ({
      agent: e.agent,
      summary: e.summary,
      timestamp: ts,
    })),
    bundleId: last.bundle_id ?? null,
    query: last.user_query ?? "",
  };
}
