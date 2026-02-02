# Module Defaults - Test Plan

**Test Date:** 2026-02-02
**Status:** Ready for Testing

---

## 🧪 Quick Test Steps

### Test 1: Modal Appearance
**Goal:** Verify modal shows when window size changes

1. Start frontend: `npm run dev`
2. Navigate to Windows view
3. Open any module window (e.g., Part Detail)
4. Note original size (check window object in Vue DevTools)
5. Resize window by >10px (drag bottom-right corner)
6. Click X to close
7. **Expected:** SaveModuleDefaultsModal appears
8. **Verify:** Modal shows correct module name and size

### Test 2: Confirm Save
**Goal:** Verify defaults are saved to mock store

1. Follow Test 1 steps
2. In modal, click "Uložit" button
3. **Expected:** Modal closes, window closes
4. Open browser console
5. **Verify:** Log message: "Saved defaults for [module-type]"
6. Reopen same module window
7. **Expected:** Window opens with saved size

### Test 3: Cancel Save
**Goal:** Verify cancel doesn't save defaults

1. Open window, resize it
2. Click X to close
3. In modal, click "Zrušit" button
4. **Expected:** Modal closes, window closes, no save message in console
5. Reopen same module window
6. **Expected:** Window opens with original size (not resized size)

### Test 4: No Changes
**Goal:** Verify modal doesn't show for small/no changes

1. Open window
2. Don't resize OR resize by <10px
3. Click X to close
4. **Expected:** No modal, window closes immediately

### Test 5: Keyboard Navigation
**Goal:** Verify accessibility

1. Open window, resize it
2. Click X to close → Modal opens
3. Press Tab key
4. **Expected:** Focus moves through buttons (Zrušit → Uložit → X close)
5. Press Enter on "Uložit"
6. **Expected:** Defaults saved, modal closes
7. Repeat, press Escape
8. **Expected:** Modal closes without saving

### Test 6: Multiple Module Types
**Goal:** Verify per-module defaults

1. Open "Part Detail" window, resize to 1000×700, close & save
2. Open "Operations" window, resize to 600×500, close & save
3. Open "Part Detail" again
4. **Expected:** Opens at 1000×700
5. Open "Operations" again
6. **Expected:** Opens at 600×500

---

## 🔍 Vue DevTools Inspection

### Check Mock Store Data

1. Open Vue DevTools → Pinia tab
2. Find `windows` store
3. After saving defaults, inspect console:
   ```javascript
   // Mock data is stored in module-defaults.ts closure
   // You can verify by checking browser console logs
   ```

### Check Window State

1. Vue DevTools → Components tab
2. Select `FloatingWindow` component
3. Inspect state:
   - `originalSize` - Should match initial size
   - `showSaveDefaultsModal` - Should be true when modal open
   - `props.window` - Check current width/height

---

## ✅ Expected Results Summary

| Test | Action | Expected Result |
|------|--------|----------------|
| 1 | Resize >10px, close | Modal appears |
| 2 | Confirm save | Console log, next open uses saved size |
| 3 | Cancel save | No log, next open uses original size |
| 4 | No resize, close | No modal (immediate close) |
| 5 | Keyboard nav | Tab, Enter, Esc work |
| 6 | Multiple modules | Each module has own defaults |

---

## 🐛 Troubleshooting

### Modal doesn't appear
- Check console for errors
- Verify window was resized >10px
- Check `hasWindowChanged()` in FloatingWindow.vue

### Defaults don't persist
- Remember: Using MOCK data (not persisted to DB yet)
- Defaults reset on page reload
- Check console for "Saved defaults for..." message

### TypeScript errors
- Run `npm run type-check`
- Existing errors in other files are unrelated
- New files should have no TS errors

---

## 📊 Coverage Checklist

### UI States
- [x] Modal shows changes summary
- [x] Confirm button enabled when changes exist
- [x] Confirm button disabled when no changes
- [x] Modal responsive (400px on desktop)
- [x] Icons use ICON_SIZE constants
- [x] Design system tokens applied

### Functionality
- [x] Window size tracking
- [x] Change detection (10px tolerance)
- [x] Modal show/hide logic
- [x] Save to mock API
- [x] Load from mock API on window open
- [x] Per-module defaults (not global)

### Accessibility
- [x] Keyboard navigation
- [x] Focus management
- [x] ARIA labels (via Modal.vue)
- [x] Screen reader text

### Error Handling
- [x] API errors logged to console
- [x] Fallback to default size (800×600)
- [x] No crash if save fails

---

## 🎯 Known Limitations (Mock Phase)

1. **No persistence** - Defaults reset on page reload
2. **No split positions** - Only size tracked (TODO: SplitPane integration)
3. **No column widths** - TODO: Table integration
4. **No per-user** - Global defaults only (not per-user)

These will be addressed when backend API is implemented.

---

## 🚀 Next Steps After Testing

1. ✅ Verify all tests pass
2. ✅ Check UI/UX is intuitive
3. ✅ Confirm design system compliance
4. → Create backend API endpoints
5. → Replace mock with real API calls
6. → Add database persistence
7. → Add SplitPane tracking
8. → Add column width tracking
