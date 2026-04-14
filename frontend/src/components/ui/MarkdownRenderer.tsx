import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeHighlight from 'rehype-highlight'
import rehypeRaw from 'rehype-raw'
import { Link } from 'react-router-dom'
import { wikilinkPlugin } from '../../lib/wikilinkPlugin'
import { useWikiPages } from '../../hooks/useWikiPages'
import 'highlight.js/styles/github-dark.css'

interface MarkdownRendererProps {
  content: string
  className?: string
}

export function MarkdownRenderer({ content, className = '' }: MarkdownRendererProps) {
  const { data: pageIndex = [] } = useWikiPages()

  const proseClass = `prose prose-invert prose-gray max-w-none
    prose-headings:text-gray-100 prose-headings:font-semibold
    prose-p:text-gray-300 prose-p:leading-relaxed
    prose-a:text-violet-400 prose-a:no-underline hover:prose-a:underline
    prose-strong:text-gray-100
    prose-code:text-violet-300 prose-code:bg-gray-800 prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-code:text-sm prose-code:before:content-none prose-code:after:content-none
    prose-pre:bg-gray-900 prose-pre:border prose-pre:border-gray-700
    prose-blockquote:border-l-violet-500 prose-blockquote:text-gray-400
    prose-table:text-sm prose-th:text-gray-300 prose-td:text-gray-400
    prose-hr:border-gray-700
    prose-li:text-gray-300
    [&_.wikilink]:text-violet-400 [&_.wikilink]:cursor-pointer [&_.wikilink:hover]:underline
    [&_.wikilink-orphan]:text-yellow-400 [&_.wikilink-orphan]:italic
    ${className}`

  return (
    <div className={proseClass}>
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      rehypePlugins={[
        rehypeRaw,
        [wikilinkPlugin, { pageIndex }],
        [rehypeHighlight, { detect: true }],
      ]}
      components={{
        a: ({ href, children, ...props }) => {
          const isWikilink = (props as Record<string, unknown>)['data-wikilink'] === 'true'
          if (isWikilink && href) {
            return <Link to={href} className="wikilink">{children}</Link>
          }
          if (href?.startsWith('/')) {
            return <Link to={href}>{children}</Link>
          }
          return <a href={href} target="_blank" rel="noopener noreferrer" {...props}>{children}</a>
        },
      }}
    >
      {content}
    </ReactMarkdown>
    </div>
  )
}
