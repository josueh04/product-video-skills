# Adapter: Vue (unproven)

Status: unproven. Written from the proven Angular method and general Vue knowledge. Follow it,
tell the user it is unproven, and add a "Learned on <product>" section at the end when done.

## Where values hide

| Layer | Files | Gives |
|---|---|---|
| Routes | `router/index.(ts|js)`, Nuxt `pages/` | which page renders the screen |
| Single-file components | `*.vue`: `<template>`, `<script setup>`, `<style scoped>` | DOM, `v-if` / `v-show` / `v-for` branches, `ref()` defaults, scoped styles |
| Stores | Pinia or Vuex modules | default state, loading and empty states |
| Global styles | `assets/**/*.scss`, `main.(ts|js)` imports | tokens and base text |
| Component library | Vuetify (`createVuetify({ theme })`), PrimeVue (presets like PrimeNG), Element Plus, Quasar, Naive UI, and their defaults in node_modules | paddings, radii, colors, overlay behaviour |
| Copy | `vue-i18n` (`$t('key')`, `locales/<lang>.json`) or literals | every string |
| Icons | `@iconify/vue`, `unplugin-icons`, `lucide-vue-next`, library icon sets, inline SVG | names map to SVG packages |
| Motion | `<Transition>` / `<TransitionGroup>` with `name`, whose CSS classes (`*-enter-active`) hold durations and easings | transitions |

## Traps to expect

- **Scoped styles.** `<style scoped>` adds data attributes; `:deep()` rules reach children, but not
  teleported content (`<Teleport to="body">` dialogs and menus), which keeps library defaults.
- **`v-show` versus `v-if`.** `v-show` keeps the element in the DOM, hidden; layout around it may
  still reserve space in some cases. Check which one the story's state uses.
- **PrimeVue** shares PrimeNG's preset system; much of `angular-primeng.md` applies (presets,
  dark mode selector, layers, overlay placement).
- **Vuetify density and variants** change paddings and heights; read the props on each component.

## Learned on products

(Add a dated section per product: what matched, what surprised you, what to check first.)
