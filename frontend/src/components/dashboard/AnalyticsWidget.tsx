import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { BarChart3 } from 'lucide-react';

export const AnalyticsWidget = () => {
  return (
    <Card className="col-span-1 shadow-sm">
      <CardHeader className="pb-2">
        <CardTitle className="text-md font-medium flex items-center gap-2">
          <BarChart3 className="h-4 w-4 text-primary" />
          Time Saved by AI
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex flex-col items-center justify-center py-4">
          <h2 className="text-4xl font-bold text-primary">12h 45m</h2>
          <p className="text-sm text-muted-foreground mt-2">This week across 34 automated workflows</p>
        </div>
      </CardContent>
    </Card>
  );
};
