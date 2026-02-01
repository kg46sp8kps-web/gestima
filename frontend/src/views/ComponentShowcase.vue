<template>
  <div class="showcase">
    <!-- HERO -->
    <section class="showcase-hero">
      <div class="hero-content">
        <h1 class="hero-title">GESTIMA Design System</h1>
        <p class="hero-subtitle">Refined & Subtle — Red Accent Edition</p>
        <div class="hero-meta">
          <span class="meta-item">shadcn/ui + radix-vue</span>
          <span class="meta-separator">•</span>
          <span class="meta-item">Tailwind CSS</span>
          <span class="meta-separator">•</span>
          <span class="meta-item">v1.12.0</span>
        </div>
      </div>
    </section>

    <!-- COLORS -->
    <section class="showcase-section">
      <h2 class="section-title">Color Palette</h2>
      <div class="color-grid">
        <div class="color-card">
          <div class="color-swatch" style="background: #991b1b"></div>
          <div class="color-info">
            <span class="color-name">Primary Red</span>
            <code class="color-value">#991b1b</code>
            <span class="color-use">Buttons, States</span>
          </div>
        </div>
        <div class="color-card">
          <div class="color-swatch" style="background: #E84545"></div>
          <div class="color-info">
            <span class="color-name">Logo Red</span>
            <code class="color-value">#E84545</code>
            <span class="color-use">Hover, Accents</span>
          </div>
        </div>
        <div class="color-card">
          <div class="color-swatch" style="background: #0a0a0a"></div>
          <div class="color-info">
            <span class="color-name">Background</span>
            <code class="color-value">#0a0a0a</code>
            <span class="color-use">Base</span>
          </div>
        </div>
        <div class="color-card">
          <div class="color-swatch" style="background: #141414"></div>
          <div class="color-info">
            <span class="color-name">Surface</span>
            <code class="color-value">#141414</code>
            <span class="color-use">Cards, Panels</span>
          </div>
        </div>
        <div class="color-card">
          <div class="color-swatch" style="background: #f43f5e"></div>
          <div class="color-info">
            <span class="color-name">Danger</span>
            <code class="color-value">#f43f5e</code>
            <span class="color-use">Errors, Delete</span>
          </div>
        </div>
        <div class="color-card">
          <div class="color-swatch" style="background: #059669"></div>
          <div class="color-info">
            <span class="color-name">Success</span>
            <code class="color-value">#059669</code>
            <span class="color-use">Confirmations</span>
          </div>
        </div>
      </div>
    </section>

    <!-- TYPOGRAPHY -->
    <section class="showcase-section">
      <h2 class="section-title">Typography</h2>
      <div class="type-stack">
        <div class="type-sample" style="font-size: var(--text-6xl); font-weight: var(--font-bold)">
          Display XL — Industrial Precision
        </div>
        <div class="type-sample" style="font-size: var(--text-4xl); font-weight: var(--font-semibold)">
          Heading Large — Professional Tools
        </div>
        <div class="type-sample" style="font-size: var(--text-2xl); font-weight: var(--font-medium)">
          Heading Medium — Business Applications
        </div>
        <div class="type-sample" style="font-size: var(--text-base)">
          Body Text — Optimized for 27" displays at 2560x1440. Compact, dense, efficient.
        </div>
        <div class="type-sample" style="font-size: var(--text-sm); color: var(--text-secondary)">
          Secondary Text — Labels, hints, metadata. Clear yet subtle.
        </div>
        <div class="type-sample" style="font-family: var(--font-mono); font-size: var(--text-sm)">
          Monospace — 12345.67 € | Precision data, numbers, codes
        </div>
      </div>
    </section>

    <!-- BUTTONS -->
    <section class="showcase-section">
      <h2 class="section-title">Buttons</h2>

      <!-- Variants -->
      <div class="component-group">
        <h3 class="group-title">Variants</h3>
        <div class="button-row">
          <Button variant="primary">Primary Button</Button>
          <Button variant="secondary">Secondary Button</Button>
          <Button variant="danger">Danger Button</Button>
          <Button variant="ghost">Ghost Button</Button>
        </div>
      </div>

      <!-- Sizes -->
      <div class="component-group">
        <h3 class="group-title">Sizes</h3>
        <div class="button-row">
          <Button size="sm">Small</Button>
          <Button size="md">Medium</Button>
          <Button size="lg">Large</Button>
        </div>
      </div>

      <!-- States -->
      <div class="component-group">
        <h3 class="group-title">States</h3>
        <div class="button-row">
          <Button>Normal</Button>
          <Button disabled>Disabled</Button>
          <Button :loading="true">Loading</Button>
        </div>
      </div>

      <!-- Business Style Showcase -->
      <div class="component-group">
        <h3 class="group-title">Business Actions</h3>
        <div class="button-row">
          <Button variant="primary">Create Quote</Button>
          <Button variant="secondary">Export PDF</Button>
          <Button variant="secondary">Generate Report</Button>
          <Button variant="danger">Delete Part</Button>
        </div>
      </div>
    </section>

    <!-- INPUTS -->
    <section class="showcase-section">
      <h2 class="section-title">Input Fields</h2>

      <div class="component-group">
        <h3 class="group-title">Text Inputs</h3>
        <div class="input-grid">
          <Input
            v-model="demoInputText"
            label="Text Input"
            placeholder="Enter text..."
          />
          <Input
            v-model="demoInputNumber"
            type="number"
            label="Number Input"
            placeholder="0.00"
            :mono="true"
          />
          <Input
            v-model="demoInputEmail"
            type="email"
            label="Email Input"
            placeholder="user@example.com"
            :required="true"
          />
        </div>
      </div>

      <div class="component-group">
        <h3 class="group-title">States</h3>
        <div class="input-grid">
          <Input
            v-model="demoInputNormal"
            label="Normal State"
            placeholder="Normal input"
          />
          <Input
            v-model="demoInputError"
            label="Error State"
            placeholder="Invalid input"
            error="This field is required"
          />
          <Input
            v-model="demoInputDisabled"
            label="Disabled State"
            placeholder="Cannot edit"
            :disabled="true"
          />
          <Input
            v-model="demoInputReadonly"
            label="Readonly State"
            :readonly="true"
          />
        </div>
      </div>

      <div class="component-group">
        <h3 class="group-title">With Hints</h3>
        <div class="input-grid">
          <Input
            v-model="demoInputHint"
            label="Part Number"
            placeholder="e.g., 10001234"
            hint="8-digit part number"
          />
        </div>
      </div>
    </section>

    <!-- FORMS -->
    <section class="showcase-section">
      <h2 class="section-title">Form Example</h2>
      <div class="form-demo">
        <form class="business-form" @submit.prevent>
          <div class="form-row">
            <Input
              v-model="formData.partNumber"
              label="Part Number"
              placeholder="10001234"
              :required="true"
              :mono="true"
            />
            <Input
              v-model="formData.partName"
              label="Part Name"
              placeholder="Component description"
              :required="true"
            />
          </div>

          <div class="form-row">
            <Input
              v-model="formData.quantity"
              type="number"
              label="Quantity"
              placeholder="0"
              :mono="true"
            />
            <Input
              v-model="formData.unitPrice"
              type="number"
              label="Unit Price (€)"
              placeholder="0.00"
              :mono="true"
            />
          </div>

          <div class="form-actions">
            <Button variant="secondary">Cancel</Button>
            <Button variant="primary" type="submit">Save Part</Button>
          </div>
        </form>
      </div>
    </section>

    <!-- BORDERS & SPACING -->
    <section class="showcase-section">
      <h2 class="section-title">Refined Style — Subtle Structure</h2>

      <div class="component-group">
        <h3 class="group-title">Border System</h3>
        <div class="border-demo-grid">
          <div class="border-demo-card">
            <div class="border-label">Subtle 1px Borders</div>
            <div class="border-sample border-subtle-demo">
              Refined, subtle borders — clean separation without heaviness
            </div>
          </div>
          <div class="border-demo-card">
            <div class="border-label">4px Radius</div>
            <div class="border-sample border-radius-demo">
              Classic corner radius — not too rounded
            </div>
          </div>
        </div>
      </div>

      <div class="component-group">
        <h3 class="group-title">Cards & Surfaces</h3>
        <div class="card-demo-grid">
          <div class="demo-card">
            <h4 class="card-title">Surface Card</h4>
            <p class="card-content">Background: <code>var(--bg-surface)</code></p>
            <p class="card-content">Border: <code>2px solid var(--border-default)</code></p>
          </div>
          <div class="demo-card demo-card-raised">
            <h4 class="card-title">Raised Card</h4>
            <p class="card-content">Background: <code>var(--bg-raised)</code></p>
            <p class="card-content">Shadow: <code>var(--shadow-md)</code></p>
          </div>
        </div>
      </div>
    </section>

    <!-- DATA DISPLAY -->
    <section class="showcase-section">
      <h2 class="section-title">Data Display</h2>

      <div class="component-group">
        <h3 class="group-title">Badges</h3>
        <div class="badge-row">
          <span class="badge">Part Badge</span>
          <span class="time-badge setup">Setup</span>
          <span class="time-badge operation">Operation</span>
          <span class="time-badge coop">Cooperation</span>
          <span class="frozen-badge">Frozen</span>
        </div>
      </div>

      <div class="component-group">
        <h3 class="group-title">Table Preview</h3>
        <table class="demo-table">
          <thead>
            <tr>
              <th>Part Number</th>
              <th>Description</th>
              <th>Quantity</th>
              <th>Unit Price</th>
              <th>Total</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td class="mono-cell">10001234</td>
              <td>Precision Component A</td>
              <td class="mono-cell">150</td>
              <td class="mono-cell">12.50 €</td>
              <td class="mono-cell">1,875.00 €</td>
            </tr>
            <tr class="row-selected">
              <td class="mono-cell">10001235</td>
              <td>Precision Component B</td>
              <td class="mono-cell">200</td>
              <td class="mono-cell">8.75 €</td>
              <td class="mono-cell">1,750.00 €</td>
            </tr>
            <tr>
              <td class="mono-cell">10001236</td>
              <td>Precision Component C</td>
              <td class="mono-cell">75</td>
              <td class="mono-cell">24.00 €</td>
              <td class="mono-cell">1,800.00 €</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import Button from '@/components/ui/Button.vue';
import Input from '@/components/ui/Input.vue';

// Demo data
const demoInputText = ref('Sample text');
const demoInputNumber = ref(123.45);
const demoInputEmail = ref('user@gestima.com');
const demoInputNormal = ref('');
const demoInputError = ref('');
const demoInputDisabled = ref('Cannot edit this');
const demoInputReadonly = ref('Read-only value');
const demoInputHint = ref('');

const formData = ref({
  partNumber: '10001234',
  partName: 'Precision Component',
  quantity: 100,
  unitPrice: 12.50
});
</script>

<style scoped>
/* === SHOWCASE LAYOUT === */
.showcase {
  max-width: 1400px;
  margin: 0 auto;
  padding: var(--space-8) var(--space-6);
  background: var(--bg-base);
  min-height: 100vh;
}

/* === HERO === */
.showcase-hero {
  margin-bottom: var(--space-12);
  padding: var(--space-10) 0;
  text-align: center;
  border-bottom: 1px solid var(--border-default);
}

.hero-title {
  font-size: var(--text-6xl);
  font-weight: var(--font-bold);
  color: var(--text-primary);
  margin-bottom: var(--space-3);
}

.hero-subtitle {
  font-size: var(--text-2xl);
  color: var(--text-secondary);
  margin-bottom: var(--space-4);
}

.hero-meta {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-3);
  font-size: var(--text-sm);
  color: var(--text-tertiary);
  font-family: var(--font-mono);
}

.meta-separator {
  color: var(--color-primary);
}

/* === SECTIONS === */
.showcase-section {
  margin-bottom: var(--space-12);
}

.section-title {
  font-size: var(--text-4xl);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
  margin-bottom: var(--space-6);
  padding-bottom: var(--space-3);
  border-bottom: 1px solid var(--border-default);
}

.component-group {
  margin-bottom: var(--space-8);
}

.group-title {
  font-size: var(--text-xl);
  font-weight: var(--font-medium);
  color: var(--text-body);
  margin-bottom: var(--space-4);
}

/* === COLORS === */
.color-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: var(--space-4);
}

.color-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius);
  overflow: hidden;
  transition: var(--transition-fast);
}

.color-card:hover {
  border-color: var(--border-strong);
  transform: translateY(-2px);
}

.color-swatch {
  height: 120px;
  width: 100%;
}

.color-info {
  padding: var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.color-name {
  font-weight: var(--font-semibold);
  color: var(--text-primary);
  font-size: var(--text-sm);
}

.color-value {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--text-secondary);
  background: var(--bg-base);
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-sm);
  width: fit-content;
}

.color-use {
  font-size: var(--text-xs);
  color: var(--text-tertiary);
}

/* === TYPOGRAPHY === */
.type-stack {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
}

.type-sample {
  padding: var(--space-4);
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius);
}

/* === BUTTONS === */
.button-row {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-3);
}

/* === INPUTS === */
.input-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: var(--space-4);
}

/* === FORMS === */
.business-form {
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius);
  padding: var(--space-6);
  max-width: 800px;
}

.form-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: var(--space-4);
  margin-bottom: var(--space-4);
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-3);
  margin-top: var(--space-6);
  padding-top: var(--space-6);
  border-top: 1px solid var(--border-default);
}

/* === BORDERS === */
.border-demo-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: var(--space-4);
}

.border-demo-card {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.border-label {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--text-secondary);
}

.border-sample {
  padding: var(--space-4);
  background: var(--bg-surface);
  border-radius: var(--radius);
}

.border-subtle-demo {
  border: 1px solid var(--color-primary);
}

.border-radius-demo {
  border: 1px solid var(--border-default);
}

/* === CARDS === */
.card-demo-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: var(--space-4);
}

.demo-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius);
  padding: var(--space-6);
}

.demo-card-raised {
  background: var(--bg-raised);
  box-shadow: var(--shadow-md);
}

.card-title {
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
  margin-bottom: var(--space-3);
}

.card-content {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  margin-bottom: var(--space-2);
}

.card-content code {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  background: var(--bg-base);
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-sm);
  color: var(--color-primary);
}

/* === BADGES === */
.badge-row {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-3);
  align-items: center;
}

/* === TABLE === */
.demo-table {
  width: 100%;
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius);
  border-collapse: separate;
  border-spacing: 0;
  overflow: hidden;
}

.demo-table thead {
  background: var(--bg-raised);
}

.demo-table th {
  padding: var(--space-3) var(--space-4);
  text-align: left;
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
  border-bottom: 1px solid var(--border-strong);
}

.demo-table td {
  padding: var(--space-3) var(--space-4);
  font-size: var(--text-sm);
  color: var(--text-body);
  border-bottom: 1px solid var(--border-subtle);
}

.demo-table tbody tr:last-child td {
  border-bottom: none;
}

.demo-table tbody tr:hover {
  background: var(--state-hover);
}

.demo-table .row-selected {
  background: var(--state-selected);
}

.mono-cell {
  font-family: var(--font-mono);
  text-align: right;
}
</style>
