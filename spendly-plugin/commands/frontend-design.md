# Spendly Frontend Design Skill

Use this skill whenever you are building or modifying any HTML template, CSS, or UI component in the Spendly expense tracker. Read it before writing a single line of markup or styles.

---

## Project identity

- **App name:** Spendly — a personal finance tracker built in Flask + Jinja2.
- **Brand tone:** Clean, editorial, financially serious. Not playful, not brutalist.
- **Currency:** Indian Rupees (₹). Always use the ₹ symbol, never "INR" or "Rs".

---

## File conventions

| What                  | Where                          |
|-----------------------|--------------------------------|
| Global styles         | `static/css/style.css`         |
| Page-scoped styles    | `static/css/<page>.css`        |
| JavaScript            | `static/js/main.js`            |
| Templates             | `templates/<page>.html`        |
| Base layout           | `templates/base.html`          |

**Always extend `base.html`.** Every page template starts with:

```jinja2
{% extends "base.html" %}

{% block title %}Page Title — Spendly{% endblock %}

{% block head %}
{# page-specific <link> tags only #}
{% endblock %}

{% block content %}
{# page body here #}
{% endblock %}

{% block scripts %}
{# page-specific <script> tags only #}
{% endblock %}
```

If a page needs its own styles, create `static/css/<page>.css` and load it in `{% block head %}`. Do **not** add page-scoped rules into `style.css`.

---

## Design tokens

All tokens are CSS custom properties on `:root` in `style.css`. **Never hardcode a color, font, or radius.** Use the variable.

### Colors

```css
/* Ink (text) */
--ink:        #0f0f0f   /* body text */
--ink-soft:   #2d2d2d   /* secondary text */
--ink-muted:  #6b6b6b   /* labels, captions */
--ink-faint:  #a0a0a0   /* placeholders, timestamps */

/* Paper (backgrounds) */
--paper:       #f7f6f3   /* page background */
--paper-warm:  #f0ede6   /* sections, stripes */
--paper-card:  #ffffff   /* card surfaces */

/* Accent — forest green (primary action, focus rings) */
--accent:       #1a472a
--accent-light: #e8f0eb

/* Accent 2 — amber (secondary highlights, charts) */
--accent-2:       #c17f24
--accent-2-light: #fdf3e3

/* Danger — destructive actions */
--danger:       #c0392b
--danger-light: #fdecea

/* Borders */
--border:      #e4e1da   /* default stroke */
--border-soft: #eeebe4   /* lighter dividers */
```

### Typography

```css
--font-display: 'DM Serif Display', Georgia, serif   /* headings, stat values */
--font-body:    'DM Sans', system-ui, sans-serif      /* everything else */
```

Rules:
- Headings (`h1`–`h3`) and large numeric values → `font-family: var(--font-display)`.
- All body copy, labels, buttons, inputs → `font-family: var(--font-body)`.
- Never mix font stacks within a single component.

### Radii

```css
--radius-sm: 6px    /* buttons, inputs, small chips */
--radius-md: 12px   /* cards, panels */
--radius-lg: 20px   /* hero card, modals */
```

### Layout widths

```css
--max-width:  1200px   /* page content container */
--auth-width: 440px    /* login / register forms */
```

---

## Component patterns

### Cards

```html
<div class="some-section">   <!-- or <section> -->
  <!-- card content -->
</div>
```

```css
.some-section {
    background: var(--paper-card);
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    padding: 1.75rem;
}
```

Use `box-shadow: 0 8px 40px rgba(0,0,0,0.06)` only on the landing hero card. Everywhere else, border alone is sufficient.

### Buttons

| Class          | Use                                 |
|----------------|-------------------------------------|
| `.btn-primary` | Primary actions (links styled as buttons) |
| `.btn-ghost`   | Secondary/cancel (links styled as buttons) |
| `.btn-submit`  | Full-width form submit `<button>`   |
| `.btn-delete`  | Inline destructive `<button>`       |
| `.nav-cta`     | Navbar CTA only                     |

- Primary hover → `var(--accent)`.
- Never invent a new button variant; adapt an existing one.

### Forms

```html
<div class="form-group">
    <label for="field-id">Label text</label>
    <input id="field-id" class="form-input" type="text" name="field" placeholder="…">
</div>
```

- All inputs use `.form-input`.
- Focus ring: `border-color: var(--accent)` (already in `style.css`).
- Error state: wrap the message in `<div class="auth-error">…</div>`.

### Stat tiles

```html
<div class="stat-tile">
    <span class="stat-label">Label</span>
    <span class="stat-value">₹1,234</span>
</div>
```

Numeric stat values always use `var(--font-display)`.

### Category badges

```html
<span class="badge badge-food">Food</span>
```

Available modifiers: `badge-food`, `badge-transport`, `badge-bills`, `badge-health`, `badge-entertainment`, `badge-shopping`, `badge-other`.

For a new category, add a matching `.badge-<name>` rule in `profile.css` using existing color pairs (`--accent`/`--accent-light`, `--accent-2`/`--accent-2-light`, etc.).

### Section headers

```html
<div class="section-header">
    <h2 class="section-title">Section Name</h2>
    <!-- optional right-side action -->
</div>
```

---

## Layout shells

### Standard page

```html
<div class="page-name-page">   <!-- scoped wrapper -->
    <!-- sections as direct children with gap via flex/grid -->
</div>
```

```css
.page-name-page {
    max-width: var(--max-width);
    margin: 0 auto;
    padding: 2.5rem 2rem 4rem;
    display: flex;
    flex-direction: column;
    gap: 2.5rem;
}
```

### Auth pages (login / register)

```html
<section class="auth-section">
    <div class="auth-container">
        <div class="auth-header">
            <h1 class="auth-title">…</h1>
            <p class="auth-subtitle">…</p>
        </div>
        <div class="auth-card">
            <!-- form -->
        </div>
        <p class="auth-switch">…</p>
    </div>
</section>
```

---

## Responsive breakpoints

| Breakpoint | Rule                                                           |
|------------|----------------------------------------------------------------|
| `≤ 900px`  | Stack hero to single column; hide hero visual; stack feature cards |
| `≤ 700px`  | Stack stat tiles; hide secondary table columns                 |
| `≤ 600px`  | Hide non-CTA nav links; reduce hero padding                    |

Always add responsive rules at the **bottom** of the relevant CSS file under a comment block.

---

## Do / Don't

**Do:**
- Use CSS variables for every color, font, radius, and width.
- Keep page-specific CSS in its own file loaded via `{% block head %}`.
- Use `DM Serif Display` for any number or heading that needs visual weight.
- Keep buttons text short (≤ 3 words).
- Test both the logged-in and logged-out navbar states.

**Don't:**
- Don't hardcode hex values or pixel font sizes.
- Don't add `box-shadow` to ordinary cards (only the hero mock card has it).
- Don't create new color variables — extend with existing ones.
- Don't write inline `style=""` attributes except for truly dynamic values (e.g., bar widths driven by template data).
- Don't use `!important` outside of `.nav-cta` (which already uses it intentionally for specificity).
- Don't add JavaScript for effects that CSS transitions already handle.
