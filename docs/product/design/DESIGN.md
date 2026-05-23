---
name: Precision Audio Utility
colors:
  surface: '#111317'
  surface-dim: '#111317'
  surface-bright: '#37393e'
  surface-container-lowest: '#0c0e12'
  surface-container-low: '#1a1c20'
  surface-container: '#1e2024'
  surface-container-high: '#282a2e'
  surface-container-highest: '#333539'
  on-surface: '#e2e2e8'
  on-surface-variant: '#c1c6d6'
  inverse-surface: '#e2e2e8'
  inverse-on-surface: '#2f3035'
  outline: '#8b91a0'
  outline-variant: '#414754'
  surface-tint: '#acc7ff'
  primary: '#acc7ff'
  on-primary: '#002f67'
  primary-container: '#468fff'
  on-primary-container: '#00285a'
  inverse-primary: '#005cbd'
  secondary: '#4edea3'
  on-secondary: '#003824'
  secondary-container: '#00a572'
  on-secondary-container: '#00311f'
  tertiary: '#ffb95f'
  on-tertiary: '#472a00'
  tertiary-container: '#ca8100'
  on-tertiary-container: '#3e2400'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#d7e2ff'
  primary-fixed-dim: '#acc7ff'
  on-primary-fixed: '#001a40'
  on-primary-fixed-variant: '#004591'
  secondary-fixed: '#6ffbbe'
  secondary-fixed-dim: '#4edea3'
  on-secondary-fixed: '#002113'
  on-secondary-fixed-variant: '#005236'
  tertiary-fixed: '#ffddb8'
  tertiary-fixed-dim: '#ffb95f'
  on-tertiary-fixed: '#2a1700'
  on-tertiary-fixed-variant: '#653e00'
  background: '#111317'
  on-background: '#e2e2e8'
  surface-variant: '#333539'
typography:
  display-sm:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
    letterSpacing: -0.01em
  headline-sm:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '600'
    lineHeight: 24px
    letterSpacing: -0.01em
  title-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '600'
    lineHeight: 20px
    letterSpacing: 0em
  body-md:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 18px
    letterSpacing: 0em
  body-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 16px
    letterSpacing: 0em
  label-md:
    fontFamily: Inter
    fontSize: 11px
    fontWeight: '500'
    lineHeight: 14px
    letterSpacing: 0.02em
  tabular-nums:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 18px
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  unit: 4px
  space-xs: 4px
  space-sm: 8px
  space-md: 12px
  space-lg: 16px
  space-xl: 24px
  container-padding: 12px
  gutter: 8px
---

## Brand & Style

The design system is engineered for high-performance music management and professional DJ workflows. It prioritizes information density and visual clarity over decorative elements, mirroring the functional aesthetic of digital audio workstations (DAWs) and modern developer environments.

The brand personality is **precise, dependable, and utilitarian**. It aims to evoke a sense of professional mastery, providing users with a "cockpit" experience where every pixel serves a functional purpose. The visual style is a blend of **Minimalism** and **Modern Corporate**, utilizing a low-chroma dark palette to reduce eye strain during long sessions in low-light environments. 

Hierarchy is established through subtle tonal shifts and crisp borders rather than heavy shadows or vibrant fills, ensuring that the focus remains entirely on the metadata and audio assets.

## Colors

This design system utilizes a sophisticated dark-mode palette optimized for high-density utility. The foundation is built on **Deep Charcoal and Slate** neutrals to provide a stable, low-distraction background.

*   **Primary (Electric Blue):** Reserved for active states, manual mappings, and primary action triggers.
*   **Success (Emerald Green):** Indicates matched tracks, verified metadata, or successful file operations.
*   **Warning (Amber):** Signals ambiguous matches or items requiring user review.
*   **Danger (Rose Red):** Highlights missing files, corrupted data, or failed syncs.
*   **Neutral (Slate):** Used for the structural framework. Multiple tiers of grey (`surface-low` to `surface-high`) define the UI depth without relying on shadows.

## Typography

The typography system relies on **Inter** for its exceptional legibility at small sizes and robust support for tabular figures. The scale is intentionally compact to facilitate high data density.

*   **Tabular Data:** Use the `tabular-nums` role for all BPM, Duration, and Bitrate columns to ensure vertical alignment across rows.
*   **Case Usage:** Labels for metadata categories (e.g., GENRE, KEY, COMMENTS) should use `label-md` with uppercase styling to differentiate them from actual track data.
*   **Weight:** Use Semibold (600) sparingly for headers and primary track titles to maintain a clean, unweighted aesthetic across the grid.

## Layout & Spacing

This design system employs a **4px base unit** to support the required density for professional music management. The layout is structured as a **Contextual Panel System**:

1.  **Sidebar (Left):** Navigation and Collection management (Fixed width, 240px).
2.  **Main Library (Center):** Fluid data table that expands to fill available space.
3.  **Inspector (Right):** Contextual metadata editing for selected tracks (Collapsible, 300px).
4.  **Mini-Player (Bottom):** Persistent transport controls and waveform preview (Fixed height, 64px).

Spacing between related items (like table rows) should be minimal (`space-xs`), while separation between major UI sections uses `space-md` gutters and subtle borders.

## Elevation & Depth

In this design system, depth is conveyed through **Tonal Layering** and **Subtle Outlines** rather than traditional shadows. This ensures the interface remains crisp on high-resolution displays.

*   **Surface Hierarchy:** The background (`surface-low`) is the furthest back. Interactive areas like the track list use `surface-medium`. Popovers or modals use `surface-high`.
*   **Borders:** Use 1px solid borders for all containers. Border color should be `white` with `0.08` opacity for subtle separation. For active or focused elements, the border color shifts to the Primary Electric Blue.
*   **Shadows:** When necessary for floating menus, use a single, sharp 4px blur with 40% opacity of the background color—avoiding soft, atmospheric shadows.

## Shapes

The shape language is **geometric and precise**. A "Soft" roundedness (`0.25rem`) is applied to buttons, input fields, and status badges to prevent the UI from feeling overly aggressive while maintaining a professional, technical look.

*   **Standard Radius:** 4px for most UI components.
*   **Table Rows:** 0px (Square) to ensure a seamless, grid-like appearance when stacked.
*   **Search Bars:** 4px (Soft) to distinguish them from structural panels.

## Components

### Data Tables
The core component. Features include:
*   **Zebra Stripping:** Alternate row colors using `surface-medium` and `surface-low`.
*   **Hover State:** Rows highlight with a 1px Primary border or a slightly lighter background fill.
*   **Inline Editing:** Fields transition to a `surface-high` background with a Primary border when clicked.

### Buttons & Inputs
*   **Primary Button:** Solid Electric Blue with white text. High contrast, minimal padding.
*   **Ghost Button:** 1px subtle border, no fill, primary-colored text. Used for secondary actions.
*   **Input Fields:** Deep background (`background`), subtle border, 12px horizontal padding.

### Status Badges
Small, pill-shaped indicators.
*   **Matched:** Emerald background (20% opacity) with Emerald text.
*   **Missing:** Rose background (20% opacity) with Rose text.

### Mini-Player
A persistent footer containing:
*   A simplified, high-contrast waveform visualization.
*   Compact transport controls (Play, Cue, Sync).
*   Current track metadata using `body-sm` and `label-md`.

### Metadata Inspector
A vertical stack of input fields and tags. Uses `space-sm` for vertical rhythm to pack maximum information into the collapsible side panel.