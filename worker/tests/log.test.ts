import { afterEach, expect, test, vi } from "vitest";
import type { Event } from "../src/contracts/log-event";
import { log } from "../src/log";

afterEach(() => {
  vi.restoreAllMocks();
});

test("writes one valid JSON line", () => {
  const spy = vi.spyOn(console, "error").mockImplementation(() => undefined);
  log("service.started", { attrs: { version: "0.1.0" }, request_id: "r1" });
  expect(spy).toHaveBeenCalledTimes(1);
  const record = JSON.parse(String(spy.mock.calls[0]?.[0])) as Record<string, unknown>;
  expect(record).toMatchObject({
    level: "info",
    service: "worker",
    event: "service.started",
    request_id: "r1",
    attrs: { version: "0.1.0" },
  });
  expect(String(record.ts)).toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/);
});

test("throws on an event outside the catalogue", () => {
  const spy = vi.spyOn(console, "error").mockImplementation(() => undefined);
  expect(() => log("made.up" as Event)).toThrow(/unknown log event/);
  expect(spy).not.toHaveBeenCalled();
});

test("throws on an unknown field or level", () => {
  expect(() => log("service.started", { extra: 1 } as object)).toThrow(/unknown log field/);
  expect(() => log("service.started", { level: "fatal" as "info" })).toThrow(/unknown log level/);
});

test("the type system rejects an unknown event", () => {
  // @ts-expect-error "made.up" is not in the catalogue
  expect(() => log("made.up")).toThrow();
});
