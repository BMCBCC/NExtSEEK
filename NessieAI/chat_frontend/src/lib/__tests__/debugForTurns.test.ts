/**
 * The Debug Output panel belongs to the chat on screen.
 *
 * `debugData` was only ever written by the live progress handlers, and nothing
 * reset it when the user switched chats. Its `bundleId` therefore stayed on the
 * last turn the user had actually *run*, and `handleDownload` paired it with a
 * `sessionId` that was likewise only set after a submit. Switch chats, click
 * JSON, and you downloaded the previous chat's bundle.
 */
import { describe, it, expect } from "vitest";
import { debugForTurns } from "../debugForTurns";
import type { Turn } from "../types/api";

const turn = (bundle_id: number, user_query: string): Turn => ({
  bundle_id,
  user_query,
  reply: "ok",
  mode: "new_search",
  ts: "2026-09-07T11:38:33",
  debug_entries: [{ agent: "router", summary: "nextseek_query" }],
});

describe("debugForTurns", () => {
  it("points at the last turn of the chat being opened", () => {
    const d = debugForTurns([turn(1, "first"), turn(2, "second"), turn(3, "third")]);

    expect(d.bundleId).toBe(3);
    expect(d.query).toBe("third");
  });

  it("carries that turn's own pipeline entries, not the previous chat's", () => {
    const d = debugForTurns([turn(9, "only")]);

    expect(d.entries.map((e) => e.agent)).toEqual(["router"]);
    expect(d.entries[0].timestamp).toBeInstanceOf(Date);
  });

  it("clears completely for a new chat", () => {
    const d = debugForTurns([]);

    expect(d).toEqual({ entries: [], bundleId: null, query: "" });
  });

  it("survives a turn that carries no debug entries", () => {
    const bare: Turn = { bundle_id: 4, user_query: "q", reply: "r", mode: "cc" };

    const d = debugForTurns([bare]);

    expect(d.bundleId).toBe(4);
    expect(d.entries).toEqual([]);
  });
});
