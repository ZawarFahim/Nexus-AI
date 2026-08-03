import React from 'react';
import { MemoryData, MemoryCard } from './MemoryCard';

interface MemoryTimelineProps {
  memories: MemoryData[];
  onDelete: (id: string) => void;
  onEdit: (id: string) => void;
}

export const MemoryTimeline: React.FC<MemoryTimelineProps> = ({ memories, onDelete, onEdit }) => {
  if (memories.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-center">
        <h3 className="text-lg font-semibold mb-2">No memories found</h3>
        <p className="text-sm text-muted-foreground">The AI hasn't learned any facts matching this filter yet.</p>
      </div>
    );
  }

  return (
    <div className="relative pl-6 md:pl-8 border-l border-primary/20 space-y-8 mt-8 pb-12">
      {memories.map((memory, index) => (
        <div key={memory.id} className="relative">
          {/* Timeline Dot */}
          <div className="absolute -left-[37px] md:-left-[45px] top-4 h-5 w-5 rounded-full border-4 border-background bg-primary shadow-sm" />
          
          <MemoryCard 
            memory={memory} 
            onDelete={onDelete} 
            onEdit={onEdit} 
          />
        </div>
      ))}
    </div>
  );
};
