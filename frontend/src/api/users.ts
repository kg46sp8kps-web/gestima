/**
 * GESTIMA Users Admin API
 */

import { adminClient } from './client'
import type {
  User,
  UserCreateRequest,
  UserUpdateRequest,
  PasswordChangeRequest
} from '@/types/auth'

export async function getUsers(): Promise<User[]> {
  const { data } = await adminClient.get<User[]>('/users')
  return data
}

export async function createUser(payload: UserCreateRequest): Promise<User> {
  const { data } = await adminClient.post<User>('/users', payload)
  return data
}

export async function updateUser(id: number, payload: UserUpdateRequest): Promise<User> {
  const { data } = await adminClient.put<User>(`/users/${id}`, payload)
  return data
}

export async function changeUserPassword(id: number, payload: PasswordChangeRequest): Promise<void> {
  await adminClient.put(`/users/${id}/password`, payload)
}

export async function deleteUser(id: number): Promise<void> {
  await adminClient.delete(`/users/${id}`)
}
