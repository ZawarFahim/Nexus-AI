import React from 'react';
import { Bot } from 'lucide-react';

export const DashboardHeader = () => {
  const hour = new Date().getHours();
  let greeting = 'Good evening';
  if (hour < 12) greeting = 'Good morning';
  else if (hour < 18) greeting = 'Good afternoon';

  return (
    <div className="flex flex-col md:flex-row items-start md:items-center justify-between mb-8 gap-4">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">{greeting}, User!</h1>
        <p className="text-muted-foreground mt-1">
          Here is what is happening across your integrated platforms today.
        </p>
      </div>
      <div className="flex items-center gap-3 px-4 py-2 bg-primary/10 rounded-full border border-primary/20">
        <Bot className="h-5 w-5 text-primary" />
        <span className="text-sm font-medium text-primary">Nexus Agent is Active</span>
      </div>
    </div>
  );
};
