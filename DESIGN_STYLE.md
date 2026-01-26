# Design Style Guide

A minimal, hacker-aesthetic design system with sharp corners, clean typography, and a dark theme with golden accents.

## Design Principles

- **Sharp corners** - No border-radius anywhere, all elements have 0 radius
- **X borders** - Vertical borders on left/right contain content in a focused column
- **Minimal** - No shadows, no gradients (except for image blending), no decorative elements
- **Consistent spacing** - Use spacing variables, never arbitrary values
- **High contrast** - Dark backgrounds with light text for readability
- **Monospace accents** - Code font for UI elements like nav, dates, tags

## Color Palette

### Backgrounds
| Variable | Value | Usage |
|----------|-------|-------|
| `--bg-color` | `#0d0d0d` | Main background |
| `--header-bg` | `#0a0a0a` | Header background |
| `--card-bg` | `#1a1a1a` | Card/elevated surfaces |
| `--code-bg` | `#111111` | Code blocks |

### Text
| Variable | Value | Usage |
|----------|-------|-------|
| `--text-color` | `#e8e8e8` | Primary text |
| `--text-muted` | `#888888` | Secondary/muted text |
| `--code-text` | `#e0e0e0` | Code block text |

### Accents (Golden)
| Variable | Value | Usage |
|----------|-------|-------|
| `--primary-color` | `#D4AF37` | Primary accent, highlights, hover states |
| `--secondary-color` | `#c9a227` | Secondary accent |
| `--accent-color` | `#e8c547` | Bright accent for emphasis |

### Borders
| Variable | Value | Usage |
|----------|-------|-------|
| `--border-color` | `#333333` | All borders |

### Subtle Backgrounds
```css
rgba(255,255,255,0.02)  /* Hover states, section headers */
```

## Typography

### Font Stacks
| Variable | Value | Usage |
|----------|-------|-------|
| `--font-primary` | System fonts (Apple, Segoe, Roboto) | Body text |
| `--font-code` | SFMono, Menlo, Monaco, Consolas | Nav, dates, tags, code |

### Font Sizes
- Body: `17px`
- Nav links: `0.9em`
- Section titles: `0.85em` (uppercase, letter-spacing: 0.1em)
- Hero greeting: `0.9em`
- Hero name: `2em`
- Hero bio: `1.1em`
- Card title: `1.1em`
- Card date: `0.85em`
- Card excerpt: `0.95em`
- Tags: `0.75em`

## Spacing Scale

| Variable | Value | Usage |
|----------|-------|-------|
| `--spacing-xs` | `8px` | Tight gaps (tag gaps, small margins) |
| `--spacing-sm` | `16px` | Small spacing (padding, gaps) |
| `--spacing-md` | `24px` | Medium spacing (section padding, card padding) |
| `--spacing-lg` | `48px` | Large spacing (section gaps) |
| `--spacing-xl` | `64px` | Extra large (hero padding) |

## Layout

### Container Widths
| Variable | Value | Usage |
|----------|-------|-------|
| `--container-width` | `900px` | Main content |
| `--article-width` | `1000px` | Blog posts |

### X Border Pattern
The main content area uses left/right borders to create a focused column:
```css
.main-container {
    border-left: 1px solid var(--border-color);
    border-right: 1px solid var(--border-color);
}
```

## Components

### Header
- Sticky position
- X borders + bottom border
- Inner wrapper for padding alignment
- Logo: monospace, regular weight, white text
- Nav: monospace, muted color, golden on hover
- Social icons: 16px, muted, no background circles

### Hero Section
- Full width (extends to X borders)
- Background image with `mix-blend-mode: lighten`
- Left-side gradient fade for text readability
- Content has z-index above overlay
- Greeting + name have minimal gap (4px)

### Section Header
- Flex row with title left, link right
- Subtle background: `rgba(255,255,255,0.02)`
- Border bottom
- Title has `>` prefix (terminal style)

### Blog Cards
- No background, transparent
- Border bottom only
- Padding on card-link (not list container)
- Hover: subtle background `rgba(255,255,255,0.02)`
- Title changes to golden on hover
- Date in YYYY-MM-DD format (hacker style)

### Tags
- Transparent background
- Border: 1px solid border-color
- Monospace font
- No border-radius

## Hover States

All hover transitions use `0.2s` timing:
```css
transition: color 0.2s;
transition: background-color 0.2s;
```

Hover patterns:
- Text: muted -> primary-color
- Backgrounds: transparent -> rgba(255,255,255,0.02)
- No transform effects (no scale, no translateY)

## Code Syntax Highlighting

```css
.hljs-keyword { color: #e8c547; }  /* accent */
.hljs-string { color: #98c379; }   /* green */
.hljs-comment { color: #7a7a7a; }  /* muted */
.hljs-number { color: #d19a66; }   /* orange */
.hljs-function .hljs-title { color: #61afef; }  /* blue */
```

## Mobile Responsiveness

At `600px` breakpoint:
- Remove X borders on main container
- Reduce hero name to `1.6em`
- Stack nav below logo
- Reduce spacing values
