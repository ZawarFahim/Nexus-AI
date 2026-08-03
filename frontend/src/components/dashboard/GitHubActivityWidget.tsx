import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { GitPullRequest, GitCommit, GitMerge } from 'lucide-react';

const MOCK_GITHUB = [
  { id: 1, type: 'pr', repo: 'nexus-ai/backend', message: 'Add n8n integration tool', time: '1h ago', icon: <GitPullRequest className="h-4 w-4 text-green-500" /> },
  { id: 2, type: 'commit', repo: 'nexus-ai/frontend', message: 'Update chat UI components', time: '3h ago', icon: <GitCommit className="h-4 w-4 text-blue-500" /> },
  { id: 3, type: 'merge', repo: 'nexus-ai/docs', message: 'Merge pull request #12 from branch', time: '1d ago', icon: <GitMerge className="h-4 w-4 text-purple-500" /> },
];

export const GitHubActivityWidget = () => {
  return (
    <Card className="col-span-1 shadow-sm">
      <CardHeader className="pb-2">
        <CardTitle className="text-md font-medium flex items-center gap-2">
          <GitPullRequest className="h-4 w-4 text-primary" />
          GitHub Activity
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4 mt-2">
          {MOCK_GITHUB.map((item) => (
            <div key={item.id} className="flex gap-3">
              <div className="mt-0.5">{item.icon}</div>
              <div>
                <p className="text-sm font-medium leading-none">{item.message}</p>
                <div className="flex items-center gap-2 mt-1">
                  <span className="text-xs text-muted-foreground">{item.repo}</span>
                  <span className="text-xs text-muted-foreground border-l pl-2">{item.time}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
};
