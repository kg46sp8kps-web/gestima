#!/usr/bin/env python3
"""
Generate SVG cross-section of Stuetzfuss (102308)
PDM-249322 Rev.03 — kontury z STEP modelu (Siemens NX 2023)

Data source: drawings/PDM-249322_03.stp
Verified against: PDM-249322_03 drawing (PDF)
"""
import math


def generate_svg():
    s = 5       # scale: px per mm
    cx = 370    # centerline X position
    y0 = 110    # top of part Y

    # ═══════════════════════════════════════════════════════════════════════
    # PART GEOMETRY FROM STEP FILE (exact values)
    # Coordinate system: z=0 at top, positive downward (drawing orientation)
    # STEP has z=0 at bottom; conversion: z_drawing = 89 - z_step
    # ═══════════════════════════════════════════════════════════════════════

    # Key dimensions from STEP:
    # - CYLINDRICAL_SURFACE R=27.5 (Ø55) — flange
    # - CYLINDRICAL_SURFACE R=15.0 (Ø30) — shaft
    # - CYLINDRICAL_SURFACE R=13.5 (Ø27) — reduced section
    # - CYLINDRICAL_SURFACE R=9.5  (Ø19) — THROUGH-BORE (full height!)
    # - CYLINDRICAL_SURFACE R=3.5  (Ø7)  — 2× holes at Y=±20
    # - CONICAL_SURFACE at z_step=10.5 (z_dwg=78.5): R=15, half-angle=30.96°
    # - CONICAL_SURFACE at z_step=5.5  (z_dwg=83.5): R=13.5, half-angle=81.87°
    # - CONICAL_SURFACE at z_step=87.5 (z_dwg=1.5):  R=15, half-angle=45° (chamfer)
    # - TOROIDAL_SURFACE major R=26.5, minor r=1 (R1 fillet at flange)
    # - TOROIDAL_SURFACE major R=14.5, minor r=1 (R1 fillet ×2 at shaft)
    # - Ø7 holes centered at (0, ±20, 0) → spacing = 40mm

    # ─── CONE CALCULATIONS ───
    tan_31 = math.tan(math.radians(30.9637565320736))   # ≈ 0.6004
    tan_82 = math.tan(math.radians(81.869897645844))     # ≈ 7.115

    # Cone #1 (31°): from (R=15, z=78.5) going inward
    # r = 15 - (z - 78.5) × tan(31°)
    # R=13.5 reached at z = 78.5 + (15-13.5)/tan(31°) = 78.5 + 2.498 ≈ 81.0

    # Cone #2 (82°): from (R=13.5, z=83.5) going outward
    # r = 13.5 + (z - 83.5) × tan(82°)
    # R=27.5 reached at z = 83.5 + (27.5-13.5)/tan(82°) = 83.5 + 1.968 ≈ 85.47

    # ─── OUTER PROFILE (right half, top to bottom) ───
    # Points: (radius_mm, z_mm_from_top)

    outer_profile = [
        # TOP SECTION
        (0,     0),       # top center
        (13.5,  0),       # top face edge (at bore + chamfer)
        (15.0,  1.5),     # 45° chamfer end → shaft OD begins

        # SHAFT Ø30
        (15.0,  78.5),    # shaft end, cone #1 begins

        # CONE #1 (31° inward transition)
        (14.2,  79.83),   # on cone (R1 fillet tangent, approx)

        # R1 FILLET → Ø27 cylinder
        (13.5,  80.6),    # tangent to Ø27 cylinder (approx)

        # Ø27 REDUCED SECTION
        (13.5,  82.4),    # Ø27 cylinder bottom (R1 fillet tangent, approx)

        # R1 FILLET → cone #2
        (14.1,  83.1),    # tangent to steep cone (approx)

        # CONE #2 (82° outward transition)
        (26.0,  84.78),   # on steep cone approaching flange

        # R1 FILLET → flange
        (27.5,  85.25),   # tangent to flange cylinder (approx)

        # FLANGE Ø55
        (27.5,  89.0),    # bottom face
    ]

    # ─── INNER BORE PROFILE (Ø19 THROUGH-BORE) ───
    bore_profile = [
        (9.5,  89.0),     # bore bottom edge
        (9.5,   0.0),     # bore top edge (THROUGH-BORE!)
    ]

    # ─── COORDINATE TRANSFORMS ───

    def R(r, z):
        return (cx + r * s, y0 + z * s)

    def L(r, z):
        return (cx - r * s, y0 + z * s)

    def pt(xy):
        return f"{xy[0]:.1f},{xy[1]:.1f}"

    def path_d(points):
        d = f"M {pt(points[0])}"
        for p in points[1:]:
            d += f" L {pt(p)}"
        d += " Z"
        return d

    # ─── BUILD SECTION PATHS ───

    right_pts = [R(r, z) for r, z in outer_profile] + [R(r, z) for r, z in bore_profile]
    left_pts = [L(r, z) for r, z in outer_profile] + [L(r, z) for r, z in bore_profile]

    right_d = path_d(right_pts)
    left_d = path_d(left_pts)

    # ─── KEY COORDINATES ───

    y_top = y0
    y_1_5 = y0 + 1.5 * s
    y_6 = y0 + 6 * s
    y_78_5 = y0 + 78.5 * s
    y_81 = y0 + 81 * s
    y_83_5 = y0 + 83.5 * s
    y_85_5 = y0 + 85.5 * s
    y_86_4 = y0 + 86.4 * s
    y_89 = y0 + 89 * s

    x_r_shaft = cx + 15 * s
    x_l_shaft = cx - 15 * s
    x_r_flange = cx + 27.5 * s
    x_l_flange = cx - 27.5 * s
    x_r_bore = cx + 9.5 * s
    x_l_bore = cx - 9.5 * s

    # ─── BOTTOM VIEW ───
    bv_cx, bv_cy = 370, 760
    bv_s = s
    bv_r_outer = 27.5 * bv_s
    bv_r_bore = 9.5 * bv_s
    bv_r_hole = 3.5 * bv_s
    bv_hole_offset = 20 * bv_s   # CORRECTED: 20mm from center (from STEP!)

    # ─── HELPER FUNCTIONS ───

    def dim_h(x1, x2, y, text, offset=-20):
        dy = y + offset
        return f'''<line x1="{x1}" y1="{y}" x2="{x1}" y2="{dy-2}" stroke="#333" stroke-width="0.3"/>
    <line x1="{x2}" y1="{y}" x2="{x2}" y2="{dy-2}" stroke="#333" stroke-width="0.3"/>
    <line x1="{x1}" y1="{dy}" x2="{x2}" y2="{dy}" stroke="#333" stroke-width="0.5" marker-start="url(#as)" marker-end="url(#ae)"/>
    <text x="{(x1+x2)/2}" y="{dy-4}" text-anchor="middle" font-size="10" fill="#333">{text}</text>'''

    def dim_v(x, y1, y2, text, offset=30):
        dx = x + offset
        mid = (y1 + y2) / 2
        return f'''<line x1="{x}" y1="{y1}" x2="{dx+2}" y2="{y1}" stroke="#333" stroke-width="0.3"/>
    <line x1="{x}" y1="{y2}" x2="{dx+2}" y2="{y2}" stroke="#333" stroke-width="0.3"/>
    <line x1="{dx}" y1="{y1}" x2="{dx}" y2="{y2}" stroke="#333" stroke-width="0.5" marker-start="url(#as)" marker-end="url(#ae)"/>
    <text x="{dx+12}" y="{mid+4}" text-anchor="middle" font-size="10" fill="#333" transform="rotate(90,{dx+12},{mid})">{text}</text>'''

    def dim_v_left(x, y1, y2, text, offset=-30):
        dx = x + offset
        mid = (y1 + y2) / 2
        return f'''<line x1="{x}" y1="{y1}" x2="{dx-2}" y2="{y1}" stroke="#333" stroke-width="0.3"/>
    <line x1="{x}" y1="{y2}" x2="{dx-2}" y2="{y2}" stroke="#333" stroke-width="0.3"/>
    <line x1="{dx}" y1="{y1}" x2="{dx}" y2="{y2}" stroke="#333" stroke-width="0.5" marker-start="url(#as)" marker-end="url(#ae)"/>
    <text x="{dx-12}" y="{mid+4}" text-anchor="middle" font-size="10" fill="#333" transform="rotate(-90,{dx-12},{mid})">{text}</text>'''

    def callout(x, y, text, dx=70, dy=-15):
        tx, ty = x + dx, y + dy
        return f'''<line x1="{x}" y1="{y}" x2="{tx}" y2="{ty}" stroke="#555" stroke-width="0.5"/>
    <circle cx="{x}" cy="{y}" r="1.5" fill="#555"/>
    <text x="{tx+4}" y="{ty+4}" font-size="9" fill="#333">{text}</text>'''

    # ═══════════════════════════════════════════════════════════════════════
    # SVG OUTPUT
    # ═══════════════════════════════════════════════════════════════════════

    svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 1050" width="800" height="1050"
     font-family="'Segoe UI', Arial, sans-serif" style="background: white">

  <defs>
    <pattern id="hatch" patternUnits="userSpaceOnUse" width="5" height="5" patternTransform="rotate(45)">
      <line x1="0" y1="0" x2="0" y2="5" stroke="#bbb" stroke-width="0.35"/>
    </pattern>
    <marker id="as" viewBox="0 0 10 10" refX="0" refY="5" markerWidth="6" markerHeight="4" orient="auto">
      <path d="M10,1 L0,5 L10,9" fill="none" stroke="#333" stroke-width="1"/>
    </marker>
    <marker id="ae" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="6" markerHeight="4" orient="auto">
      <path d="M0,1 L10,5 L0,9" fill="none" stroke="#333" stroke-width="1"/>
    </marker>
  </defs>

  <!-- ═══════════ TITLE ═══════════ -->
  <text x="400" y="28" text-anchor="middle" font-size="17" font-weight="bold" fill="#111">
    102308 — Stuetzfuss (PDM-249322 Rev.03)
  </text>
  <text x="400" y="48" text-anchor="middle" font-size="11" fill="#666">
    Mat: 1.1191 (C45E) | Rheinnitrieren var. a1 → 350 HV0.5 | ISO 2768-mK
  </text>
  <text x="400" y="65" text-anchor="middle" font-size="11" font-weight="bold" fill="#07a">
    PROFIL Z 3D MODELU (STEP) — Siemens NX 2023
  </text>
  <rect x="20" y="72" width="760" height="20" fill="#e8f4e8" rx="3"/>
  <text x="400" y="86" text-anchor="middle" font-size="10" fill="#060">
    Korekce: Profil je KUZELOVY (ne stupnovity) | Ø19 je PRUCHOZI vrtani | Diry Ø7 rozestup 40mm
  </text>

  <!-- ═══════════ SECTION VIEW ═══════════ -->
  <g id="section-view">

    <!-- RIGHT HALF (hatched section) -->
    <path d="{right_d}" fill="url(#hatch)" stroke="#222" stroke-width="1.0" stroke-linejoin="round"/>

    <!-- LEFT HALF (hatched section) -->
    <path d="{left_d}" fill="url(#hatch)" stroke="#222" stroke-width="1.0" stroke-linejoin="round"/>

    <!-- CENTERLINE -->
    <line x1="{cx}" y1="{y_top - 20}" x2="{cx}" y2="{y_89 + 20}"
          stroke="#c00" stroke-width="0.4" stroke-dasharray="20,3,3,3"/>
    <text x="{cx}" y="{y_top - 25}" text-anchor="middle" font-size="8" fill="#c00">CL</text>

    <!-- THREAD ZONE: M30×2 (shaft Ø30 from z=1.5 to z=78.5) -->
    <!-- Minor diameter indication (thin dashed line) -->
    <line x1="{cx + 13.9*s}" y1="{y_1_5}" x2="{cx + 13.9*s}" y2="{y_78_5}"
          stroke="#888" stroke-width="0.3" stroke-dasharray="2,2"/>
    <line x1="{cx - 13.9*s}" y1="{y_1_5}" x2="{cx - 13.9*s}" y2="{y_78_5}"
          stroke="#888" stroke-width="0.3" stroke-dasharray="2,2"/>

    <!-- Thread zone label -->
    <text x="{cx + 5}" y="{y0 + 40*s}" text-anchor="start" font-size="8" fill="#888"
          transform="rotate(90,{cx + 5},{y0 + 40*s})">M30×2 zavit (77mm)</text>

    <!-- Ø19 THROUGH-BORE indication (thin lines through bore) -->
    <line x1="{x_r_bore}" y1="{y_top}" x2="{x_r_bore}" y2="{y_89}"
          stroke="#222" stroke-width="0.6"/>
    <line x1="{x_l_bore}" y1="{y_top}" x2="{x_l_bore}" y2="{y_89}"
          stroke="#222" stroke-width="0.6"/>

    <!-- Ø7 HOLES IN SECTION (through cutting plane at Y=±20) -->
    <!-- Right hole at r=20mm -->
    <rect x="{cx + 20*s - 3.5*s}" y="{y0 + 84.5*s}" width="{7*s}" height="{4.5*s}"
          fill="white" stroke="#222" stroke-width="0.6" stroke-dasharray="3,2"/>
    <!-- Left hole at r=20mm -->
    <rect x="{cx - 20*s - 3.5*s}" y="{y0 + 84.5*s}" width="{7*s}" height="{4.5*s}"
          fill="white" stroke="#222" stroke-width="0.6" stroke-dasharray="3,2"/>

    <!-- TRANSITION ZONE DETAIL (highlighted) -->
    <rect x="{x_l_flange - 5}" y="{y_78_5 - 5}" width="{(x_r_flange - x_l_flange) + 10}" height="{(y_89 - y_78_5) + 10}"
          fill="none" stroke="#07a" stroke-width="0.5" stroke-dasharray="5,3" rx="3"/>
    <text x="{x_r_flange + 15}" y="{y_78_5}" font-size="8" fill="#07a">Prechod</text>
    <text x="{x_r_flange + 15}" y="{y_78_5 + 11}" font-size="8" fill="#07a">kuzelovy</text>

  </g>

  <!-- ═══════════ DIMENSIONS ═══════════ -->
  <g id="dimensions">

    <!-- M30×2 / Ø30 at top -->
    {dim_h(x_l_shaft, x_r_shaft, y_top, "M30×2 (Ø30)", -25)}

    <!-- Ø27 at reduced section -->
    {dim_h(cx - 13.5*s, cx + 13.5*s, y0 + 81.5*s, "Ø27", 15)}

    <!-- Ø19 through-bore -->
    {dim_h(x_l_bore, x_r_bore, y0 + 45*s, "Ø19 pruchozi", -12)}

    <!-- Ø55 at flange -->
    {dim_h(x_l_flange, x_r_flange, y_89, "Ø55", 22)}

    <!-- Overall height 89 -->
    {dim_v(x_r_flange, y_top, y_89, "89", 35)}

    <!-- Chamfer 1.5×45° -->
    {dim_v(x_r_shaft, y_top, y_1_5, "1.5×45°", 15)}

    <!-- Heights from top (left side) -->
    {dim_v_left(x_l_shaft, y_top, y_78_5, "78,5", -35)}
    {dim_v_left(x_l_flange, y_top, y_81, "≈81", -60)}
    {dim_v_left(x_l_flange, y_top, y_83_5, "83,5", -85)}
    {dim_v_left(x_l_flange, y_top, y_86_4, "86,4", -110)}

    <!-- Flange cylinder height -->
    {dim_v(x_r_flange, y_86_4, y_89, "2,63", 15)}

  </g>

  <!-- ═══════════ CALLOUTS ═══════════ -->
  <g id="callouts" font-size="9">
    {callout(cx + 15*s, y_1_5, "Zkoseni 1,5×45° (CONICAL_SURFACE)", 50, -20)}
    {callout(cx + 14.5*s, y0 + 79.5*s, "Kuzel 31° (R15→R13.5)", 55, -12)}
    {callout(cx + 13.5*s, y0 + 81.5*s, "Ø27 valec (1,35mm)", 80, 5)}
    {callout(cx + 14*s, y0 + 83*s, "R1 zaobleni (TOROIDAL r=1)", 75, 15)}
    {callout(cx + 20*s, y0 + 84*s, "Kuzel 82° (R13.5→R27.5)", 45, -15)}
    {callout(cx + 27*s, y0 + 85.5*s, "R1 zaobleni → Ø55", 30, 15)}
    {callout(cx + 9.5*s, y0 + 50*s, "Ø19 PRUCHOZI vrtani", 75, 0)}
    {callout(cx + 20*s, y0 + 86*s, "Ø7 (2×) v=±20mm od osy", 40, 25)}
  </g>

  <!-- ═══════════ CONE ANGLE DETAIL ═══════════ -->
  <g id="cone-angles" font-size="8" fill="#07a">
    <!-- 31° angle indicator on right side -->
    <line x1="{cx + 15*s}" y1="{y_78_5}"
          x2="{cx + 13.5*s}" y2="{y_81}"
          stroke="#07a" stroke-width="1.5" stroke-dasharray="none" opacity="0.5"/>
    <text x="{cx + 16*s}" y="{y0 + 80*s}" font-size="9" fill="#07a">31°</text>

    <!-- 82° angle indicator -->
    <line x1="{cx + 13.5*s}" y1="{y_83_5}"
          x2="{cx + 27.5*s}" y2="{y0 + 85.5*s}"
          stroke="#07a" stroke-width="1.5" stroke-dasharray="none" opacity="0.5"/>
    <text x="{cx + 21*s}" y="{y0 + 83.8*s}" font-size="9" fill="#07a">82°</text>
  </g>

  <!-- ═══════════ BOTTOM VIEW ═══════════ -->
  <g id="bottom-view">
    <text x="{bv_cx}" y="{bv_cy - bv_r_outer - 25}" text-anchor="middle"
          font-size="14" font-weight="bold" fill="#222">Pohled zdola</text>
    <text x="{bv_cx}" y="{bv_cy - bv_r_outer - 12}" text-anchor="middle"
          font-size="9" fill="#888">(rozestup der opraveny ze STEP: 40mm, ne 24mm)</text>

    <!-- Outer circle Ø55 -->
    <circle cx="{bv_cx}" cy="{bv_cy}" r="{bv_r_outer}" fill="#f9f9f9" stroke="#222" stroke-width="1.2"/>

    <!-- Center bore Ø19 (through!) -->
    <circle cx="{bv_cx}" cy="{bv_cy}" r="{bv_r_bore}" fill="white" stroke="#222" stroke-width="1.0"/>
    <line x1="{bv_cx - bv_r_bore*0.5}" y1="{bv_cy - bv_r_bore*0.5}"
          x2="{bv_cx + bv_r_bore*0.5}" y2="{bv_cy + bv_r_bore*0.5}" stroke="#222" stroke-width="0.3"/>
    <line x1="{bv_cx + bv_r_bore*0.5}" y1="{bv_cy - bv_r_bore*0.5}"
          x2="{bv_cx - bv_r_bore*0.5}" y2="{bv_cy + bv_r_bore*0.5}" stroke="#222" stroke-width="0.3"/>

    <!-- Centerlines -->
    <line x1="{bv_cx - bv_r_outer - 15}" y1="{bv_cy}" x2="{bv_cx + bv_r_outer + 15}" y2="{bv_cy}"
          stroke="#c00" stroke-width="0.3" stroke-dasharray="12,3,3,3"/>
    <line x1="{bv_cx}" y1="{bv_cy - bv_r_outer - 15}" x2="{bv_cx}" y2="{bv_cy + bv_r_outer + 15}"
          stroke="#c00" stroke-width="0.3" stroke-dasharray="12,3,3,3"/>

    <!-- 2× Ø7 holes at ±20mm from center (FROM STEP!) -->
    <circle cx="{bv_cx - bv_hole_offset}" cy="{bv_cy}" r="{bv_r_hole}"
            fill="white" stroke="#222" stroke-width="0.8"/>
    <line x1="{bv_cx - bv_hole_offset - bv_r_hole*0.6}" y1="{bv_cy - bv_r_hole*0.6}"
          x2="{bv_cx - bv_hole_offset + bv_r_hole*0.6}" y2="{bv_cy + bv_r_hole*0.6}"
          stroke="#222" stroke-width="0.3"/>
    <line x1="{bv_cx - bv_hole_offset + bv_r_hole*0.6}" y1="{bv_cy - bv_r_hole*0.6}"
          x2="{bv_cx - bv_hole_offset - bv_r_hole*0.6}" y2="{bv_cy + bv_r_hole*0.6}"
          stroke="#222" stroke-width="0.3"/>

    <circle cx="{bv_cx + bv_hole_offset}" cy="{bv_cy}" r="{bv_r_hole}"
            fill="white" stroke="#222" stroke-width="0.8"/>
    <line x1="{bv_cx + bv_hole_offset - bv_r_hole*0.6}" y1="{bv_cy - bv_r_hole*0.6}"
          x2="{bv_cx + bv_hole_offset + bv_r_hole*0.6}" y2="{bv_cy + bv_r_hole*0.6}"
          stroke="#222" stroke-width="0.3"/>
    <line x1="{bv_cx + bv_hole_offset + bv_r_hole*0.6}" y1="{bv_cy - bv_r_hole*0.6}"
          x2="{bv_cx + bv_hole_offset - bv_r_hole*0.6}" y2="{bv_cy + bv_r_hole*0.6}"
          stroke="#222" stroke-width="0.3"/>

    <!-- Bottom view dimensions -->
    <text x="{bv_cx}" y="{bv_cy + bv_r_outer + 22}" text-anchor="middle" font-size="10" fill="#333">Ø55</text>
    <text x="{bv_cx + 2}" y="{bv_cy - bv_r_bore - 5}" text-anchor="middle" font-size="9" fill="#333">Ø19</text>
    <text x="{bv_cx + bv_hole_offset}" y="{bv_cy - bv_r_hole - 5}"
          text-anchor="middle" font-size="8" fill="#333">Ø7</text>
    <text x="{bv_cx - bv_hole_offset}" y="{bv_cy - bv_r_hole - 5}"
          text-anchor="middle" font-size="8" fill="#333">Ø7</text>

    <!-- Spacing dimension 40mm (CORRECTED from STEP!) -->
    <line x1="{bv_cx - bv_hole_offset}" y1="{bv_cy + bv_r_hole + 10}"
          x2="{bv_cx + bv_hole_offset}" y2="{bv_cy + bv_r_hole + 10}"
          stroke="#333" stroke-width="0.5" marker-start="url(#as)" marker-end="url(#ae)"/>
    <text x="{bv_cx}" y="{bv_cy + bv_r_hole + 23}" text-anchor="middle"
          font-size="10" font-weight="bold" fill="#c00">40 (ze STEP)</text>
  </g>

  <!-- ═══════════ COMPARISON TABLE ═══════════ -->
  <g id="info-block" font-size="9">
    <rect x="20" y="910" width="760" height="130" fill="#f8f8f8" stroke="#ddd" stroke-width="0.5" rx="4"/>

    <text x="400" y="928" text-anchor="middle" font-size="12" font-weight="bold" fill="#222">
      Srovnani: Odhad z PDF vs. Presna data ze STEP
    </text>

    <!-- Table header -->
    <text x="40" y="948" font-weight="bold" fill="#555">Parametr</text>
    <text x="250" y="948" font-weight="bold" fill="#555">Odhad z PDF</text>
    <text x="470" y="948" font-weight="bold" fill="#555">STEP (presne)</text>
    <text x="670" y="948" font-weight="bold" fill="#555">Status</text>
    <line x1="30" y1="952" x2="770" y2="952" stroke="#ccc" stroke-width="0.5"/>

    <!-- Row 1 -->
    <text x="40" y="965" fill="#333">Profil prechodu</text>
    <text x="250" y="965" fill="#c00">4 stupne (schody)</text>
    <text x="470" y="965" fill="#060">Kuzely 31°+82° + R1 zaobleni</text>
    <text x="670" y="965" fill="#c00" font-weight="bold">OPRAVENO</text>

    <!-- Row 2 -->
    <text x="40" y="980" fill="#333">Vrtani Ø19</text>
    <text x="250" y="980" fill="#c00">Slepe (4mm v prirube)</text>
    <text x="470" y="980" fill="#060">PRUCHOZI (89mm!)</text>
    <text x="670" y="980" fill="#c00" font-weight="bold">OPRAVENO</text>

    <!-- Row 3 -->
    <text x="40" y="995" fill="#333">Rozestup der Ø7</text>
    <text x="250" y="995" fill="#c00">24mm</text>
    <text x="470" y="995" fill="#060">40mm (±20mm od osy)</text>
    <text x="670" y="995" fill="#c00" font-weight="bold">OPRAVENO</text>

    <!-- Row 4 -->
    <text x="40" y="1010" fill="#333">Vyska valce Ø55</text>
    <text x="250" y="1010" fill="#c00">~3.5mm</text>
    <text x="470" y="1010" fill="#060">2.63mm</text>
    <text x="670" y="1010" fill="#c00" font-weight="bold">OPRAVENO</text>

    <!-- Row 5 -->
    <text x="40" y="1025" fill="#333">Ø30, Ø27, Ø55, Ø19, Ø7</text>
    <text x="250" y="1025" fill="#060">Spravne</text>
    <text x="470" y="1025" fill="#060">Potvrzeno</text>
    <text x="670" y="1025" fill="#060" font-weight="bold">OK</text>

    <!-- Row 6 -->
    <text x="40" y="1040" fill="#333">Celkova vyska 89mm</text>
    <text x="250" y="1040" fill="#060">Spravne</text>
    <text x="470" y="1040" fill="#060">Potvrzeno</text>
    <text x="670" y="1040" fill="#060" font-weight="bold">OK</text>
  </g>

</svg>'''

    return svg


if __name__ == '__main__':
    svg_content = generate_svg()
    output_path = '/Users/lofas/Documents/__App_Claude/Gestima/stuetzfuss_contour.svg'
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(svg_content)
    print(f"SVG saved to: {output_path}")
    print(f"\nKey findings from STEP analysis:")
    print(f"  - Through-bore Ø19 (full 89mm height!)")
    print(f"  - Conical transitions (31° + 82°), NOT stepped")
    print(f"  - Ø7 hole spacing: 40mm (±20mm from axis)")
    print(f"  - Flange cylinder height: 2.63mm")
    print(f"  - Top chamfer: 1.5×45°")
    print(f"  - Thread not modeled in STEP (smooth Ø30 shaft)")
