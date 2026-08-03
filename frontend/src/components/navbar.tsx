import { SidebarTrigger } from "@/components/ui/sidebar"
import { useAuth } from "@/contexts/AuthContext"
import { Button } from "@/components/ui/button"
import { LogOut, User } from "lucide-react"

export function Navbar() {
  const { user, logout } = useAuth();

  return (
    <header className="sticky top-0 z-10 flex h-14 items-center gap-4 border-b bg-background/80 backdrop-blur-md px-6">
      <SidebarTrigger />
      <div className="flex-1 font-semibold text-lg bg-clip-text text-transparent bg-gradient-to-r from-primary to-blue-400">
        Nexus AI
      </div>
      
      {user && (
        <div className="flex items-center gap-4">
          <div className="hidden md:flex items-center gap-2 text-sm text-muted-foreground">
            <User className="w-4 h-4" />
            <span>{user.full_name}</span>
          </div>
          <Button variant="ghost" size="icon" onClick={logout} title="Logout">
            <LogOut className="w-5 h-5 text-destructive" />
          </Button>
        </div>
      )}
    </header>
  )
}
