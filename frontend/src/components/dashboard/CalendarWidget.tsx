import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Calendar, Video } from 'lucide-react';

const MOCK_EVENTS = [
  { id: 1, title: 'Standup Meeting', time: '10:00 AM - 10:30 AM', type: 'video' },
  { id: 2, title: 'Architecture Review', time: '2:00 PM - 3:00 PM', type: 'video' },
  { id: 3, title: 'Focus Time', time: '3:30 PM - 5:00 PM', type: 'focus' },
];

export const CalendarWidget = () => {
  return (
    <Card className="col-span-1 shadow-sm">
      <CardHeader className="pb-2">
        <CardTitle className="text-md font-medium flex items-center gap-2">
          <Calendar className="h-4 w-4 text-primary" />
          Today's Schedule
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4 mt-2">
          {MOCK_EVENTS.map((event) => (
            <div key={event.id} className="flex gap-4 items-start relative pl-2">
              <div className="absolute left-0 top-1 bottom-0 w-0.5 bg-primary rounded-full"></div>
              <div className="flex-1">
                <p className="text-sm font-semibold">{event.title}</p>
                <div className="flex items-center gap-2 mt-1">
                  <span className="text-xs text-muted-foreground">{event.time}</span>
                  {event.type === 'video' && <Video className="h-3 w-3 text-muted-foreground" />}
                </div>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
};
