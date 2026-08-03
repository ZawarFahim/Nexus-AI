import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Activity } from 'lucide-react';

const MOCK_WORKFLOWS = [
  { id: 1, name: 'Smart Email', status: 'Running', time: 'Just now', color: 'text-blue-500' },
  { id: 2, name: 'Daily Briefing', status: 'Completed', time: '2 hours ago', color: 'text-green-500' },
  { id: 3, name: 'GitHub Sync', status: 'Failed', time: '5 hours ago', color: 'text-destructive' },
];

export const WorkflowStatusWidget = () => {
  return (
    <Card className="col-span-1 shadow-sm">
      <CardHeader className="pb-2">
        <CardTitle className="text-md font-medium flex items-center gap-2">
          <Activity className="h-4 w-4 text-primary" />
          Workflow Status
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4 mt-2">
          {MOCK_WORKFLOWS.map((wf) => (
            <div key={wf.id} className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium leading-none">{wf.name}</p>
                <p className="text-xs text-muted-foreground mt-1">{wf.time}</p>
              </div>
              <div className={`text-xs font-semibold ${wf.color}`}>
                {wf.status}
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
};
