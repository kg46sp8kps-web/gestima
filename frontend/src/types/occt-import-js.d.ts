/**
 * Type declarations for occt-import-js
 *
 * WASM-based OpenCascade STEP/IGES/BREP importer.
 * @see https://github.com/nickkang1/occt-import-js
 */

declare module 'occt-import-js' {
  interface OcctImportParams {
    linearUnit?: 'millimeter' | 'centimeter' | 'meter' | 'inch' | 'foot'
    linearDeflectionType?: 'bounding_box_ratio' | 'absolute_value'
    linearDeflection?: number
    angularDeflection?: number
  }

  interface OcctBrepFace {
    first: number
    last: number
    color: [number, number, number] | null
  }

  interface OcctMesh {
    name: string
    color?: [number, number, number]
    brep_faces: OcctBrepFace[]
    attributes: {
      position: { array: number[] }
      normal?: { array: number[] }
    }
    index: { array: number[] }
  }

  interface OcctNode {
    name: string
    meshes: number[]
    children: OcctNode[]
  }

  interface OcctResult {
    success: boolean
    root: OcctNode
    meshes: OcctMesh[]
  }

  interface OcctInstance {
    ReadStepFile(content: Uint8Array, params: OcctImportParams | null): OcctResult
    ReadBrepFile(content: Uint8Array, params: OcctImportParams | null): OcctResult
    ReadIgesFile(content: Uint8Array, params: OcctImportParams | null): OcctResult
  }

  interface OcctModuleConfig {
    locateFile?: (filename: string, scriptDirectory?: string) => string
    [key: string]: unknown
  }

  function occtimportjs(config?: OcctModuleConfig): Promise<OcctInstance>
  export default occtimportjs
}
