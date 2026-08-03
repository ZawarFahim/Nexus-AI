import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Mail, ArrowRight } from 'lucide-react';
import { Badge } from '@/components/ui/badge';

const MOCK_EMAILS = [
  { id: 1, sender: 'Alex Johnson', subject: 'Re: Q3 Roadmap update', time: '10:42 AM', unread: true },
  { id: 2, sender: 'AWS Notifications', subject: 'Your AWS invoice is ready', time: 'Yesterday', unread: true },
  { id: 3, sender: 'Sarah Smith', subject: 'Feedback on the new UI', time: 'Yesterday', unread: false },
];

export const EmailWidget = () => {
  const unreadCount = MOCK_EMAILS.filter(e => e.unread).length;

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
        <div className="space-y-0 divide-y">
          {MOCK_EMAILS.map((email) => (
            <div key={email.id} className="py-3 flex items-center justify-between group cursor-pointer">
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
                <ArrowRight className="h-4 w-4 opacity-0 group-hover:opacity-100 transition-opacity text-primary" />
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
};
