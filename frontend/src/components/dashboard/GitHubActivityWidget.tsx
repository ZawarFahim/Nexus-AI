"use client";

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { GitPullRequest, GitCommit, GitMerge, Star } from 'lucide-react';
import { Skeleton } from '@/components/ui/skeleton';

export const GitHubActivityWidget = () => {
  const [loading, setLoading] = useState(true);
  const [repos, setRepos] = useState<any[]>([]);

  useEffect(() => {
    const fetchGithub = async () => {
      try {
        const response = await fetch('http://localhost:8000/api/v1/dashboard/github', {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('access_token')}`
          }
        });
        if (response.ok) {
          const data = await response.json();
          setRepos(data);
        }
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    };
    fetchGithub();
  }, []);
  return (
    <Card className="col-span-1 shadow-sm">
      <CardHeader className="pb-2">
        <CardTitle className="text-md font-medium flex items-center gap-2">
          <GitPullRequest className="h-4 w-4 text-primary" />
          GitHub Activity
        </CardTitle>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="space-y-4 mt-2">
            {[1, 2, 3].map((i) => (
              <div key={i} className="flex gap-3">
                <Skeleton className="h-4 w-4 rounded-full mt-0.5" />
                <div className="space-y-2 flex-1">
                  <Skeleton className="h-4 w-3/4" />
                  <Skeleton className="h-3 w-1/2" />
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="space-y-4 mt-2">
            {repos.length === 0 ? (
              <div className="text-center text-sm text-muted-foreground py-4">No recent activity.</div>
            ) : (
              repos.slice(0, 5).map((repo, idx) => (
                <div key={idx} className="flex gap-3 items-start">
                  <div className="mt-0.5"><GitCommit className="h-4 w-4 text-blue-500" /></div>
                  <div>
                    <a href={repo.url} target="_blank" rel="noreferrer" className="text-sm font-medium leading-none hover:underline">{repo.name}</a>
                    <div className="flex items-center gap-2 mt-1">
                      <span className="text-xs text-muted-foreground max-w-[150px] truncate">{repo.description || 'No description'}</span>
                      <span className="text-xs text-muted-foreground border-l pl-2 flex items-center gap-1"><Star className="h-3 w-3" /> {repo.stars}</span>
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
