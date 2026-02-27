# Frontend Rules (Codex)

Platí pro práci v `frontend/`.

## Povinné principy

- Vue 3 + `<script setup lang="ts">`
- `<style scoped>`
- Žádné `any`
- API volání přes `frontend/src/api/` moduly, ne přímý axios v komponentách
- Žádné hardcoded hex barvy v modulech (použít design tokeny)
- Interaktivní prvky mají `data-testid`

## State a data flow

- API -> store -> component -> template
- Komponenta nemění store přímo, jen přes actions
- Error handling přes UI store/toast pattern

Doporučené ověření:

```bash
npm run lint -C frontend
npm run build -C frontend
```

## Definice hotovo

Frontend změna je hotová jen pokud:
- build + lint projdou
- wiring je kompletní (komponenta je importovaná a použitá)
- `quality-gate.sh fe` projde
