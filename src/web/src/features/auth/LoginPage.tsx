import { PageHeader } from '../../components/ui/PageHeader'

export function LoginPage() {
  return (
    <>
      <PageHeader title="Staff sign in" subtitle="Warehouse, finance and operations staff." />
      <form className="form" aria-label="Staff sign in" onSubmit={(e) => e.preventDefault()}>
        <label>
          Email
          <input name="email" type="email" required autoComplete="username" />
        </label>
        <label>
          Password
          <input name="password" type="password" required autoComplete="current-password" />
        </label>
        <button type="submit">Sign in</button>
      </form>
    </>
  )
}
