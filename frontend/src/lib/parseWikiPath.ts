export interface WikiPathParts {
  type: string
  slug: string
  displayName: string
}

/** "concept/agent-loop.md" or "concept/agent-loop" → {type, slug (no .md), displayName} */
export function parseWikiPath(path: string): WikiPathParts {
  const parts = path.split('/')
  const type = parts[0] ?? 'concept'
  const rawSlug = parts.slice(1).join('/')
  const slug = rawSlug.replace(/\.md$/, '')
  const displayName = slug
    .replace(/-/g, ' ')
    .replace(/\b\w/g, c => c.toUpperCase())
  return { type, slug, displayName }
}
