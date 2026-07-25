# Fix Plan: "Failed to start scanning" 404 Bug

## Root Cause
In `backend/devices/urls.py`, `path('<str:pk>/', ...)` is listed BEFORE `path('scan/', ...)`.
Django matches `scan` as `pk="scan"` → routes to `DeviceDetailView` → no POST handler → 405 error.

## Steps
- [x] 1. Reorder `devices/urls.py` — move scan/refresh/register/diagnostics/before `<str:pk>/`
- [x] 2. Rewrite `DeviceScanView` in `devices/views.py` — production-ready with agent connection
- [x] 3. Update `Devices.jsx` — better error messages (405 vs 404)
- [x] 4. Update `vite.config.js` — add dev proxy
- [x] 5. Verify with `python manage.py check`
- [x] 6. Verify with `python manage.py show_urls`
- [x] 7. Test end-to-end

