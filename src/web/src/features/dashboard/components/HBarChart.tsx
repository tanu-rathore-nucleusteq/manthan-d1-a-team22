import { useState } from 'react'

import { Button } from '../../../components/ui/Button'

export interface BarDatum {
  label: string
  value: number
  /** Text printed at the bar tip, e.g. "11.4%". */
  display: string
  /** Extra line in the tooltip, e.g. "47 returns of 412 orders". */
  detail?: string
}

interface HBarChartProps {
  data: BarDatum[]
  /** Names the measure for screen readers and the table header. */
  measure: string
}

/**
 * Single-series horizontal bars: one hue, value at the tip, tooltip on hover and keyboard focus,
 * and a table view so no number relies on the chart alone.
 */
export function HBarChart({ data, measure }: HBarChartProps) {
  const [asTable, setAsTable] = useState(false)
  const max = Math.max(...data.map((d) => d.value), 0) || 1

  return (
    <div className="hbar">
      <div className="hbar__toolbar">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setAsTable(!asTable)}
          aria-pressed={asTable}
        >
          {asTable ? 'Show chart' : 'Show table'}
        </Button>
      </div>

      {asTable ? (
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th scope="col">Category</th>
                <th scope="col" className="num">
                  {measure}
                </th>
                <th scope="col">Detail</th>
              </tr>
            </thead>
            <tbody>
              {data.map((d) => (
                <tr key={d.label}>
                  <td>{d.label}</td>
                  <td className="num">{d.display}</td>
                  <td className="muted">{d.detail ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <ul className="hbar__rows" aria-label={measure}>
          {data.map((d) => (
            <li key={d.label} className="hbar__row">
              <span className="hbar__label">{d.label}</span>
              <span
                className="hbar__track"
                tabIndex={0}
                aria-label={`${d.label}: ${d.display}${d.detail ? `, ${d.detail}` : ''}`}
              >
                <span className="hbar__bar" style={{ width: `${(d.value / max) * 100}%` }} />
                <span className="hbar__value">{d.display}</span>
                <span className="hbar__tooltip" role="presentation">
                  <strong>{d.label}</strong>
                  <span>{d.display}</span>
                  {d.detail && <span className="muted">{d.detail}</span>}
                </span>
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
