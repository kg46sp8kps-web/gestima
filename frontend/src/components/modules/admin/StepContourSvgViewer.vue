<script setup lang="ts">
/**
 * STEP Contour SVG Viewer
 *
 * Renders 2D profile SVG from contour points (outer/inner).
 * Shows: centerline, dimension labels, contour path visualization.
 */

import { computed } from 'vue'

interface ContourPoint {
  r: number
  z: number
}

interface ProfileData {
  total_length: number | null
  max_diameter: number | null
  outer_contour: ContourPoint[]
  inner_contour: ContourPoint[]
  holes: unknown[]
}

const props = defineProps<{
  profile: ProfileData
  filename: string
}>()

// SVG colors - using design system compliant values
// Note: These are hardcoded for SVG rendering in JS context where CSS vars don't work
const SVG_COLORS = {
  background: 'rgb(26, 26, 46)',   // --bg-base equivalent (dark theme)
  centerline: 'rgb(38, 38, 38)',   // --border-default (#262626)
  outerContour: 'rgb(79, 195, 247)',  // light blue (SVG visualization specific)
  innerContour: 'rgb(239, 83, 80)',   // red (SVG visualization specific)
  label: 'rgb(163, 163, 163)',     // --text-secondary (#a3a3a3)
}

function contourToSvgPath(points: ContourPoint[], scale: number, offsetX: number, cy: number, offsetZ: number): string {
  if (points.length < 2) return ''
  const parts = points.map((p, i) => {
    const x = offsetX + (p.z + offsetZ) * scale
    const y = cy - p.r * scale
    return `${i === 0 ? 'M' : 'L'} ${x.toFixed(1)} ${y.toFixed(1)}`
  })
  return parts.join(' ')
}

const svgContent = computed(() => {
  const outer = props.profile.outer_contour
  const inner = props.profile.inner_contour
  if (outer.length < 2) return ''

  // Debug: log contour bounds
  console.log(`[SVG] ${props.filename}: outer=${outer.length} pts, inner=${inner.length} pts`)

  const maxZ = Math.max(...outer.map(p => p.z), 1)
  const maxR = Math.max(...outer.map(p => p.r), 1)
  const minZ = Math.min(...outer.map(p => p.z), 0)
  const minR = Math.min(...outer.map(p => p.r), 0)

  console.log(`[SVG] Bounds: Z=[${minZ.toFixed(1)}, ${maxZ.toFixed(1)}], R=[${minR.toFixed(1)}, ${maxR.toFixed(1)}]`)

  const padding = 40
  const svgW = 600
  const svgH = 300
  const drawW = svgW - padding * 2
  const drawH = svgH - padding * 2

  // Calculate scale based on ACTUAL range (not just max)
  const rangeZ = maxZ - minZ
  const rangeR = maxR - minR
  const scaleZ = rangeZ > 0 ? drawW / rangeZ : 1
  const scaleR = rangeR > 0 ? (drawH / 2) / rangeR : 1
  const scale = Math.min(scaleZ, scaleR)

  // Offset to handle negative Z values
  const offsetZ = -minZ
  const cx = padding
  const cy = svgH / 2

  console.log(`[SVG] Scale: ${scale.toFixed(2)}, offsetZ: ${offsetZ.toFixed(1)}`)

  // Build SVG
  let svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${svgW} ${svgH}" style="width:100%;height:100%">`

  // Background
  svg += `<rect width="${svgW}" height="${svgH}" fill="${SVG_COLORS.background}" rx="4"/>`

  // Centerline
  const lineStartX = cx
  const lineEndX = cx + rangeZ * scale
  svg += `<line x1="${lineStartX}" y1="${cy}" x2="${lineEndX}" y2="${cy}" stroke="${SVG_COLORS.centerline}" stroke-dasharray="4,4" stroke-width="1"/>`

  // Outer contour (top half)
  const outerPath = contourToSvgPath(outer, scale, cx, cy, offsetZ)
  svg += `<path d="${outerPath}" fill="none" stroke="${SVG_COLORS.outerContour}" stroke-width="2"/>`

  // Mirror (bottom half)
  const outerMirror = outer.map(p => ({ r: -p.r, z: p.z }))
  const mirrorPath = contourToSvgPath(outerMirror, scale, cx, cy, offsetZ)
  svg += `<path d="${mirrorPath}" fill="none" stroke="${SVG_COLORS.outerContour}" stroke-width="2"/>`

  // Inner contour
  if (inner.length >= 2) {
    const innerPath = contourToSvgPath(inner, scale, cx, cy, offsetZ)
    svg += `<path d="${innerPath}" fill="none" stroke="${SVG_COLORS.innerContour}" stroke-width="1.5" stroke-dasharray="4,2"/>`

    const innerMirror = inner.map(p => ({ r: -p.r, z: p.z }))
    const innerMirrorPath = contourToSvgPath(innerMirror, scale, cx, cy, offsetZ)
    svg += `<path d="${innerMirrorPath}" fill="none" stroke="${SVG_COLORS.innerContour}" stroke-width="1.5" stroke-dasharray="4,2"/>`
  }

  // Dimension labels
  const L = props.profile.total_length
  const D = props.profile.max_diameter
  if (L) {
    svg += `<text x="${cx + rangeZ * scale / 2}" y="${svgH - 8}" text-anchor="middle" fill="${SVG_COLORS.label}" font-size="12" font-weight="500">L = ${L.toFixed(1)} mm</text>`
  }
  if (D) {
    svg += `<text x="${svgW - 12}" y="${cy - 6}" text-anchor="end" fill="${SVG_COLORS.label}" font-size="12" font-weight="500">Ø${D.toFixed(1)}</text>`
  }

  // Contour points (visible markers)
  outer.forEach(p => {
    const x = cx + (p.z + offsetZ) * scale
    const y = cy - p.r * scale
    svg += `<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="2.5" fill="${SVG_COLORS.outerContour}" opacity="0.7"/>`
  })

  // Inner contour points
  if (inner.length >= 2) {
    inner.forEach(p => {
      const x = cx + (p.z + offsetZ) * scale
      const y = cy - p.r * scale
      svg += `<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="2" fill="${SVG_COLORS.innerContour}" opacity="0.7"/>`
    })
  }

  svg += '</svg>'
  return svg
})
</script>

<template>
  <div class="svg-preview">
    <div v-html="svgContent" class="svg-container"></div>
  </div>
</template>

<style scoped>
.svg-preview {
  background: var(--bg-primary);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.svg-container {
  width: 100%;
  aspect-ratio: 600 / 300;
  min-height: 300px;
}

.svg-container :deep(svg) {
  width: 100%;
  height: 100%;
}
</style>
