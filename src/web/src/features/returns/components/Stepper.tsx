import { Icon } from '../../../components/ui/Icon'

interface StepperProps {
  steps: readonly string[]
  current: number
  /** Lets the customer jump back to a completed step. */
  onSelect?: (index: number) => void
}

export function Stepper({ steps, current, onSelect }: StepperProps) {
  return (
    <ol className="stepper" aria-label="Return steps">
      {steps.map((label, i) => {
        const state = i < current ? 'done' : i === current ? 'current' : 'upcoming'
        const content = (
          <>
            <span className="stepper__index" aria-hidden="true">
              {state === 'done' ? <Icon name="check" size={14} strokeWidth={3} /> : i + 1}
            </span>
            <span className="stepper__label">{label}</span>
            {state === 'done' && <span className="visually-hidden"> (completed)</span>}
          </>
        )
        return (
          <li
            key={label}
            className={`stepper__step stepper__step--${state}`}
            aria-current={state === 'current' ? 'step' : undefined}
          >
            {state === 'done' && onSelect ? (
              <button type="button" className="stepper__button" onClick={() => onSelect(i)}>
                {content}
              </button>
            ) : (
              <span className="stepper__button">{content}</span>
            )}
          </li>
        )
      })}
    </ol>
  )
}
