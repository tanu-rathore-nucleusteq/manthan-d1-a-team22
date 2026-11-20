import { PageHeader } from '../../../components/ui/PageHeader'

export function InspectionPage() {
  return (
    <>
      <PageHeader title="Inspect a return" subtitle="Scan or type the code on the label." />
      <form className="form" aria-label="Find return by label" onSubmit={(e) => e.preventDefault()}>
        <label>
          Label code
          <input name="labelCode" required autoFocus autoComplete="off" />
        </label>
        <button type="submit">Open return</button>
      </form>
    </>
  )
}
