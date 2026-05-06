import { Search, Bell, ChevronDown, LogOut, User as UserIcon } from "lucide-react";
import { SidebarTrigger } from "@/components/ui/sidebar";
import { useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

const titleMap: Record<string, string> = {
  "/": "Dashboard",
  "/upload": "Upload Tender",
  "/evaluation": "Live Evaluation",
  "/review": "Review Queue",
  "/audit": "Audit Trail",
  "/reports": "Reports",
};

export function AppHeader() {
  const { pathname } = useLocation();
  const { user, role, signOut } = useAuth();
  const navigate = useNavigate();
  
  const title = Object.entries(titleMap).find(([k]) => k === "/" ? pathname === "/" : pathname.startsWith(k))?.[1] || (pathname.startsWith('/bidder') ? "Bidder Portal" : "TenderSense");

  const handleSignOut = async () => {
    await signOut();
    navigate('/login');
  };

  const getInitials = (email: string) => {
    return email.substring(0, 2).toUpperCase();
  };

  return (
    <header className="sticky top-0 z-30 flex h-14 items-center gap-3 border-b border-border bg-background px-3 md:px-6">
      <SidebarTrigger className="md:mr-1" />
      <div className="hidden md:flex items-center gap-2 text-sm">
        <span className="text-muted-foreground">TenderSense</span>
        <span className="text-muted-foreground">/</span>
        <span className="font-medium">{title}</span>
      </div>
      <div className="ml-auto flex items-center gap-2 md:gap-3">
        <div className="relative hidden sm:block">
          <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
          <input
            placeholder="Search tenders, bidders, audits…"
            className="h-9 w-56 md:w-80 rounded-sm border border-border bg-surface pl-8 pr-3 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring"
          />
        </div>
        <button className="relative rounded-sm border border-border bg-background p-2 hover:bg-surface" aria-label="Notifications">
          <Bell className="h-4 w-4" />
          <span className="absolute right-1.5 top-1.5 h-1.5 w-1.5 rounded-full bg-status-warning" />
        </button>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <div className="flex items-center gap-2 rounded-sm border border-border bg-background px-2 py-1.5 cursor-pointer hover:bg-surface transition-colors">
              <div className="flex h-6 w-6 items-center justify-center rounded-sm bg-foreground text-[10px] font-semibold text-background">
                {user?.email ? getInitials(user.email) : "US"}
              </div>
              <div className="hidden md:block text-xs leading-tight">
                <div className="font-medium truncate max-w-[120px]">{user?.email?.split('@')[0]}</div>
                <div className="text-muted-foreground text-[10px] capitalize">{role?.replace('_', ' ')}</div>
              </div>
              <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />
            </div>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-56">
            <DropdownMenuLabel>My Account</DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem className="text-xs">
              <UserIcon className="mr-2 h-4 w-4" /> Profile
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem className="text-red-600 focus:text-red-600 cursor-pointer" onClick={handleSignOut}>
              <LogOut className="mr-2 h-4 w-4" /> Logout
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}
