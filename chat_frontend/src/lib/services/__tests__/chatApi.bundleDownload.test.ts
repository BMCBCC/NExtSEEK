/**
 * The Debug Output panel's JSON and Metadata downloads.
 *
 * Both buttons sent `?format=`, which is DRF's content-negotiation parameter.
 * With no renderer named "metadata" the server 404'd before the view ran, so
 * the Metadata button had never worked. Selection is `?part=` now, and the two
 * downloads must not land on the same filename.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { NextseekApiService } from "../chatApi";

function makeService() {
  const auth = {
    getApiBaseUrl: () => "https://nextseek.mit.edu",
    getAuthHeaders: () => ({ Authorization: "Token abc" }),
  };
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  return new NextseekApiService(auth as any);
}

describe("downloadBundle", () => {
  let anchor: HTMLAnchorElement;

  beforeEach(() => {
    anchor = document.createElement("a");
    anchor.click = vi.fn();
    vi.spyOn(document, "createElement").mockReturnValue(anchor);
    vi.spyOn(document.body, "appendChild").mockImplementation((n) => n);
    vi.spyOn(document.body, "removeChild").mockImplementation((n) => n);
    global.URL.createObjectURL = vi.fn(() => "blob:x");
    global.URL.revokeObjectURL = vi.fn();
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      blob: async () => new Blob(["{}"], { type: "application/json" }),
    });
  });

  afterEach(() => vi.restoreAllMocks());

  it("asks for the whole bundle by default", async () => {
    await makeService().downloadBundle("sess-1", 7, "json");

    const url = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0][0] as string;
    expect(url).toContain("/sessions/sess-1/bundles/7/");
    expect(url).not.toContain("format=");
  });

  it("selects metadata with part, never with DRF's format parameter", async () => {
    await makeService().downloadBundle("sess-1", 7, "metadata");

    const url = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0][0] as string;
    expect(url).toContain("part=metadata");
    expect(url).not.toContain("format=metadata");
  });

  it("gives the two downloads different filenames", async () => {
    const svc = makeService();

    await svc.downloadBundle("sess-1", 7, "json");
    const full = anchor.download;
    await svc.downloadBundle("sess-1", 7, "metadata");
    const meta = anchor.download;

    expect(full).toBe("bundle_7.json");
    expect(meta).toBe("bundle_7.metadata.json");
    expect(full).not.toBe(meta);
  });
});
