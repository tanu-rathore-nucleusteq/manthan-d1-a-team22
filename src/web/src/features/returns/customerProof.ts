/**
 * The customer proves ownership of a return with the order email (CustomerProofRequest).
 * We keep it per return code for this tab only, so the label and status pages survive a reload.
 */
const key = (returnCode: string) => `returnright.proof.${returnCode.toUpperCase()}`

export function getProof(returnCode: string): string | null {
  try {
    return sessionStorage.getItem(key(returnCode))
  } catch {
    return null
  }
}

export function saveProof(returnCode: string, email: string): void {
  try {
    sessionStorage.setItem(key(returnCode), email.trim().toLowerCase())
  } catch {
    // Storage blocked: the customer re-enters the email on reload.
  }
}
