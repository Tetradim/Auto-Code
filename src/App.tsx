import { createRootRoute, createRoute, createRouter, RouterProvider, Outlet, useNavigate, useLocation } from '@tanstack/react-router'
import { AppShell, AppShellSidebar, AppShellMain, Sidebar, SidebarHeader, SidebarContent, SidebarGroup, SidebarItem, MobileSidebarTrigger, Toaster, useBlinkUI } from '@blinkdotnew/ui'
import { LayoutDashboard, Activity, History, Settings as SettingsIcon, Shield, Zap, AlertTriangle, TrendingUp, BarChart3, Database } from 'lucide-react'
import { useBlinkAuth } from '@blinkdotnew/react'
import { blink } from './lib/blink'
import { DashboardPage } from './pages/Dashboard'
import { TickersPage } from './pages/Tickers'
import { LogsPage } from './pages/Logs'
import { SettingsPage } from './pages/Settings'

// Root route with AppShell layout
const rootRoute = createRootRoute({
  component: () => {
    const { isAuthenticated, isLoading } = useBlinkAuth()
    const navigate = useNavigate()
    const location = useLocation()
    const { darkMode } = useBlinkUI()

    if (isLoading) {
      return (
        <div className="flex h-screen items-center justify-center bg-background">
          <div className="h-8 w-8 animate-spin rounded-full border-b-2 border-primary" />
        </div>
      )
    }

    if (!isAuthenticated) {
      return (
        <div className="flex h-screen flex-col items-center justify-center bg-background p-4 text-center">
          <Shield className="mb-6 h-16 w-16 text-primary animate-pulse" />
          <h1 className="mb-2 text-3xl font-bold tracking-tight text-foreground">Sentinel Edge</h1>
          <p className="mb-8 max-w-md text-muted-foreground">
            Advanced trading assistant for Opening Range Breakout detection and dynamic risk management.
          </p>
          <button 
            onClick={() => blink.auth.login(window.location.href)}
            className="flex items-center gap-2 rounded-lg bg-primary px-8 py-3 font-semibold text-primary-foreground transition-all hover:opacity-90 active:scale-95"
          >
            Authenticate with Sentinel
          </button>
        </div>
      )
    }

    return (
      <AppShell>
        <AppShellSidebar>
          <Sidebar>
            <SidebarHeader className="flex items-center gap-2 px-4 py-6">
              <Zap className="h-6 w-6 text-primary fill-primary/20" />
              <span className="text-xl font-bold tracking-tight text-foreground">SENTINEL <span className="text-primary">EDGE</span></span>
            </SidebarHeader>
            <SidebarContent>
              <SidebarGroup>
                <SidebarItem 
                  icon={<LayoutDashboard className="h-4 w-4" />} 
                  label="Command Center" 
                  href="/" 
                  active={location.pathname === '/'} 
                />
                <SidebarItem 
                  icon={<BarChart3 className="h-4 w-4" />} 
                  label="Ticker Analytics" 
                  href="/tickers" 
                  active={location.pathname === '/tickers'} 
                />
                <SidebarItem 
                  icon={<Activity className="h-4 w-4" />} 
                  label="Live Alerts" 
                  href="/logs" 
                  active={location.pathname === '/logs'} 
                />
                <SidebarItem 
                  icon={<History className="h-4 w-4" />} 
                  label="Trade Audit" 
                  href="/audit" 
                />
              </SidebarGroup>
              <SidebarGroup className="mt-auto">
                <SidebarItem 
                  icon={<Database className="h-4 w-4" />} 
                  label="DB Health" 
                  href="/health" 
                />
                <SidebarItem 
                  icon={<SettingsIcon className="h-4 w-4" />} 
                  label="Configuration" 
                  href="/settings" 
                  active={location.pathname === '/settings'} 
                />
              </SidebarGroup>
            </SidebarContent>
          </Sidebar>
        </AppShellSidebar>
        <AppShellMain className="bg-background/50 backdrop-blur-sm">
          <header className="flex h-16 items-center justify-between border-b border-border px-6 md:h-14">
            <div className="flex items-center gap-3">
              <MobileSidebarTrigger className="md:hidden" />
              <h2 className="text-sm font-medium text-muted-foreground">
                {location.pathname === '/' ? 'Real-time Dashboard' : 
                 location.pathname === '/tickers' ? 'Ticker Monitoring' : 
                 location.pathname === '/logs' ? 'Breakout Alerts' : 
                 location.pathname === '/settings' ? 'Bot Configuration' : 'Page'}
              </h2>
            </div>
            <div className="flex items-center gap-4">
              <div className="hidden items-center gap-2 rounded-full border border-border bg-card px-3 py-1 text-[10px] font-bold uppercase tracking-widest md:flex">
                <span className="h-2 w-2 animate-pulse rounded-full bg-green-500" />
                MARKET OPEN
              </div>
              <button 
                onClick={() => blink.auth.logout()}
                className="text-xs font-medium text-muted-foreground hover:text-foreground"
              >
                Sign Out
              </button>
            </div>
          </header>
          <div className="p-6">
            <Outlet />
          </div>
        </AppShellMain>
      </AppShell>
    )
  }
})

// Define routes
const indexRoute = createRoute({ getParentRoute: () => rootRoute, path: '/', component: DashboardPage })
const tickersRoute = createRoute({ getParentRoute: () => rootRoute, path: '/tickers', component: TickersPage })
const logsRoute = createRoute({ getParentRoute: () => rootRoute, path: '/logs', component: LogsPage })
const settingsRoute = createRoute({ getParentRoute: () => rootRoute, path: '/settings', component: SettingsPage })

const routeTree = rootRoute.addChildren([indexRoute, tickersRoute, logsRoute, settingsRoute])
const router = createRouter({ routeTree })

declare module '@tanstack/react-router' {
  interface Register { router: typeof router }
}

export default function App() {
  return <RouterProvider router={router} />
}
