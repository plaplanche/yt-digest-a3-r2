import { EventValues, LevelValues, type Event, type Level, type LogEvent } from "./contracts/log-event";

export type LogFields = Partial<Pick<LogEvent, "request_id" | "video_id" | "attrs">> & {
  level?: Level;
};

const FIELD_NAMES = ["level", "request_id", "video_id", "attrs"];

export function log(event: Event, fields: LogFields = {}): void {
  if (!EventValues.includes(event)) {
    throw new Error(`unknown log event: ${String(event)}`);
  }
  for (const name of Object.keys(fields)) {
    if (!FIELD_NAMES.includes(name)) {
      throw new Error(`unknown log field: ${name}`);
    }
  }
  const { level = "info", ...rest } = fields;
  if (!LevelValues.includes(level)) {
    throw new Error(`unknown log level: ${String(level)}`);
  }
  const line: LogEvent = {
    ts: new Date().toISOString(),
    level,
    service: "worker",
    event,
    attrs: {},
    ...rest,
  };
  console.error(JSON.stringify(line));
}
