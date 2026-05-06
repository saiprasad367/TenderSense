import { NavLink, useLocation } from "react-router-dom";
import {
  LayoutDashboard, Upload, Activity, ListChecks, FileSearch, FileBarChart2, ShieldCheck,
} from "lucide-react";
import {
  Sidebar, SidebarContent, SidebarGroup, SidebarGroupContent, SidebarGroupLabel,
  SidebarMenu, SidebarMenuButton, SidebarMenuItem, SidebarHeader, SidebarFooter, useSidebar,
} from "@/components/ui/sidebar";

import { AuthProvider, useAuth } from "@/contexts/AuthContext";

const adminItems = [
  { title: "Dashboard", url: "/", icon: LayoutDashboard, roles: ['admin', 'senior_officer', 'evaluation_officer'] },
  { title: "Upload Tender", url: "/upload", icon: Upload, roles: ['admin', 'senior_officer', 'evaluation_officer'] },
  { title: "Evaluation Runs", url: "/evaluation", icon: Activity, roles: ['admin', 'senior_officer', 'evaluation_officer'] },
  { title: "Review Queue", url: "/review", icon: ListChecks, roles: ['admin', 'senior_officer', 'evaluation_officer'] },
  { title: "Audit Trail", url: "/audit", icon: FileSearch, roles: ['admin'] },
  { title: "Reports", url: "/reports", icon: FileBarChart2, roles: ['admin', 'senior_officer'] },
];

const bidderItems = [
  { title: "My Applications", url: "/bidder", icon: ListChecks, roles: ['viewer'] },
];

export function AppSidebar() {
  const { state } = useSidebar();
  const { role } = useAuth();
  const collapsed = state === "collapsed";
  const { pathname } = useLocation();
  const isActive = (path: string) => path === "/" ? pathname === "/" : pathname.startsWith(path);

  const items = role === 'viewer' ? bidderItems : adminItems.filter(item => item.roles.includes(role || ''));

  return (
    <Sidebar collapsible="icon" className="border-r border-sidebar-border">
      <SidebarHeader className="border-b border-sidebar-border">
        <div className="flex items-center gap-2 px-2 py-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-sm border border-border bg-background">
            <ShieldCheck className="h-4 w-4" />
          </div>
          {!collapsed && (
            <div className="leading-tight">
              <div className="text-sm font-semibold tracking-tight">TenderSense</div>
              <div className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground">AI · Gov Eval</div>
            </div>
          )}
        </div>
      </SidebarHeader>
      <SidebarContent className="bg-sidebar">
        <SidebarGroup>
          {!collapsed && <SidebarGroupLabel className="ts-section-title px-3 pt-3">Workspace</SidebarGroupLabel>}
          <SidebarGroupContent>
            <SidebarMenu>
              {items.map((item) => (
                <SidebarMenuItem key={item.title}>
                  <SidebarMenuButton asChild isActive={isActive(item.url)} tooltip={item.title}>
                    <NavLink to={item.url} className="flex items-center gap-3">
                      <item.icon className="h-4 w-4 shrink-0" />
                      {!collapsed && <span className="text-sm">{item.title}</span>}
                    </NavLink>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
      <SidebarFooter className="border-t border-sidebar-border">
        {!collapsed ? (
          <div className="px-3 py-3 text-[11px] text-muted-foreground leading-relaxed">
            <div className="font-medium text-foreground">System Status</div>
            <div className="mt-1 flex items-center gap-2">
              <span className="h-1.5 w-1.5 rounded-full bg-status-success animate-pulse-soft" />
              All agents online
            </div>
          </div>
        ) : (
          <div className="flex justify-center py-3"><span className="h-1.5 w-1.5 rounded-full bg-status-success animate-pulse-soft" /></div>
        )}
      </SidebarFooter>
    </Sidebar>
  );
}
