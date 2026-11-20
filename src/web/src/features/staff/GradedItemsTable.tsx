import type { Money, ReturnItemResponse } from '../../api/types'
import { Badge } from '../../components/ui/Badge'
import { formatInr } from '../../lib/format'

export function GradedItemsTable({
  items,
  total,
}: {
  items: ReturnItemResponse[]
  total?: Money | null
}) {
  return (
    <div className="table-wrap">
      <table className="table">
        <caption className="visually-hidden">Graded items and refund amounts</caption>
        <thead>
          <tr>
            <th scope="col">Item</th>
            <th scope="col" className="num">
              Qty
            </th>
            <th scope="col">Grade</th>
            <th scope="col">Decision</th>
            <th scope="col" className="num">
              Refund
            </th>
          </tr>
        </thead>
        <tbody>
          {items.map((i) => (
            <tr key={i.return_item_id}>
              <td>{i.product_name}</td>
              <td className="num">{i.quantity}</td>
              <td>{i.grade ?? '—'}</td>
              <td>
                {i.decision ? (
                  <Badge tone={i.decision === 'accept' ? 'success' : 'danger'}>
                    {i.decision === 'accept' ? 'Accepted' : 'Rejected'}
                  </Badge>
                ) : (
                  '—'
                )}
              </td>
              <td className="num">{formatInr(i.refund_amount)}</td>
            </tr>
          ))}
        </tbody>
        {total !== undefined && (
          <tfoot>
            <tr>
              <th scope="row" colSpan={4}>
                Refund total
              </th>
              <td className="num">
                <strong>{formatInr(total)}</strong>
              </td>
            </tr>
          </tfoot>
        )}
      </table>
    </div>
  )
}
