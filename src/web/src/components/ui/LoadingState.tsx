/** Skeleton lines keep the layout steady while data loads; the label is announced. */
export function LoadingState({
  label = 'Loading…',
  lines = 3,
}: {
  label?: string
  lines?: number
}) {
  return (
    <div className="loading" role="status" aria-live="polite">
      <span className="visually-hidden">{label}</span>
      {Array.from({ length: lines }, (_, i) => (
        <span
          key={i}
          className="skeleton"
          style={{ width: `${92 - i * 14}%` }}
          aria-hidden="true"
        />
      ))}
    </div>
  )
}
