'use client';

import React, { useState } from 'react';
import { MemorySearch } from '@/components/memory/MemorySearch';
import { MemoryTimeline } from '@/components/memory/MemoryTimeline';
import { MemoryData } from '@/components/memory/MemoryCard';
import { BrainCircuit } from 'lucide-react';

// Highly realistic mock data for UI construction
const INITIAL_MEMORIES: MemoryData[] = [
  {
    id: '1',
    content: 'The user prefers code snippets to be written in TypeScript rather than standard JavaScript.',
    category: 'Preferences',
    importance: 8.5,
    date: 'August 1, 2026'
  },
  {
    id: '2',
    content: 'The user works as a Senior AI Architect at a tech startup.',
    category: 'Work',
    importance: 9.0,
    date: 'August 2, 2026'
  },
  {
    id: '3',
    content: 'The user explicitly requested that all UI components must follow a premium, glassmorphic Web 3.0 aesthetic.',
    category: 'Preferences',
    importance: 9.5,
    date: 'August 3, 2026'
  },
  {
    id: '4',
    content: 'The user is learning about vector databases, specifically Qdrant.',
    category: 'Personal',
    importance: 6.0,
    date: 'August 3, 2026'
  }
];

export default function MemoryPage() {
  const [loading, setLoading] = useState(true);
  const [memories, setMemories] = useState<MemoryData[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('all');

  useEffect(() => {
    const timer = setTimeout(() => {
      setMemories(INITIAL_MEMORIES);
      setLoading(false);
    }, 1500);
    return () => clearTimeout(timer);
  }, []);

  const handleDelete = (id: string) => {
    // In a real app, this would be an API call
    setMemories(prev => prev.filter(m => m.id !== id));
  };

  const handleEdit = (id: string) => {
    // Placeholder for opening an edit modal
    console.log("Edit memory:", id);
  };

  // Filter logic
  const filteredMemories = memories.filter(m => {
    const matchesSearch = m.content.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesCategory = categoryFilter === 'all' || m.category === categoryFilter;
    return matchesSearch && matchesCategory;
  });

  return (
    <div className="flex-1 overflow-y-auto bg-transparent min-h-screen">
      <div className="container max-w-4xl mx-auto p-6 md:p-10">
        
        {/* Header */}
        <div className="mb-10">
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2 bg-primary/10 rounded-2xl border border-primary/20 shadow-inner">
              <BrainCircuit className="h-8 w-8 text-primary" />
            </div>
            <h1 className="text-4xl font-extrabold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-foreground to-foreground/70">Long-Term Memory</h1>
          </div>
          <p className="text-muted-foreground text-lg ml-1 mt-3">
            Review and manage the facts, preferences, and context Nexus AI has learned about you.
          </p>
        </div>

        {/* Search & Filter Bar */}
        <div className="sticky top-0 z-10 py-4 bg-background/60 backdrop-blur-2xl border-b border-border/50 mb-8 -mx-6 px-6 md:-mx-10 md:px-10 shadow-sm">
          <MemorySearch 
            onSearch={setSearchQuery} 
            onFilterChange={setCategoryFilter} 
          />
        </div>

        {/* Timeline Content */}
        <MemoryTimeline 
          memories={filteredMemories} 
          onDelete={handleDelete} 
          onEdit={handleEdit} 
          loading={loading}
        />
        
      </div>
    </div>
  );
}
