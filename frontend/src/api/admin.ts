import { adminClient } from './client'
import type { AdminUser, MaterialNorm } from '@/types/admin-user'

export async function getUsers(): Promise<AdminUser[]> {
  const { data } = await adminClient.get<AdminUser[]>('/users')
  return data
}

export async function getMaterialNorms(): Promise<MaterialNorm[]> {
  const { data } = await adminClient.get<MaterialNorm[]>('/material-norms')
  return data
}
