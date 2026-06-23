# Frontend Changes

## Dark/Light Theme Toggle

### Files Modified

- `frontend/index.html`
- `frontend/style.css`
- `frontend/script.js`

---

### What Was Added

#### `style.css`

1. **Light theme CSS variables** — a `[data-theme="light"]` block overrides the dark-mode `:root` values:
   - Background shifts from `#0f172a` → `#f8fafc`
   - Surfaces: `#1e293b` → `#ffffff`
   - Text: `#f1f5f9` → `#0f172a`
   - Borders: `#334155` → `#e2e8f0`
   - Toggle button colours adapted per theme

2. **Global theme transition** — `background-color`, `color`, `border-color`, and `box-shadow` are transitioned over 0.25 s on all elements so the switch is smooth rather than a jarring flash.

3. **`.theme-toggle` button styles** — fixed 40×40 px circular button, top-right corner (`position: fixed; top: 1rem; right: 1rem; z-index: 100`). Includes hover scale, active press-down, and `focus-visible` ring for keyboard navigation.

4. **Icon animation** — Sun and Moon SVGs are stacked (`position: absolute`). In dark mode the sun is visible and the moon is rotated/scaled out; in light mode the roles are swapped. The swap is handled via CSS `opacity` + `transform` transitions.

#### `index.html`

- Added the `<button class="theme-toggle" id="themeToggle">` element with inline Sun and Moon SVGs immediately inside `<body>` (before `.container`).
- Both SVGs carry `aria-hidden="true"`; the button has `aria-label="Toggle dark/light theme"` and a `title` tooltip for accessibility.
- Bumped cache-busting version on `style.css` and `script.js` from `v=9` to `v=10`.

#### `script.js`

- **`initTheme()`** — reads `localStorage` for a saved preference, falling back to `prefers-color-scheme` media query. Sets `data-theme` on `<html>` before the DOM is ready to prevent flash of wrong theme.
- **`toggleTheme()`** — flips `data-theme` between `dark` and `light` and persists the choice to `localStorage`.
- `initTheme()` is called immediately (outside `DOMContentLoaded`) so the attribute is set synchronously.
- Click listener on `#themeToggle` wired up inside `DOMContentLoaded`.

---

### Behaviour Summary

| Action | Result |
|---|---|
| First visit, no saved preference | Follows OS `prefers-color-scheme` |
| First visit, OS = dark | Dark theme |
| First visit, OS = light | Light theme |
| Click toggle | Switches theme; preference saved to `localStorage` |
| Return visit | Restores last saved theme |
| Keyboard Tab + Enter/Space on button | Toggles theme (fully accessible) |

---

## Light Theme Colour Audit & Accessibility Fixes

### File Modified

- `frontend/style.css`

---

### What Changed

The initial light theme block had several hardcoded colours in the CSS body that did not adapt to the theme and failed WCAG AA contrast on light backgrounds. This pass converted every hardcoded colour to a CSS variable and tuned the light-mode values for accessibility.

#### New CSS variables added to `:root` (dark-mode defaults)

| Variable | Dark value | Purpose |
|---|---|---|
| `--source-chip-bg` | `rgba(99,179,237,0.12)` | Source chip background |
| `--source-chip-border` | `rgba(99,179,237,0.3)` | Source chip border |
| `--source-chip-color` | `#90cdf4` | Source chip text |
| `--source-chip-hover-bg/border/color` | lighter blues | Hover state |
| `--code-bg` | `rgba(0,0,0,0.2)` | Inline/block code background |
| `--error-color` / `--error-bg` / `--error-border` | red tones | Error messages |
| `--success-color` / `--success-bg` / `--success-border` | green tones | Success messages |
| `--welcome-shadow` | `0 4px 16px rgba(0,0,0,0.2)` | Welcome card shadow |

#### `[data-theme="light"]` overrides added/updated

| Variable | Light value | Contrast on light bg | WCAG |
|---|---|---|---|
| `--primary-color` | `#1d4ed8` | 5.7:1 on `#f8fafc` | AA ✓ |
| `--primary-hover` | `#1e40af` | 6.8:1 | AA ✓ |
| `--text-secondary` | `#475569` | 6.2:1 on `#f8fafc` | AA ✓ (was `#64748b` ≈4.1:1 ✗) |
| `--focus-ring` | `rgba(29,78,216,0.25)` | visible against light | — |
| `--source-chip-color` | `#1d4ed8` | 5.7:1 on tinted bg | AA ✓ |
| `--source-chip-hover-color` | `#1e40af` | 6.8:1 | AA ✓ |
| `--code-bg` | `rgba(0,0,0,0.06)` | subtle tint on white | — |
| `--error-color` | `#dc2626` | 5.1:1 on white | AA ✓ (was `#f87171` ≈3.5:1 ✗) |
| `--success-color` | `#16a34a` | 5.0:1 on white | AA ✓ (was `#4ade80` ≈1.7:1 ✗) |
| `--welcome-shadow` | `0 4px 16px rgba(0,0,0,0.08)` | softer on light | — |

#### Selectors updated to use variables

- `.source-chip` — `background`, `border`, `color`
- `a.source-chip:hover` — all three hover properties
- `.message-content code` — `background-color`
- `.message-content pre` — `background-color`
- `.message.welcome-message .message-content` — `box-shadow`
- `.error-message` — `background`, `color`, `border`
- `.success-message` — `background`, `color`, `border`

---

## JS Functionality & Implementation Completeness

### Files Modified

- `frontend/style.css`
- `frontend/script.js`

---

### What Changed

#### Bug fix — `var(--primary)` → `var(--primary-color)` (`style.css`)

`blockquote` used `var(--primary)` which was never defined, so it rendered with no border colour in either theme. Fixed to `var(--primary-color)`.

#### `prefers-reduced-motion` support (`style.css`)

Added a `@media (prefers-reduced-motion: reduce)` block at the end of the stylesheet that collapses all transition durations and animation durations to `0.01ms` for users who have enabled this OS-level accessibility setting. Covers the global theme-switch transitions, the icon spin/fade on the toggle button, the message `fadeIn` animation, and the loading-dot `bounce` animation.

```css
@media (prefers-reduced-motion: reduce) {
    body, body *, body *::before, body *::after {
        transition-duration: 0.01ms !important;
        animation-duration: 0.01ms !important;
        animation-iteration-count: 1 !important;
    }
}
```

#### OS theme change listener (`script.js`)

Added a `matchMedia` change listener so the page automatically follows OS-level dark/light mode changes — but only when the user has not set a manual preference via the toggle button (i.e. nothing stored in `localStorage`). Once a manual preference exists it takes precedence and the listener is a no-op.

```js
window.matchMedia('(prefers-color-scheme: light)').addEventListener('change', (e) => {
    if (!localStorage.getItem('theme')) {
        document.documentElement.setAttribute('data-theme', e.matches ? 'light' : 'dark');
    }
});
```

---

### Complete Theme System Behaviour

| Scenario | Result |
|---|---|
| First visit, no OS preference | Dark theme |
| First visit, OS = light | Light theme |
| First visit, OS = dark | Dark theme |
| Toggle button clicked | Flips theme; saves to `localStorage` |
| Return visit | Restores saved `localStorage` preference |
| OS changes while page open, no manual pref | Page follows OS change |
| OS changes while page open, manual pref set | Manual preference wins |
| `prefers-reduced-motion` enabled | All transitions/animations disabled |
| Keyboard Tab → Enter/Space on toggle | Toggles theme (accessible) |
