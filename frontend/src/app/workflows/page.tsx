'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Play, Pause, AlertCircle, Plus, Activity, Clock } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { DashboardHeader } from '@/components/dashboard/DashboardHeader';

const MOCK_WORKFLOWS = [
  {
    id: 1,
    name: 'Daily Email Digest',
    description: 'Summarizes unread emails and posts them to Slack.',
    status: 'active',
    lastRun: '10 mins ago',
    icon: Activity
  },
  {
    id: 2,
    name: 'GitHub Issue Triage',
    description: 'Auto-labels and assigns new repository issues.',
    status: 'active',
    lastRun: '2 hours ago',
    icon: Activity
  },
  {
    id: 3,
    name: 'Weekly Analytics Report',
    description: 'Generates a PDF report of site traffic.',
    status: 'paused',
    lastRun: '5 days ago',
    icon: Pause
  },
  {
    id: 4,
    name: 'Twitter Auto-Responder',
    description: 'Replies to mentions containing specific keywords.',
    status: 'error',
    lastRun: '1 day ago',
    icon: AlertCircle
  }
];

export default function WorkflowsPage() {
  return (
    <div className="flex-1 overflow-y-auto bg-muted/20">
      <div className="container max-w-7xl mx-auto p-6 md:p-8">
        <div className="flex flex-col md:flex-row md:items-center justify-between mb-8 gap-4">
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-foreground">Workflows</h1>
            <p className="text-muted-foreground mt-1">Automate tasks across your apps using n8n.</p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {MOCK_WORKFLOWS.map((wf, idx) => (
            <motion.div
              key={wf.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: idx * 0.1 }}
              whileHover={{ y: -5 }}
            >
              <Card className="h-full bg-card/60 backdrop-blur-xl border-border/50 hover:shadow-xl transition-all duration-300 relative overflow-hidden group">
                {wf.status === 'active' && (
                  <div className="absolute top-0 right-0 w-32 h-32 bg-green-500/10 rounded-full blur-3xl -mr-10 -mt-10 group-hover:bg-green-500/20 transition-all" />
                )}
                {wf.status === 'error' && (
                  <div className="absolute top-0 right-0 w-32 h-32 bg-red-500/10 rounded-full blur-3xl -mr-10 -mt-10 group-hover:bg-red-500/20 transition-all" />
                )}
                <CardHeader>
                  <div className="flex justify-between items-start">
                    <div className="p-3 bg-primary/10 rounded-xl text-primary">
                      <wf.icon className="w-5 h-5" />
                    </div>
                    {wf.status === 'active' && <Badge className="bg-green-500/10 text-green-500 hover:bg-green-500/20 border-green-500/20">Active</Badge>}
                    {wf.status === 'paused' && <Badge variant="secondary" className="bg-muted text-muted-foreground">Paused</Badge>}
                    {wf.status === 'error' && <Badge variant="destructive" className="bg-red-500/10 text-red-500 hover:bg-red-500/20 border-red-500/20">Failed</Badge>}
                  </div>
                  <CardTitle className="mt-4 text-xl">{wf.name}</CardTitle>
                  <CardDescription className="line-clamp-2 min-h-[2.5rem]">{wf.description}</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="flex items-center text-xs text-muted-foreground mt-4">
                    <Clock className="w-3 h-3 mr-1" />
                    Last run: {wf.lastRun}
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </div>
      </div>
    </div>
  );
}
