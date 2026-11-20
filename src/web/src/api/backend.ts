import { createHttpBackend } from './httpBackend'
import { mockBackend } from './mock/mockBackend'
import type {
  ApprovalDecisionRequest,
  CreateReturnRequest,
  CreateStaffRequest,
  CustomerProofRequest,
  DashboardResponse,
  InspectionRequest,
  InspectionResultResponse,
  LedgerEntryResponse,
  LoginRequest,
  OrderLookupRequest,
  OrderLookupResponse,
  PageResponse,
  PendingApprovalResponse,
  ReturnDetailResponse,
  ReturnLabelResponse,
  ReturnSummaryResponse,
  StaffMemberResponse,
  TokenResponse,
  UpdateStaffRequest,
} from './types'

/**
 * Every call the UI makes. Screens use these only through the hooks in features/<area>/api.ts,
 * so swapping the mock for the HTTP implementation touches this file alone.
 */
export interface ReturnRightBackend {
  // Staff auth
  login(body: LoginRequest): Promise<TokenResponse>

  // Customer
  lookupOrder(body: OrderLookupRequest): Promise<OrderLookupResponse>
  createReturn(body: CreateReturnRequest): Promise<ReturnDetailResponse>
  uploadReturnPhoto(
    returnCode: string,
    email: string,
    returnItemId: number,
    photo: File,
  ): Promise<void>
  getReturn(returnCode: string, proof: CustomerProofRequest): Promise<ReturnDetailResponse>
  getLabel(returnCode: string, proof: CustomerProofRequest): Promise<ReturnLabelResponse>
  markShipped(returnCode: string, proof: CustomerProofRequest): Promise<ReturnDetailResponse>

  // Warehouse agent
  listWarehouseQueue(
    status: 'in_transit' | 'received',
  ): Promise<PageResponse<ReturnSummaryResponse>>
  getReturnForStaff(returnCode: string): Promise<ReturnDetailResponse>
  markReceived(returnCode: string): Promise<ReturnDetailResponse>
  inspectReturn(returnCode: string, body: InspectionRequest): Promise<InspectionResultResponse>

  // Finance reviewer
  listPendingApprovals(): Promise<PendingApprovalResponse[]>
  decideApproval(
    returnCode: string,
    body: ApprovalDecisionRequest,
  ): Promise<PendingApprovalResponse>
  listLedger(): Promise<PageResponse<LedgerEntryResponse>>

  // Operations manager
  getDashboard(): Promise<DashboardResponse>
  listStaff(): Promise<StaffMemberResponse[]>
  createStaff(body: CreateStaffRequest): Promise<StaffMemberResponse>
  updateStaff(staffId: number, body: UpdateStaffRequest): Promise<StaffMemberResponse>
}

/**
 * Demo mode: every call is served in the browser by the mock backend, with synthetic data.
 * Off by default now that the API is live; set VITE_USE_MOCKS=true to demo without it.
 */
export const USE_MOCKS = import.meta.env.VITE_USE_MOCKS === 'true'

export const backend: ReturnRightBackend = USE_MOCKS ? mockBackend : createHttpBackend()
