import { createContext, useContext } from 'react'

import type { Tone } from '../../lib/labels'

export interface ToastInput {
  tone?: Extract<Tone, 'success' | 'danger' | 'info'>
  title: string
  body?: string
}

export const ToastContext = createContext<((toast: ToastInput) => void) | null>(null)

export function useToast() {
  const push = useContext(ToastContext)
  if (!push) throw new Error('useToast must be used inside <ToastProvider>')
  return push
}
