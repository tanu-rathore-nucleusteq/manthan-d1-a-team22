/** Staff roles. Values match the backend Role enum (src/api/returnright/domain/enums.py). */
export const ROLES = {
  warehouseAgent: 'warehouse_agent',
  financeReviewer: 'finance_reviewer',
  operationsManager: 'operations_manager',
} as const

export type Role = (typeof ROLES)[keyof typeof ROLES]

export const ROLE_LABEL: Record<Role, string> = {
  warehouse_agent: 'Warehouse agent',
  finance_reviewer: 'Finance reviewer',
  operations_manager: 'Operations manager',
}

/** Landing page for each staff role after login. */
export const HOME_BY_ROLE: Record<Role, string> = {
  warehouse_agent: '/warehouse',
  finance_reviewer: '/finance',
  operations_manager: '/dashboard',
}

/** Navigation shown to each staff role. */
export const NAV_BY_ROLE: Record<Role, { to: string; label: string; end?: boolean }[]> = {
  warehouse_agent: [{ to: '/warehouse', label: 'Inspection queue' }],
  finance_reviewer: [
    { to: '/finance', label: 'Approvals', end: true },
    { to: '/finance/ledger', label: 'Ledger' },
  ],
  operations_manager: [{ to: '/dashboard', label: 'Dashboard' }],
}
