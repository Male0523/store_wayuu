import { createContext, useContext } from 'react'
import type { SessionUser } from '../types'

export interface UserSession {
  user: SessionUser | null
  loaded: boolean
  sessionError: string
  login: (username: string, password: string) => Promise<SessionUser>
  register: (values: Record<string, string>, craftswoman?: boolean) => Promise<SessionUser>
  logout: () => Promise<void>
}

export const UserContext = createContext<UserSession | null>(null)

export function useUserSession() {
  const session = useContext(UserContext)
  if (!session) throw new Error('useUserSession debe utilizarse dentro de UserProvider.')
  return session
}
