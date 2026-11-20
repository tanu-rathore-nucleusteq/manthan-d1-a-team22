/** Staff roles. Values must match the role names the API puts in the JWT. */
export const ROLES = {
  warehouseAgent: 'warehouse_agent',
  financeReviewer: 'finance_reviewer',
  operationsManager: 'operations_manager',
} as const

export type Role = (typeof ROLES)[keyof typeof ROLES]

/** Landing page for each staff role after login. */
export const HOME_BY_ROLE: Record<Role, string> = {
  warehouse_agent: '/warehouse',
  finance_reviewer: '/finance',
  operations_manager: '/dashboard',
}
