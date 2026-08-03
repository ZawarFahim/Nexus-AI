"use client";

import React from 'react';
import { Search } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

interface MemorySearchProps {
  onSearch: (query: string) => void;
  onFilterChange: (category: string) => void;
}

export const MemorySearch: React.FC<MemorySearchProps> = ({ onSearch, onFilterChange }) => {
  return (
    <div className="flex flex-col md:flex-row gap-4 w-full max-w-2xl">
      <div className="relative flex-1">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input 
          placeholder="Search memories..." 
          className="pl-9 bg-background/50 backdrop-blur-sm"
          onChange={(e) => onSearch(e.target.value)}
        />
      </div>
      <Select onValueChange={(val) => onFilterChange(val || "all")} defaultValue="all">
        <SelectTrigger className="w-full md:w-[180px] bg-background/50 backdrop-blur-sm">
          <SelectValue placeholder="Category" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All Categories</SelectItem>
          <SelectItem value="Preferences">Preferences</SelectItem>
          <SelectItem value="Work">Work</SelectItem>
          <SelectItem value="Personal">Personal</SelectItem>
        </SelectContent>
      </Select>
    </div>
  );
};
