"use client";

import React from 'react';
import { Brain, MoreHorizontal, Pencil, Trash2 } from 'lucide-react';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';

export interface MemoryData {
  id: string;
  content: string;
  category: string;
  importance: number;
  date: string;
}

interface MemoryCardProps {
  memory: MemoryData;
  onDelete: (id: string) => void;
  onEdit: (id: string) => void;
}

export const MemoryCard: React.FC<MemoryCardProps> = ({ memory, onDelete, onEdit }) => {
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = React.useState(false);

  return (
    <Card className="w-full bg-card/40 backdrop-blur-sm border shadow-sm hover:shadow-md transition-shadow relative group">
      <CardHeader className="py-3 px-4 flex flex-row items-center justify-between space-y-0 pb-2">
        <div className="flex items-center gap-2">
          <Brain className="h-4 w-4 text-primary" />
          <Badge variant="secondary" className="text-xs font-normal">
            {memory.category}
          </Badge>
        </div>
        
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1 opacity-60" title={`Importance: ${memory.importance}/10`}>
            <div className="h-1.5 w-16 bg-muted rounded-full overflow-hidden">
              <div 
                className="h-full bg-primary" 
                style={{ width: `${(memory.importance / 10) * 100}%` }}
              />
            </div>
          </div>

          <DropdownMenu>
            <DropdownMenuTrigger render={<Button variant="ghost" className="h-8 w-8 p-0 opacity-0 group-hover:opacity-100 transition-opacity" />}>
              <MoreHorizontal className="h-4 w-4" />
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={() => onEdit(memory.id)}>
                <Pencil className="mr-2 h-4 w-4" />
                Edit
              </DropdownMenuItem>
              <Dialog open={isDeleteDialogOpen} onOpenChange={setIsDeleteDialogOpen}>
                <DialogTrigger render={<DropdownMenuItem onSelect={(e) => e.preventDefault()} className="text-destructive focus:text-destructive" />}>
                  <Trash2 className="mr-2 h-4 w-4" />
                  Delete
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>Are you absolutely sure?</DialogTitle>
                    <DialogDescription>
                      This action cannot be undone. This will permanently delete this memory from the Nexus AI long-term database.
                    </DialogDescription>
                  </DialogHeader>
                  <DialogFooter>
                    <Button variant="outline" onClick={() => setIsDeleteDialogOpen(false)}>Cancel</Button>
                    <Button variant="destructive" onClick={() => {
                      onDelete(memory.id);
                      setIsDeleteDialogOpen(false);
                    }}>Delete</Button>
                  </DialogFooter>
                </DialogContent>
              </Dialog>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </CardHeader>
      <CardContent className="px-4 pb-4">
        <p className="text-sm leading-relaxed">{memory.content}</p>
        <p className="text-xs text-muted-foreground mt-3">{memory.date}</p>
      </CardContent>
    </Card>
  );
};
