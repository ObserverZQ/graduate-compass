/** Verify the browser receives complete SSE events across network chunks. */

import { expect, test } from 'bun:test';
import { streamMatches } from './api';

test('streamMatches reads split frames and skips keep-alive comments', async () => {
  const originalFetch = globalThis.fetch;
  const chunks = [
    ': keep-alive\n\nevent: run_started\ndata: {"type":"run_sta',
    'rted","run_id":"synthetic","sequence":1}\n\n',
    'event: complete\ndata: {"type":"complete","run_id":"synthetic","sequence":2,"results":[]}\n\n',
  ];
  const body = new ReadableStream<Uint8Array>({
    start(controller) {
      const encoder = new TextEncoder();
      for (const chunk of chunks) controller.enqueue(encoder.encode(chunk));
      controller.close();
    },
  });
  globalThis.fetch = async () => new Response(body, {
    headers: { 'Content-Type': 'text/event-stream' },
  });

  try {
    const events = [];
    for await (const event of streamMatches('synthetic-session')) {
      events.push(event);
    }
    expect(events.map((event) => event.type)).toEqual(['run_started', 'complete']);
    expect(events[1].sequence).toBe(2);
  } finally {
    globalThis.fetch = originalFetch;
  }
});
