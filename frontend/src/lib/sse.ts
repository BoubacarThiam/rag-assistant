// Server-Sent Events parser.
//
// The browser's EventSource only supports GET requests, and /chat is a POST. So we read the
// response body ourselves: network chunks arrive at arbitrary boundaries (an event can be cut
// in two, or several events can arrive together), hence the buffer.

export interface SseEvent {
  event: string;
  data: string;
}

export function createSseParser(onEvent: (event: SseEvent) => void) {
  let buffer = "";

  function parseBlock(block: string) {
    let event = "message";
    const data: string[] = [];
    for (const line of block.split("\n")) {
      if (line.startsWith("event:")) event = line.slice(6).trim();
      else if (line.startsWith("data:")) data.push(line.slice(5).replace(/^ /, ""));
    }
    if (data.length > 0) onEvent({ event, data: data.join("\n") });
  }

  return {
    /** Feed decoded text; complete events (terminated by a blank line) are emitted. */
    push(chunk: string) {
      buffer += chunk.replace(/\r\n/g, "\n");
      let end = buffer.indexOf("\n\n");
      while (end !== -1) {
        parseBlock(buffer.slice(0, end));
        buffer = buffer.slice(end + 2);
        end = buffer.indexOf("\n\n");
      }
    },
  };
}
