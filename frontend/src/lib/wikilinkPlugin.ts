import { visit, SKIP } from 'unist-util-visit'
import type { Root, Text, Element, RootContent } from 'hast'
import { slugify } from './slugify'

const WIKILINK_RE = /\[\[([^\]]+)\]\]/g
const PAGE_TYPES = ['concept', 'summary', 'insight', 'connection', 'qa', 'lint']

interface Options {
  pageIndex: string[]
}

/** Resolve [[Title]] or [[Title|Display]] to a route path, or null if orphan */
// Normalise a raw page path from the API (strips .md extension)
function normalisePath(p: string) {
  return p.replace(/\.md$/, '')
}

function resolve(raw: string, pageIndex: string[]): { href: string; label: string } | null {
  const [target, label] = raw.split('|')
  const displayLabel = (label ?? target).trim()
  const slug = slugify(target.trim())
  const normalised = pageIndex.map(normalisePath)

  for (const type of PAGE_TYPES) {
    if (normalised.includes(`${type}/${slug}`)) {
      return { href: `/wiki/${type}/${slug}`, label: displayLabel }
    }
  }
  return null
}

export function wikilinkPlugin(options: Options) {
  return (tree: Root) => {
    visit(tree, 'text', (node: Text, index, parent) => {
      if (!parent || index === undefined) return
      if (!node.value.includes('[[')) return

      const parts: RootContent[] = []
      let lastIndex = 0

      for (const match of node.value.matchAll(WIKILINK_RE)) {
        const [full, inner] = match
        const start = match.index!

        if (start > lastIndex) {
          parts.push({ type: 'text', value: node.value.slice(lastIndex, start) })
        }

        const resolved = resolve(inner, options.pageIndex)
        if (resolved) {
          parts.push({
            type: 'element',
            tagName: 'a',
            properties: {
              href: resolved.href,
              'data-wikilink': 'true',
              className: ['wikilink'],
            },
            children: [{ type: 'text', value: resolved.label }],
          } as Element)
        } else {
          parts.push({
            type: 'element',
            tagName: 'span',
            properties: { className: ['wikilink-orphan'] },
            children: [{ type: 'text', value: inner.split('|').pop()?.trim() ?? inner }],
          } as Element)
        }

        lastIndex = start + full.length
      }

      if (lastIndex < node.value.length) {
        parts.push({ type: 'text', value: node.value.slice(lastIndex) })
      }

      if (parts.length > 0) {
        parent.children.splice(index, 1, ...parts)
        return [SKIP, index + parts.length]
      }
    })
  }
}
