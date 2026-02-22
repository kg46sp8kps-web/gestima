import { apiClient } from './client'
import type { UserLayout, UserLayoutCreate, UserLayoutUpdate } from '@/types/layout'

export async function getAll(): Promise<UserLayout[]> {
  const { data } = await apiClient.get<UserLayout[]>('/user-layouts')
  return data
}

export async function create(payload: UserLayoutCreate): Promise<UserLayout> {
  const { data } = await apiClient.post<UserLayout>('/user-layouts', payload)
  return data
}

export async function update(id: number, payload: UserLayoutUpdate): Promise<UserLayout> {
  const { data } = await apiClient.put<UserLayout>(`/user-layouts/${id}`, payload)
  return data
}

export async function remove(id: number): Promise<void> {
  await apiClient.delete(`/user-layouts/${id}`)
}
