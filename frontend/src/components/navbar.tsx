import { SidebarTrigger } from "@/components/ui/sidebar"

export function Navbar() {
  return (
    <header className="sticky top-0 z-10 flex h-14 items-center gap-4 border-b bg-background px-6">
      <SidebarTrigger />
      <div className="flex-1 font-semibold">Nexus AI Dashboard</div>
    </header>
  )
}
