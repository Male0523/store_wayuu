import { useEffect, useEffectEvent, useState, type ReactNode } from 'react'
import { api, ApiError } from '../lib/api'
import type { SessionUser } from '../types'
import { UserContext } from './user-context'

export function UserProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<SessionUser | null>(null)
  const [loaded, setLoaded] = useState(false)
  const [sessionError, setSessionError] = useState('')

  const refreshSession = useEffectEvent(async () => {
    try {
      const response = await api.me()
      setUser(response.user)
      setSessionError('')
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        setUser(null)
        setSessionError('')
      } else if (error instanceof ApiError && error.status === 403) {
        setUser(null)
        setSessionError('La cuenta no tiene un rol de acceso asignado. Contacta a administración.')
      } else if (error instanceof ApiError && error.status > 0) {
        setSessionError(`Django respondió HTTP ${error.status}. ${error.message}`)
      } else {
        setSessionError('No fue posible verificar la sesión con Django. Revisa la conexión e inténtalo de nuevo.')
      }
    } finally {
      setLoaded(true)
    }
  })

  const expireSession = useEffectEvent(() => {
    setUser(null)
    setLoaded(true)
    setSessionError('')
  })

  useEffect(() => {
    const refresh = () => { void refreshSession() }
    const expire = () => expireSession()
    const refreshVisibleSession = () => {
      if (document.visibilityState === 'visible') refresh()
    }
    const initialRefresh = window.setTimeout(refresh, 0)
    window.addEventListener('wayuu:session-change', refresh)
    window.addEventListener('wayuu:session-expired', expire)
    window.addEventListener('focus', refresh)
    document.addEventListener('visibilitychange', refreshVisibleSession)
    return () => {
      window.clearTimeout(initialRefresh)
      window.removeEventListener('wayuu:session-change', refresh)
      window.removeEventListener('wayuu:session-expired', expire)
      window.removeEventListener('focus', refresh)
      document.removeEventListener('visibilitychange', refreshVisibleSession)
    }
  }, [])

  async function login(username: string, password: string) {
    const response = await api.login(username, password)
    setUser(response.user)
    setLoaded(true)
    setSessionError('')
    return response.user
  }

  async function register(values: Record<string, string>, craftswoman = false) {
    const response = await api.register(values, craftswoman)
    setUser(response.user)
    setLoaded(true)
    setSessionError('')
    return response.user
  }

  async function logout() {
    try {
      await api.logout()
    } catch (error) {
      if (!(error instanceof ApiError) || error.status !== 401) throw error
    }
    setUser(null)
    setLoaded(true)
    setSessionError('')
  }

  return <UserContext.Provider value={{ user, loaded, sessionError, login, register, logout }}>{children}</UserContext.Provider>
}
