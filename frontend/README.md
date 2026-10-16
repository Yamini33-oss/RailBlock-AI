# KAVACH BIE - Frontend (Stage 1)

React + Vite + TypeScript + Tailwind CSS + Lucide React + React Router.

## What is in Stage 1

- Collapsible left sidebar with all nine pages and working navigation
- Top status bar with an IST clock and a live backend health check
- Operations Dashboard: metric panels, 24-hour track timeline, module status, recent events
- Eight other pages are placeholders that later stages will fill in
- All sample statistics, timeline blocks and events are labelled DEMO DATA
- Backend shows NOT CONNECTED until the FastAPI backend (Stage 2) is running

## Run it on Windows with VS Code

1. Install Node.js 20 or newer (LTS) from https://nodejs.org if `node --version` fails in PowerShell.
2. Right-click `KAVACH-BIE-frontend.zip` and choose **Extract All...**. Extract into the folder where you want your project.
3. In VS Code, choose **File > Open Folder...** and open the extracted `KAVACH-BIE` folder.
4. Open a terminal with `` Ctrl+` `` (PowerShell).
5. Move into the frontend and install dependencies (run once):

   ```powershell
   cd frontend
   npm install
   ```

6. Start the app:

   ```powershell
   npm run dev
   ```

   Open http://localhost:5173 in your browser. Stop the server with `Ctrl+C`.

7. Verify the production build (from the `frontend` folder):

   ```powershell
   npm run build
   ```

   It should finish with `built in ...` and no red errors.

## Backend URL

By default the app checks `http://localhost:8000/api/health`. To change it, copy `.env.example` to `.env` and edit `VITE_API_BASE_URL`.

## Folder map

- `src/layouts/` sidebar and top bar
- `src/pages/` one file per page (Dashboard now, placeholders for the rest)
- `src/components/` reusable panels, badges, timeline
- `src/data/demoData.ts` all demo data, kept out of components
- `src/services/` backend calls
- `src/types/` shared TypeScript types
