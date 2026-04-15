export interface IndexEntry {
  path: string   // e.g. "concept/agent-loop"
  type: string
  title: string
  summary: string
}

// Matches:  - [[concept/foo.md|Title]] `concept` — Summary text
const ENTRY_RE = /\[\[([^\]|]+?)(?:\|([^\]]+?))?\]\]\s*`([^`]+)`\s*—\s*(.+)/g

export function parseIndex(indexMarkdown: string): IndexEntry[] {
  const entries: IndexEntry[] = []
  for (const m of indexMarkdown.matchAll(ENTRY_RE)) {
    const rawPath = m[1].replace(/\.md$/, '')   // strip .md
    entries.push({
      path: rawPath,
      type: m[3].trim(),
      title: (m[2] ?? rawPath.split('/').pop() ?? rawPath).trim(),
      summary: m[4].trim(),
    })
  }
  return entries
}
