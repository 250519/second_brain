interface SpinnerProps {
  size?: 'sm' | 'md' | 'lg'
  label?: string
}

const sizes = { sm: 'h-4 w-4', md: 'h-6 w-6', lg: 'h-8 w-8' }

export function Spinner({ size = 'md', label }: SpinnerProps) {
  return (
    <div className="flex items-center gap-2">
      <div
        className={`${sizes[size]} animate-spin rounded-full border-2 border-gray-600 border-t-violet-500`}
        role="status"
        aria-label={label ?? 'Loading'}
      />
      {label && <span className="text-gray-400 text-sm">{label}</span>}
    </div>
  )
}
