"use client";

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Calendar, Video } from 'lucide-react';
import { Skeleton } from '@/components/ui/skeleton';

const MOCK_EVENTS = [
  { id: 1, title: 'Standup Meeting', time: '10:00 AM - 10:30 AM', type: 'video' },
  { id: 2, title: 'Architecture Review', time: '2:00 PM - 3:00 PM', type: 'video' },
  { id: 3, title: 'Focus Time', time: '3:30 PM - 5:00 PM', type: 'focus' },
];

export const CalendarWidget = () => {
  const [loading, setLoading] = useState(true);
  const [events, setEvents] = useState<any[]>([]);

  useEffect(() => {
    const fetchCalendar = async () => {
      try {
        const response = await fetch('http://localhost:8000/api/v1/dashboard/calendar', {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('access_token')}`
          }
        });
        if (response.ok) {
          const data = await response.json();
          setEvents(data);
        }
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    };
    fetchCalendar();
  }, []);

  return (
    <Card className="col-span-1 shadow-sm">
      <CardHeader className="pb-2">
        <CardTitle className="text-md font-medium flex items-center gap-2">
          <Calendar className="h-4 w-4 text-primary" />
          Today's Schedule
        </CardTitle>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="space-y-4 mt-2">
            {[1, 2, 3].map((i) => (
              <div key={i} className="flex gap-4 items-start relative pl-2">
                <div className="absolute left-0 top-1 bottom-0 w-0.5 bg-primary/20 rounded-full"></div>
                <div className="space-y-2 flex-1">
                  <Skeleton className="h-4 w-3/4" />
                  <Skeleton className="h-3 w-1/2" />
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="space-y-4 mt-2">
            {events.length === 0 ? (
              <div className="text-center text-sm text-muted-foreground py-4">No events today.</div>
            ) : (
              events.map((event) => (
                <div key={event.id} className="flex gap-4 items-start relative pl-2">
                  <div className="absolute left-0 top-1 bottom-0 w-0.5 bg-primary rounded-full"></div>
                  <div className="flex-1">
                    <p className="text-sm font-semibold">{event.title}</p>
                    <div className="flex items-center gap-2 mt-1">
                      <span className="text-xs text-muted-foreground">
                        {new Date(event.time).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                      </span>
                      {event.type === 'video' && <Video className="h-3 w-3 text-muted-foreground" />}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
};
