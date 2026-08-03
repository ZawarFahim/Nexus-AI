import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Activity, Workflow } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { Skeleton } from '@/components/ui/skeleton';
import { EmptyState } from '@/components/ui/empty-state';

const MOCK_WORKFLOWS = [
  { id: 1, name: 'Smart Email', status: 'Running', time: 'Just now', color: 'text-blue-500 bg-blue-500/10' },
  { id: 2, name: 'Daily Briefing', status: 'Completed', time: '2 hours ago', color: 'text-green-500 bg-green-500/10' },
  { id: 3, name: 'GitHub Sync', status: 'Failed', time: '5 hours ago', color: 'text-destructive bg-destructive/10' },
];

export const WorkflowStatusWidget = () => {
  const [loading, setLoading] = useState(true);
  const [workflows, setWorkflows] = useState<typeof MOCK_WORKFLOWS>([]);

  useEffect(() => {
    const timer = setTimeout(() => {
      setWorkflows(MOCK_WORKFLOWS);
      setLoading(false);
    }, 1800);
    return () => clearTimeout(timer);
  }, []);

  return (
    <motion.div whileHover={{ y: -2 }} transition={{ type: "spring", stiffness: 300 }}>
      <Card className="col-span-1 shadow-lg bg-card/40 backdrop-blur-md border-border/50 h-full flex flex-col">
        <CardHeader className="pb-4">
          <CardTitle className="text-md font-medium flex items-center gap-2">
            <Activity className="h-5 w-5 text-primary" />
            Workflow Status
          </CardTitle>
        </CardHeader>
        <CardContent className="flex-1 flex flex-col">
          {loading ? (
            <div className="space-y-5">
              {[1, 2, 3].map(i => (
                <div key={i} className="flex items-center justify-between">
                  <div className="space-y-2">
                    <Skeleton className="h-4 w-24 rounded" />
                    <Skeleton className="h-3 w-16 rounded" />
                  </div>
                  <Skeleton className="h-6 w-16 rounded-full" />
                </div>
              ))}
            </div>
          ) : workflows.length === 0 ? (
            <div className="flex-1 flex items-center justify-center">
              <EmptyState 
                icon={Workflow} 
                title="No active workflows" 
                description="Trigger an automation via the chat interface or n8n dashboard." 
              />
            </div>
          ) : (
            <div className="space-y-4">
              <AnimatePresence>
                {workflows.map((wf, idx) => (
                  <motion.div 
                    key={wf.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: idx * 0.1 }}
                    className="flex items-center justify-between p-3 rounded-xl hover:bg-muted/30 transition-colors"
                  >
                    <div>
                      <p className="text-sm font-semibold leading-none">{wf.name}</p>
                      <p className="text-xs text-muted-foreground mt-1.5">{wf.time}</p>
                    </div>
                    <div className={`px-2.5 py-1 rounded-full text-xs font-semibold ${wf.color} border border-current/20`}>
                      {wf.status}
                    </div>
                  </motion.div>
                ))}
              </AnimatePresence>
            </div>
          )}
        </CardContent>
      </Card>
    </motion.div>
  );
};
