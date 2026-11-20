/** Same rule as the API's ReturnCode path parameter: 6 to 32 letters, digits or hyphens. */
const RETURN_CODE = /^[A-Za-z0-9-]{6,32}$/

/** Example shown in placeholders and messages; real codes look like RR-7K2P9QX4. */
export const RETURN_CODE_EXAMPLE = 'RR-7K2P9QX4'

export function isReturnCode(value: string): boolean {
  return RETURN_CODE.test(value.trim())
}
