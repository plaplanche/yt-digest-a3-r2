import Ajv from "ajv";
import { describe, expect, test } from "vitest";
import logSchema from "../../contracts/log-event.schema.json";
import resultSchema from "../../contracts/transcript-result.schema.json";
import { EventValues } from "../src/contracts/log-event";
import type { TranscriptResult } from "../src/contracts/transcript-result";

const ajv = new Ajv({ allowUnionTypes: true });
const validResult = ajv.compile(resultSchema);
const validLine = ajv.compile(logSchema);

const result: TranscriptResult = {
  video_id: "dQw4w9WgXcQ",
  status: "ok",
  lang: "en",
  source: "manual",
  word_count: 3,
  truncated: false,
  sponsor_ratio: 0.5,
  pages: ["one two three"],
};

const line = {
  ts: "2026-10-16T12:00:00.000Z",
  level: "info",
  service: "worker",
  event: "service.started",
  attrs: { version: "0.1.0" },
};

describe("transcript result schema", () => {
  test("accepts a valid result", () => {
    expect(validResult(result)).toBe(true);
    const empty = { ...result, status: "no_transcript", lang: null, source: null, sponsor_ratio: null, pages: [] };
    expect(validResult(empty)).toBe(true);
  });

  test.each([
    ["an extra field", { extra: 1 }],
    ["a bad video_id", { video_id: "short" }],
    ["a bad status", { status: "done" }],
    ["a negative word_count", { word_count: -1 }],
    ["a sponsor_ratio above 1", { sponsor_ratio: 1.5 }],
  ])("rejects %s", (_name, change) => {
    expect(validResult({ ...result, ...change })).toBe(false);
  });
});

describe("log event schema", () => {
  test("accepts a valid line", () => {
    expect(validLine(line)).toBe(true);
  });

  test.each([
    ["an unknown event", { event: "made.up" }],
    ["an unknown field", { extra: 1 }],
    ["a bad timestamp", { ts: "yesterday" }],
  ])("rejects %s", (_name, change) => {
    expect(validLine({ ...line, ...change })).toBe(false);
  });

  test("the generated catalogue matches the schema", () => {
    expect([...EventValues]).toEqual(logSchema.properties.event.enum);
  });
});
