# UI/UX Design System Guide

## Aesthetic Concept
The UI design is inspired by modern **Cyber-Intelligence Control Rooms** and **Sleek Dark Interfaces**. It balances visual richness with functional clarity to convey high-tech capability, professionalism, and reliability. 

---

## Design Tokens

### Color Palette (Tailwind Custom Config & CSS Variables)
We employ a dark gradient theme with vibrant neon accents:
- **Base Background:** Deep gradients `from-gray-900 via-gray-800 to-black`
- **Surface Panels:** Semi-transparent cards `bg-gray-800/60` or `bg-gray-950/50`
- **Primary Accent (Cyber Blue):** `#3B82F6` (representing diagnostic systems and connectivity)
- **Secondary Accent (AI Purple):** `#8B5CF6` (representing AI systems, neural processing)
- **Success Tone (System Active):** `#10B981` (safe state, clean files)
- **Warning Tone (Caution):** `#F59E0B` (corrupted sectors, unclassified files)
- **Danger Tone (Alert):** `#EF4444` (encrypted partitions, threat indicators)

### Typography
- **Primary Font:** [Google Font Outfit](https://fonts.google.com/specimen/Outfit) or **Inter** (clean, geometric, highly legible at small sizes)
- **Console Font:** **SF Mono** or **JetBrains Mono** (used in Z-Mode Autonomous Kernel logs)

---

## Component Architecture

### 1. Glassmorphism Panels
Cards and dialog boxes feature transparent overlays with backdrop filters to feel premium and dimensional:
```css
.glass-panel {
  background: rgba(31, 41, 55, 0.6);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.05);
}
```

### 2. Micro-Animations
Interaction elements utilize transitions to create a tactile and responsive feel:
- **Buttons:** Subtle scale down on active states, glowing color transitions on hover.
- **Pulse Indicators:** Glowing rings around active status indicators (e.g., active AI cores).
- **Z-Mode Feed:** Smooth scrolling terminal messages that cascade dynamically.

### 3. Responsive Drawer Menu
- **Desktop:** Sidebar stays visible, providing quick navigation.
- **Mobile/Tablet:** Collapses into a responsive sidebar menu triggered via header hamburger icon, using a full-screen semi-transparent overlay to cover workspace components.
