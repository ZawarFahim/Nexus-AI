import React from 'react';
import { DashboardHeader } from '@/components/dashboard/DashboardHeader';
import { TaskWidget } from '@/components/dashboard/TaskWidget';
import { WorkflowStatusWidget } from '@/components/dashboard/WorkflowStatusWidget';
import { GitHubActivityWidget } from '@/components/dashboard/GitHubActivityWidget';
import { EmailWidget } from '@/components/dashboard/EmailWidget';
import { CalendarWidget } from '@/components/dashboard/CalendarWidget';
import { NotificationsWidget } from '@/components/dashboard/NotificationsWidget';
import { AnalyticsWidget } from '@/components/dashboard/AnalyticsWidget';

export default function DashboardPage() {
  return (
    <div className="flex-1 overflow-y-auto bg-muted/20">
      <div className="container max-w-7xl mx-auto p-6 md:p-8">
        <DashboardHeader />
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {/* Main Content Column */}
          <div className="col-span-1 lg:col-span-2 flex flex-col gap-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <TaskWidget />
              <WorkflowStatusWidget />
            </div>
            
            <EmailWidget />
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <GitHubActivityWidget />
              <NotificationsWidget />
            </div>
          </div>
          
          {/* Right Sidebar Column */}
          <div className="col-span-1 flex flex-col gap-6">
            <CalendarWidget />
            <AnalyticsWidget />
          </div>
        </div>
      </div>
    </div>
  );
}
