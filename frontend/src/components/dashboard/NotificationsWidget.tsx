import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Bell, ShieldAlert, Info } from 'lucide-react';

const MOCK_NOTIFS = [
  { id: 1, message: 'Nexus AI flagged an anomalous login attempt.', type: 'alert', time: '10m ago' },
  { id: 2, message: 'Your weekly digest is ready.', type: 'info', time: '1h ago' },
];

export const NotificationsWidget = () => {
  return (
    <Card className="col-span-1 shadow-sm">
      <CardHeader className="pb-2">
        <CardTitle className="text-md font-medium flex items-center gap-2">
          <Bell className="h-4 w-4 text-primary" />
          System Notifications
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4 mt-2">
          {MOCK_NOTIFS.map((notif) => (
            <div key={notif.id} className="flex gap-3">
              <div className="mt-0.5">
                {notif.type === 'alert' ? <ShieldAlert className="h-4 w-4 text-destructive" /> : <Info className="h-4 w-4 text-blue-500" />}
              </div>
              <div>
                <p className="text-sm font-medium leading-tight">{notif.message}</p>
                <p className="text-xs text-muted-foreground mt-1">{notif.time}</p>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
};
