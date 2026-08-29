/** @type {import('tailwindcss').Config} */
export default {
  // IMPORTANT: Tailwind only generates CSS for class names it finds in these
  // files. If a .jsx file isn't listed here, its className="flex gap-2 ..."
  // utilities silently produce NO css in the final build (this is the most
  // common reason a Tailwind app "looks unstyled" after building).
  content: [
    "./index.html",
    "./App.jsx",
    "./KrushiMitraChatUI.jsx",
    "./KrushiMitraAdminDashboard.jsx",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
};