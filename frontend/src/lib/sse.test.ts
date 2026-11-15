import { describe, expect, it } from "vitest";
import { createSseParser, type SseEvent } from "./sse";

function collect(chunks: string[]): SseEvent[] {
  const events: SseEvent[] = [];
  const parser = createSseParser((event) => events.push(event));
  for (const chunk of chunks) parser.push(chunk);
  return events;
}

describe("createSseParser", () => {
  it("parses several events arriving in one chunk", () => {
    const events = collect(['event: token\ndata: {"text":"Bon"}\n\nevent: done\ndata: {}\n\n']);
    expect(events).toEqual([
      { event: "token", data: '{"text":"Bon"}' },
      { event: "done", data: "{}" },
    ]);
  });

  it("reassembles an event split across network chunks", () => {
    const events = collect(["event: tok", 'en\ndata: {"text":', '"jour"}\n', "\n"]);
    expect(events).toEqual([{ event: "token", data: '{"text":"jour"}' }]);
  });

  it("waits for the blank line before emitting", () => {
    expect(collect(['event: token\ndata: {"text":"a"}\n'])).toEqual([]);
  });

  it("accepts CRLF line endings", () => {
    expect(collect(["event: done\r\ndata: {}\r\n\r\n"])).toEqual([{ event: "done", data: "{}" }]);
  });

  it("defaults to the 'message' event and ignores comment lines", () => {
    expect(collect([": keep-alive\n\ndata: hello\n\n"])).toEqual([
      { event: "message", data: "hello" },
    ]);
  });
});
