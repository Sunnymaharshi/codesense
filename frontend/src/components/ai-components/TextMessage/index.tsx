// text type — parent MessageStream renders rawText; this is a no-op.
export function TextMessage(_: { data: Record<string, unknown> }) {
  return null;
}
