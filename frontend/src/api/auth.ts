import axios from 'axios'
import type { TokenResponse, User } from '@/types/auth'

/** Login — uses form encoding as required by OAuth2 password flow */
export async function login(username: string, password: string): Promise<TokenResponse> {
  const params = new URLSearchParams()
  params.append('username', username)
  params.append('password', password)

  const { data } = await axios.post<TokenResponse>('/api/auth/token', params, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  })
  return data
}

/** Get current user info */
export async function getMe(): Promise<User> {
  const token = localStorage.getItem('access_token')
  const { data } = await axios.get<User>('/api/auth/me', {
    headers: { Authorization: `Bearer ${token}` },
  })
  return data
}
