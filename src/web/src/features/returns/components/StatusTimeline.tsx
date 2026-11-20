import { RETURN_STEPS, type ReturnStatus } from '../returnStatus'

/** Vertical timeline: Requested → … → Inspected → Refunded or Rejected. */
export function StatusTimeline({ status }: { status: ReturnStatus }) {
  const isFinal = status === 'Refunded' || status === 'Rejected'
  const reached = isFinal
    ? RETURN_STEPS.length
    : RETURN_STEPS.indexOf(status as (typeof RETURN_STEPS)[number])
  const steps: ReturnStatus[] = [...RETURN_STEPS, isFinal ? status : 'Refunded']

  return (
    <ol className="timeline" aria-label="Return status">
      {steps.map((step, i) => {
        const state = i < reached ? 'done' : i === reached ? 'current' : 'upcoming'
        return (
          <li key={step} className={`timeline__step timeline__step--${state}`}>
            <span aria-current={state === 'current' ? 'step' : undefined}>{step}</span>
          </li>
        )
      })}
    </ol>
  )
}
