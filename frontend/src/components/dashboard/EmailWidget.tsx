"use client";

import React, { useState, useEffect } from 'react';
import { API_BASE_URL } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Mail, ArrowRight } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';

export const EmailWidget = () => {
  const [loading, setLoading] = useState(true);
  const [emails, setEmails] = useState<any[]>([]);

  useEffect(() => {
    const fetchEmails = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/dashboard/emails`, {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('access_token')}`
          }
        });
        if (response.ok) {
          const data = await response.json();
          // API returns simplified data for MVP
          setEmails(data.map((e: any, i: number) => ({
            id: e.id,
            sender: `Sender ${i+1}`,
            subject: e.snippet.substring(0, 50) + '...',
            time: 'Recently',
            unread: true
          })));
        }
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    };
    fetchEmails();
  }, []);

  const unreadCount = emails.filter(e => e.unread).length;

  return (
    <Card className="col-span-1 md:col-span-2 shadow-sm">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-md font-medium flex items-center gap-2">
            <Mail className="h-4 w-4 text-primary" />
            Priority Inbox
          </CardTitle>
          <Badge variant="destructive">{unreadCount} Unread</Badge>
        </div>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="space-y-4 py-3">
            {[1, 2, 3].map(i => (
              <div key={i} className="flex justify-between items-center">
                <div className="space-y-2">
                  <Skeleton className="h-4 w-[150px]" />
                  <Skeleton className="h-4 w-[250px]" />
                </div>
                <Skeleton className="h-4 w-[50px]" />
              </div>
            ))}
          </div>
        ) : (
          <div className="space-y-0 divide-y">
            {emails.length === 0 ? (
              <div className="py-8 text-center text-sm text-muted-foreground">
                No recent emails found.
              </div>
            ) : (
              emails.map((email) => (
                <div key={email.id} className="py-3 flex items-center justify-between">
                  <div>
                    <p className={`text-sm ${email.unread ? 'font-semibold text-foreground' : 'font-medium text-muted-foreground'}`}>
                      {email.sender}
                    </p>
                    <p className="text-sm text-muted-foreground truncate max-w-[200px] sm:max-w-[400px]">
                      {email.subject}
                    </p>
                  </div>
                  <div className="flex items-center gap-4">
                    <span className="text-xs text-muted-foreground">{email.time}</span>
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
