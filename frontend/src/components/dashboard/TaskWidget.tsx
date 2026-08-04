"use client";

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { CheckCircle2, Circle } from 'lucide-react';
import { Skeleton } from '@/components/ui/skeleton';
import { motion, AnimatePresence } from 'framer-motion';
import { EmptyState } from '@/components/ui/empty-state';
import { ListTodo } from 'lucide-react';

const MOCK_TASKS = [
  { id: 1, title: 'Review PR #42 in Nexus-AI', completed: true },
  { id: 2, title: 'Draft Q3 Planning Document', completed: false },
  { id: 3, title: 'Reply to Sarah regarding UI bugs', completed: false },
];

export const TaskWidget = () => {
  const [loading, setLoading] = useState(true);
  const [tasks, setTasks] = useState<{id: string, title: string, priority: string, status: string, completed: boolean}[]>([]);

  useEffect(() => {
    const fetchTasks = async () => {
      try {
        const response = await fetch('http://localhost:8000/api/v1/dashboard/tasks', {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('access_token')}`
          }
        });
        if (response.ok) {
          const data = await response.json();
          setTasks(data.map((t: any) => ({...t, completed: t.status === 'Completed'})));
        }
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    };
    fetchTasks();
  }, []);

  const completedCount = tasks.filter(t => t.completed).length;
  const progress = tasks.length > 0 ? (completedCount / tasks.length) * 100 : 0;

  return (
    <motion.div whileHover={{ y: -2 }} transition={{ type: "spring", stiffness: 300 }}>
      <Card className="col-span-1 shadow-lg bg-card/40 backdrop-blur-md border-border/50 h-full flex flex-col">
        <CardHeader className="pb-4">
          <div className="flex items-center justify-between">
            <CardTitle className="text-md font-medium flex items-center gap-2">
              <CheckCircle2 className="h-5 w-5 text-primary" />
              Today's Tasks
            </CardTitle>
            {!loading && <Badge variant="secondary" className="bg-primary/20 text-primary hover:bg-primary/30 transition-colors">{completedCount}/{tasks.length}</Badge>}
          </div>
        </CardHeader>
        <CardContent className="flex-1 flex flex-col">
          {loading ? (
            <div className="space-y-4">
              <Skeleton className="h-2 w-full mb-6" />
              {[1, 2, 3].map(i => (
                <div key={i} className="flex items-center gap-3">
                  <Skeleton className="h-5 w-5 rounded-full shrink-0" />
                  <Skeleton className="h-4 w-full rounded" />
                </div>
              ))}
            </div>
          ) : tasks.length === 0 ? (
            <div className="flex-1 flex items-center justify-center">
              <EmptyState 
                icon={ListTodo} 
                title="You're all caught up!" 
                description="No tasks assigned for today. Time to relax or ask Nexus AI to find you some work." 
              />
            </div>
          ) : (
            <>
              <Progress value={progress} className="h-1.5 mb-6 bg-muted/50" />
              <div className="space-y-4">
                <AnimatePresence>
                  {tasks.map((task) => (
                    <motion.div 
                      key={task.id} 
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      className="flex items-start gap-3 group cursor-pointer"
                      onClick={() => setTasks(tasks.map(t => t.id === task.id ? { ...t, completed: !t.completed } : t))}
                    >
                      <div className="mt-0.5 shrink-0 transition-transform group-hover:scale-110">
                        {task.completed ? (
                          <CheckCircle2 className="h-5 w-5 text-primary" />
                        ) : (
                          <Circle className="h-5 w-5 text-muted-foreground group-hover:text-primary transition-colors" />
                        )}
                      </div>
                      <span className={`text-sm transition-all duration-300 ${task.completed ? 'line-through text-muted-foreground opacity-60' : 'text-foreground'}`}>
                        {task.title}
                      </span>
                    </motion.div>
                  ))}
                </AnimatePresence>
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </motion.div>
  );
};
