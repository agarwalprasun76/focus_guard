import { Route, Routes } from "react-router-dom";

import { RequireAuth, RequireGuest } from "./auth/guards";
import { AppLayout } from "./ui/AppLayout";
import { Dashboard } from "./views/Dashboard";
import { Devices } from "./views/Devices";
import { Exceptions } from "./views/Exceptions";
import { LoginPage } from "./views/LoginPage";
import { NotFoundPage } from "./views/NotFoundPage";
import { SavedLinks } from "./views/SavedLinks";
import { Settings } from "./views/Settings";

export function AppRouter() {
  return (
    <Routes>
      <Route
        path="/login"
        element={
          <RequireGuest>
            <LoginPage />
          </RequireGuest>
        }
      />
      <Route
        path="/"
        element={
          <RequireAuth>
            <AppLayout />
          </RequireAuth>
        }
      >
        <Route index element={<Dashboard />} />
        <Route path="dashboard" element={<Dashboard />} />
        <Route path="saved-links" element={<SavedLinks />} />
        <Route path="exceptions" element={<Exceptions />} />
        <Route path="overrides" element={<Exceptions />} />
        <Route path="devices" element={<Devices />} />
        <Route path="settings" element={<Settings />} />
      </Route>
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
