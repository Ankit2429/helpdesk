# KLE Tech AI Campus Helpdesk — Desktop UI Style Guide

This document defines the official Design System, typography hierarchy, HSL color palettes, spacing grid, and touchscreen standards for the **KLE Tech / BVBCET AI Campus Helpdesk Desktop Application**.

---

## 🎨 Color Palettes

### 🌙 Dark Theme (Default Kiosk & Modern Desktop)
| Color Role | Hex Code | HSL / Usage |
| :--- | :--- | :--- |
| **Window Background** | `#0F172A` | Slate 900 — Main window background |
| **Panel / Card Background** | `#1E293B` | Slate 800 — Cards, sidebar, modal background |
| **Border / Divider** | `#334155` | Slate 700 — Crisp subtle borders |
| **Primary Accent** | `#3B82F6` | Royal Blue 500 — Action buttons, active indicators |
| **Primary Accent Hover/Active** | `#2563EB` | Royal Blue 600 — Pressed state |
| **Secondary Accent / Success** | `#10B981` | Emerald 500 — Healthy status, bot bubbles |
| **Warning Accent** | `#F59E0B` | Amber 500 — Warning status |
| **Error Accent** | `#EF4444` | Rose 500 — Offline / Error status, hallucination flags |
| **Primary Text** | `#F8FAFC` | Slate 50 — Primary readable text |
| **Muted Text** | `#94A3B8` | Slate 400 — Captions, timestamps, secondary labels |

### ☀️ Light Theme
| Color Role | Hex Code | HSL / Usage |
| :--- | :--- | :--- |
| **Window Background** | `#F8FAFC` | Slate 50 — Main window background |
| **Panel / Card Background** | `#FFFFFF` | Pure White — Cards, panels |
| **Border / Divider** | `#E2E8F0` | Slate 200 — Clean borders |
| **Primary Accent** | `#2563EB` | Royal Blue 600 — Action buttons |
| **Primary Text** | `#0F172A` | Slate 900 — Primary readable text |
| **Muted Text** | `#64748B` | Slate 500 — Secondary text |

---

## 📐 Typography Hierarchy

| Role | Font Family | Size | Weight | Usage |
| :--- | :--- | :--- | :--- | :--- |
| **Display Title** | Segoe UI / Inter | 22pt | Bold | Window headers, main app title |
| **Section Title** | Segoe UI / Inter | 16pt | Bold | Card titles, view headers |
| **Subsection / Card Header** | Segoe UI / Inter | 14pt | SemiBold | Tile titles, form labels |
| **Body Text** | Segoe UI / Inter | 12pt | Regular | Chat messages, log entries, inputs |
| **Caption / Status Text** | Segoe UI / Inter | 10pt | Regular | Timestamps, indicator tooltips |

---

## 👆 Touchscreen Input Standards

1. **Target Dimensions**:
   - **Minimum Touch Target**: `44x44 px`
   - **Default Button Size**: `48x48 px` or `160x48 px` (with text label)
   - **Sidebar Navigation Target**: `52x52 px`
2. **Padding & Spacing**:
   - Base grid unit: `8px`
   - Card Padding: `16px`
   - Container Gap: `12px`
3. **No Hover-Dependent Logic**:
   - Every interaction must trigger cleanly via tap/click.
   - Tooltips are expandable on tap rather than hover-only.

---

## 🧩 Component Library Reference

### 1. Navigation Sidebar
- Width: `200px` (or `64px` collapsed)
- Action: Tap to switch current view with zero window reload.

### 2. Status Indicator Badge
- Structure: Color Dot (`12x12px`) + Label + Expandable Detail Box
- States: `● Online (Green)`, `● Warning (Yellow)`, `● Offline (Red)`

### 3. Speech Bubbles
- **User Bubble**: Royal Blue background (`#2563EB`), White text, right-aligned.
- **Bot Bubble**: Dark Slate/Emerald background (`#1E293B`), Slate text, left-aligned with inline expandable citation drawer.

### 4. Citation Card Drawer
- Contains: Source Document, Heading, Match Confidence Score, Verbatim Snippet.

### 5. Camera Control & Gallery
- Framed video stream preview, Start/Stop toggle button, Snapshot capture button, bottom scrollable thumbnail gallery.
