import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { CheckCircle2, Clock } from 'lucide-react';

const MOCK_TASKS = [
  { id: 1, title: 'Review PR #42 in Nexus-AI', completed: true },
  { id: 2, title: 'Draft Q3 Planning Document', completed: false },
  { id: 3, title: 'Reply to Sarah regarding UI bugs', completed: false },
];

export const TaskWidget = () => {
  const completedCount = MOCK_TASKS.filter(t => t.completed).length;
  const progress = (completedCount / MOCK_TASKS.length) * 100;

  return (
    <Card className="col-span-1 shadow-sm">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-md font-medium flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 text-primary" />
            Today's Tasks
          </CardTitle>
          <Badge variant="secondary">{completedCount}/{MOCK_TASKS.length}</Badge>
        </div>
      </CardHeader>
      <CardContent>
        <Progress value={progress} className="h-2 mb-4" />
        <div className="space-y-3">
          {MOCK_TASKS.map((task) => (
            <div key={task.id} className="flex items-start gap-3">
              <div className={`mt-0.5 h-4 w-4 rounded-full border ${task.completed ? 'bg-primary border-primary flex items-center justify-center' : 'border-muted-foreground'}`}>
                {task.completed && <CheckCircle2 className="h-3 w-3 text-primary-foreground" />}
              </div>
              <span className={`text-sm ${task.completed ? 'line-through text-muted-foreground' : 'text-foreground'}`}>
                {task.title}
              </span>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
};
