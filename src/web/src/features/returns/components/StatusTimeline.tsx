import type { ReturnStatus, StatusEventResponse } from '../../../api/types'
import { formatDateTime } from '../../../lib/format'
import { STATUS_FLOW, STATUS_LABEL } from '../../../lib/labels'

/** Past events with their time and note, then the steps still to come. */
export function StatusTimeline({
  status,
  timeline,
}: {
  status: ReturnStatus
  timeline: StatusEventResponse[]
}) {
  const final = status === 'refunded' || status === 'rejected'
  const upcoming = final ? [] : STATUS_FLOW.slice(STATUS_FLOW.indexOf(status) + 1)

  return (
    <ol className="timeline" aria-label="Return status history">
      {timeline.map((event, i) => {
        const current = i === timeline.length - 1
        const tone = event.status === 'rejected' ? 'danger' : current && !final ? 'current' : 'done'
        return (
          <li
            key={`${event.status}-${event.at}`}
            className={`timeline__item timeline__item--${tone}`}
          >
            <span className="timeline__marker" aria-hidden="true" />
            <div className="timeline__content">
              <span className="timeline__title" aria-current={current ? 'step' : undefined}>
                {STATUS_LABEL[event.status]}
              </span>
              <time className="timeline__time" dateTime={event.at}>
                {formatDateTime(event.at)}
              </time>
              {event.note && <p className="timeline__note">{event.note}</p>}
            </div>
          </li>
        )
      })}
      {upcoming.map((step) => (
        <li key={step} className="timeline__item timeline__item--upcoming">
          <span className="timeline__marker" aria-hidden="true" />
          <div className="timeline__content">
            <span className="timeline__title">{STATUS_LABEL[step]}</span>
            <span className="timeline__time">Not yet</span>
          </div>
        </li>
      ))}
    </ol>
  )
}
