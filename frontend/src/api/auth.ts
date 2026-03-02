import type { TokenResponse, PinLoginResponse, User } from '@/types/auth'
import { apiClient } from './client'

/** Login — POST /auth/login with JSON, server sets HttpOnly cookie */
export async function login(username: string, password: string): Promise<TokenResponse> {
  const { data } = await apiClient.post<TokenResponse>('/auth/login', { username, password })
  return data
}

/** Get current user info — reads from HttpOnly cookie (withCredentials) */
export async function getMe(): Promise<User> {
  const { data } = await apiClient.get<User>('/auth/me')
  return data
}

/** Logout — DELETE cookie on server */
export async function logout(): Promise<void> {
  await apiClient.post('/auth/logout')
}

/** PIN login — POST /auth/pin-login, server sets HttpOnly cookie + returns user data */
export async function pinLogin(pin: string): Promise<PinLoginResponse> {
  const { data } = await apiClient.post<PinLoginResponse>('/auth/pin-login', { pin })
  return data
}
