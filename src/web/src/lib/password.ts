/** Same rule as the API (CreateStaffRequest): at least 10 characters with a letter and a number. */
export const PASSWORD_HINT = 'At least 10 characters, with a letter and a number.'

export function passwordProblem(password: string): string | undefined {
  if (password.length < 10) return 'Use at least 10 characters.'
  if (!/[A-Za-z]/.test(password) || !/\d/.test(password))
    return 'Use at least one letter and one number.'
  return undefined
}
