import { BrowserRouter, Routes, Route, NavLink } from "react-router-dom";
import { LayoutDashboard, Settings } from "lucide-react";
import Dashboard from "./pages/Dashboard";
import SettingsPage from "./pages/Settings";

function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen flex flex-col">
        <header className="border-b border-border bg-card/50 backdrop-blur">
          <div className="container mx-auto px-4 h-14 flex items-center justify-between">
            <h1 className="font-bold text-xl tracking-tight text-primary">
              TREND WATCHING
            </h1>
            <nav className="flex gap-6">
              <NavLink
                to="/"
                className={({ isActive }) =>
                  `flex items-center gap-2 text-sm font-medium transition-colors ${
                    isActive ? "text-primary" : "text-muted-foreground hover:text-foreground"
                  }`
                }
              >
                <LayoutDashboard className="h-4 w-4" />
                Панель
              </NavLink>
              <NavLink
                to="/settings"
                className={({ isActive }) =>
                  `flex items-center gap-2 text-sm font-medium transition-colors ${
                    isActive ? "text-primary" : "text-muted-foreground hover:text-foreground"
                  }`
                }
              >
                <Settings className="h-4 w-4" />
                Настройки
              </NavLink>
            </nav>
          </div>
        </header>
        <main className="flex-1 container mx-auto px-4 py-8">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;
