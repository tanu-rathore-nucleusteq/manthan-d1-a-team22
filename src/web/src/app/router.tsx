import type { ReactNode } from 'react'
import { createBrowserRouter, Navigate } from 'react-router'

import { RequireRole } from '../auth/RequireRole'
import { ROLES, type Role } from '../auth/roles'
import { LoginPage } from '../features/auth/LoginPage'
import { ManagerDashboardPage } from '../features/dashboard/pages/ManagerDashboardPage'
import { ApprovalDetailPage } from '../features/finance/pages/ApprovalDetailPage'
import { ApprovalQueuePage } from '../features/finance/pages/ApprovalQueuePage'
import { LedgerPage } from '../features/finance/pages/LedgerPage'
import { OrderLookupPage } from '../features/returns/pages/OrderLookupPage'
import { ReturnLabelPage } from '../features/returns/pages/ReturnLabelPage'
import { ReturnStatusPage } from '../features/returns/pages/ReturnStatusPage'
import { ReturnWizardPage } from '../features/returns/pages/ReturnWizardPage'
import { TrackReturnPage } from '../features/returns/pages/TrackReturnPage'
import { TeamPage } from '../features/team/pages/TeamPage'
import { InspectionPage } from '../features/warehouse/pages/InspectionPage'
import { WarehouseQueuePage } from '../features/warehouse/pages/WarehouseQueuePage'
import { AppLayout } from './AppLayout'
import { NotFoundPage } from './NotFoundPage'

const staff = (roles: Role[], page: ReactNode) => <RequireRole roles={roles}>{page}</RequireRole>

export const router = createBrowserRouter([
  {
    element: <AppLayout />,
    children: [
      { index: true, element: <Navigate to="/returns" replace /> },

      // Customer: public; the order email proves ownership
      { path: 'returns', element: <OrderLookupPage /> },
      { path: 'returns/track', element: <TrackReturnPage /> },
      { path: 'returns/new/:orderNumber', element: <ReturnWizardPage /> },
      { path: 'returns/:returnCode/label', element: <ReturnLabelPage /> },
      { path: 'returns/:returnCode', element: <ReturnStatusPage /> },

      // Staff
      { path: 'login', element: <LoginPage /> },
      { path: 'warehouse', element: staff([ROLES.warehouseAgent], <WarehouseQueuePage />) },
      {
        path: 'warehouse/returns/:returnCode',
        element: staff([ROLES.warehouseAgent], <InspectionPage />),
      },
      { path: 'finance', element: staff([ROLES.financeReviewer], <ApprovalQueuePage />) },
      {
        path: 'finance/returns/:returnCode',
        element: staff([ROLES.financeReviewer], <ApprovalDetailPage />),
      },
      { path: 'finance/ledger', element: staff([ROLES.financeReviewer], <LedgerPage />) },
      { path: 'dashboard', element: staff([ROLES.operationsManager], <ManagerDashboardPage />) },
      { path: 'team', element: staff([ROLES.operationsManager], <TeamPage />) },

      { path: '*', element: <NotFoundPage /> },
    ],
  },
])
