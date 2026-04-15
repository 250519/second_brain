export interface Frontmatter {
  title?: string
  type?: string
  summary?: string
  [key: string]: string | undefined
}

/** Parse YAML frontmatter from a wiki page. Only handles simple key: value pairs. */
export function parseFrontmatter(raw: string): { data: Frontmatter; content: string } {
  const FENCE = /^---\r?\n([\s\S]*?)\r?\n---\r?\n?/

  const match = raw.match(FENCE)
  if (!match) return { data: {}, content: raw }

  const yamlBlock = match[1]
  const content = raw.slice(match[0].length)
  const data: Frontmatter = {}

  for (const line of yamlBlock.split('\n')) {
    const colon = line.indexOf(':')
    if (colon === -1) continue
    const key = line.slice(0, colon).trim()
    const value = line.slice(colon + 1).trim().replace(/^["']|["']$/g, '')
    if (key) data[key] = value
  }

  return { data, content }
}
