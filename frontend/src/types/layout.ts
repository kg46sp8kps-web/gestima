import type { TileNode } from '@/types/workspace'

export interface UserLayout {
  id: number
  user_id: number
  name: string
  tree_json: TileNode
  is_default: boolean
  show_in_header: boolean
  version: number
  created_at: string
  updated_at: string
}

export interface UserLayoutCreate {
  name: string
  tree_json: TileNode
  is_default?: boolean
  show_in_header?: boolean
}

export interface UserLayoutUpdate {
  name?: string
  tree_json?: TileNode
  is_default?: boolean
  show_in_header?: boolean
  version: number
}
