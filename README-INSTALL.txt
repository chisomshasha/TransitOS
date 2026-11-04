TransitOS UI Redesign Pack
==========================

HOW TO INSTALL
--------------
1. Unzip this archive.
2. From your repo root, copy the contents of `frontend/` OVER your existing `frontend/` folder
   (merge / replace files — do not delete unrelated files you still need).

   Example (from repo root):
     cp -R TransitOS-UI-Redesign-Pack/frontend/* frontend/

3. Ensure expo-linear-gradient is installed:
     cd frontend
     npx expo install expo-linear-gradient

4. Commit and push:
     git add frontend
     git commit -m "ui: apply TransitOS navy/yellow redesign pack"
     git push

5. Rebuild:
     npx eas build --platform android --profile preview --clear-cache

FILES IN THIS PACK
------------------
- lib/theme.ts                          (NEW design tokens)
- components/ui/BottomTabs.tsx
- components/ui/Button.tsx              (yellow primary)
- components/admin/*                    (navy chips)
- app/(auth)/login.tsx
- app/(app)/_layout.tsx
- app/(app)/index.tsx                   (Dashboard)
- app/(app)/trips/index.tsx + [id].tsx
- app/(app)/vehicles/index.tsx + [id].tsx
- app/(app)/profile.tsx
- app/(app)/cash-ups.tsx
- app/(app)/reports.tsx
- app/(app)/fuel.tsx, maintenance.tsx, expenses.tsx
- app/(app)/branches, drivers, conductors, users, routes
- package.json                          (includes expo-linear-gradient)

Brand: Navy #0B3D91 · Yellow #FFCC00 · Background #F8F7F4
