import { createBrowserRouter, Navigate } from 'react-router'

import { RequireRole } from '../auth/RequireRole'
import { ROLES } from '../auth/roles'
import { LoginPage } from '../features/auth/LoginPage'
import { ManagerDashboardPage } from '../features/dashboard/pages/ManagerDashboardPage'
import { ApprovalQueuePage } from '../features/finance/pages/ApprovalQueuePage'
import { OrderLookupPage } from '../features/returns/pages/OrderLookupPage'
import { ReturnLabelPage } from '../features/returns/pages/ReturnLabelPage'
import { ReturnStatusPage } from '../features/returns/pages/ReturnStatusPage'
import { ReturnWizardPage } from '../features/returns/pages/ReturnWizardPage'
import { InspectionPage } from '../features/warehouse/pages/InspectionPage'
import { AppLayout } from './AppLayout'
import { NotFoundPage } from './NotFoundPage'

export const router = createBrowserRouter([
  {
    element: <AppLayout />,
    children: [
      { index: true, element: <Navigate to="/returns" replace /> },

      // Customer: public, identified by order number + email
      { path: 'returns', element: <OrderLookupPage /> },
      { path: 'returns/new/:orderId', element: <ReturnWizardPage /> },
      { path: 'returns/:returnId/label', element: <ReturnLabelPage /> },
      { path: 'returns/:returnId', element: <ReturnStatusPage /> },

      // Staff
      { path: 'login', element: <LoginPage /> },
      {
        path: 'warehouse',
        element: (
          <RequireRole roles={[ROLES.warehouseAgent]}>
            <InspectionPage />
          </RequireRole>
        ),
      },
      {
        path: 'finance',
        element: (
          <RequireRole roles={[ROLES.financeReviewer]}>
            <ApprovalQueuePage />
          </RequireRole>
        ),
      },
      {
        path: 'dashboard',
        element: (
          <RequireRole roles={[ROLES.operationsManager]}>
            <ManagerDashboardPage />
          </RequireRole>
        ),
      },

      { path: '*', element: <NotFoundPage /> },
    ],
  },
])
