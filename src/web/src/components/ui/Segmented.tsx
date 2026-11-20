import { useId } from 'react'

interface SegmentedProps<T extends string> {
  legend: string
  hideLegend?: boolean
  options: { value: T; label: string; hint?: string }[]
  value: T | null
  onChange: (value: T) => void
  size?: 'md' | 'sm'
}

/** Radio group styled as a segmented control: arrow keys move between options. */
export function Segmented<T extends string>({
  legend,
  hideLegend,
  options,
  value,
  onChange,
  size = 'md',
}: SegmentedProps<T>) {
  const name = useId()
  return (
    <fieldset className={size === 'sm' ? 'segmented segmented--sm' : 'segmented'}>
      <legend className={hideLegend ? 'visually-hidden' : 'segmented__legend'}>{legend}</legend>
      <div className="segmented__options">
        {options.map((option) => (
          <label key={option.value} className="segmented__option" title={option.hint}>
            <input
              type="radio"
              name={name}
              value={option.value}
              checked={value === option.value}
              onChange={() => onChange(option.value)}
            />
            <span>{option.label}</span>
          </label>
        ))}
      </div>
    </fieldset>
  )
}
