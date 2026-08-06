'use client';

import React, { useEffect, useState } from 'react';
import { API_BASE_URL } from '@/lib/api';
import { motion } from 'framer-motion';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { BrainCircuit, Loader2, Sparkles, Tag, Plus } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';

interface Memory {
  id?: string;
  title: string;
  content: string;
  category: string;
  importance_score: number;
  created_at: string;
}

export default function MemoryPage() {
  const [memories, setMemories] = useState<Memory[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchMemories = async () => {
      try {
        const token = localStorage.getItem('access_token');
        if (!token) throw new Error("Not authenticated");

        const response = await fetch(`${API_BASE_URL}/memory/`, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });

        if (!response.ok) {
          throw new Error("Failed to fetch memories");
        }

        const data = await response.json();
        setMemories(data);
      } catch (err: any) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchMemories();
  }, []);

  return (
    <div className="flex-1 overflow-y-auto bg-muted/20">
      <div className="container max-w-7xl mx-auto p-6 md:p-8">
        <div className="flex flex-col md:flex-row md:items-center justify-between mb-8 gap-4">
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-foreground flex items-center gap-2">
              <BrainCircuit className="w-8 h-8 text-primary" />
              Long-Term Memory
            </h1>
            <p className="text-muted-foreground mt-1">Facts, preferences, and context securely saved for your AI.</p>
          </div>
          <Button className="shrink-0 gap-2 shadow-lg shadow-primary/20">
            <Plus className="w-4 h-4" />
            Add Memory
          </Button>
        </div>

        {error && (
          <div className="p-4 bg-red-500/10 text-red-500 rounded-lg border border-red-500/20 mb-6 text-sm">
            {error}
          </div>
        )}

        {loading ? (
          <div className="flex flex-col items-center justify-center h-64 text-muted-foreground">
            <Loader2 className="w-8 h-8 animate-spin mb-4" />
            <p>Accessing memory vault...</p>
          </div>
        ) : memories.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-64 border-2 border-dashed border-muted-foreground/20 rounded-xl bg-muted/10">
            <BrainCircuit className="w-12 h-12 text-muted-foreground/50 mb-4" />
            <h3 className="text-lg font-medium text-foreground">No memories found</h3>
            <p className="text-sm text-muted-foreground mt-1 text-center max-w-md">
              Your memory vault is empty. Try asking the AI to "remember that I prefer dark mode" or use the Add Memory button.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {memories.map((memory, idx) => (
              <motion.div
                key={memory.id || idx}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: idx * 0.05 }}
              >
                <Card className="h-full bg-card/60 backdrop-blur-xl border-border/50 hover:border-primary/30 transition-colors">
                  <CardHeader className="pb-3">
                    <div className="flex justify-between items-start mb-2">
                      <Badge variant="secondary" className="flex items-center gap-1 bg-primary/10 text-primary hover:bg-primary/20">
                        <Tag className="w-3 h-3" />
                        {memory.category || 'General'}
                      </Badge>
                      <div className="flex items-center text-xs font-medium text-amber-500 bg-amber-500/10 px-2 py-1 rounded-full">
                        <Sparkles className="w-3 h-3 mr-1" />
                        {memory.importance_score.toFixed(1)}
                      </div>
                    </div>
                    <CardTitle className="text-lg">{memory.title || "Untitled Memory"}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm text-muted-foreground mb-4">
                      {memory.content}
                    </p>
                    <p className="text-xs text-muted-foreground/60">
                      Saved {new Date(memory.created_at).toLocaleDateString()}
                    </p>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
