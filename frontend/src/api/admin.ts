import { adminClient } from './client'
import type { AdminUser, AdminUserUpdate, MaterialNorm, MaterialNormUpdate } from '@/types/admin-user'

export async function getUsers(): Promise<AdminUser[]> {
  const { data } = await adminClient.get<AdminUser[]>('/users')
  return data
}

export async function updateUser(id: number, payload: AdminUserUpdate): Promise<AdminUser> {
  const { data } = await adminClient.put<AdminUser>(`/users/${id}`, payload)
  return data
}

export async function getMaterialNorms(): Promise<MaterialNorm[]> {
  const { data } = await adminClient.get<MaterialNorm[]>('/material-norms')
  return data
}

export async function updateMaterialNorm(id: number, payload: MaterialNormUpdate): Promise<MaterialNorm> {
  const { data } = await adminClient.put<MaterialNorm>(`/material-norms/${id}`, payload)
  return data
}
