import { WIZARD_STEPS } from '../wizardSteps'

/** Wizard progress indicator. `current` is the 0-based index of the active step. */
export function Stepper({ current }: { current: number }) {
  return (
    <ol className="stepper" aria-label="Return steps">
      {WIZARD_STEPS.map((label, i) => (
        <li
          key={label}
          className={i < current ? 'done' : i === current ? 'current' : undefined}
          aria-current={i === current ? 'step' : undefined}
        >
          <span className="stepper__index">{i + 1}</span> {label}
        </li>
      ))}
    </ol>
  )
}
