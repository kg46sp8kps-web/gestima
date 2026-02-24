/// <reference types="vite/client" />

declare module 'occt-import-js' {
  interface OcctMesh {
    name: string
    color?: [number, number, number]
    attributes: {
      position: { array: number[] }
      normal?: { array: number[] }
    }
    index: { array: number[] }
    brep_faces: Array<{ first: number; last: number; color: [number, number, number] | null }>
  }
  interface OcctResult {
    success: boolean
    meshes: OcctMesh[]
  }
  interface OcctInstance {
    ReadStepFile(buf: Uint8Array, params: object | null): OcctResult
    ReadIgesFile(buf: Uint8Array, params: object | null): OcctResult
    ReadBrepFile(buf: Uint8Array, params: object | null): OcctResult
  }
  type OcctFactory = (opts?: { locateFile?: (path: string) => string }) => Promise<OcctInstance>
  const factory: OcctFactory
  export default factory
}
