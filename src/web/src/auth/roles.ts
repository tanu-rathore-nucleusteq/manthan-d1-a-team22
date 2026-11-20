import type { IconName } from '../components/ui/Icon'

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

export interface NavItem {
  to: string
  label: string
  icon: IconName
  end?: boolean
}

/** Navigation shown to each staff role. */
export const NAV_BY_ROLE: Record<Role, NavItem[]> = {
  warehouse_agent: [{ to: '/warehouse', label: 'Inspection queue', icon: 'clipboardCheck' }],
  finance_reviewer: [
    { to: '/finance', label: 'Approvals', icon: 'shieldCheck', end: true },
    { to: '/finance/ledger', label: 'Ledger', icon: 'receipt' },
  ],
  operations_manager: [
    { to: '/dashboard', label: 'Dashboard', icon: 'dashboard' },
    { to: '/team', label: 'Team', icon: 'users' },
  ],
}

/** Short workspace name shown above the staff navigation. */
export const WORKSPACE_BY_ROLE: Record<Role, string> = {
  warehouse_agent: 'Warehouse',
  finance_reviewer: 'Finance',
  operations_manager: 'Operations',
}
