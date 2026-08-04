'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { FileUploadWidget } from '@/components/dashboard/FileUploadWidget';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { FileText, Clock, FileType, Search } from 'lucide-react';
import { Input } from '@/components/ui/input';

const MOCK_FILES = [
  { id: 1, name: 'Project_Requirements.pdf', size: '2.4 MB', type: 'PDF', date: '2 hours ago' },
  { id: 2, name: 'Q3_Financial_Data.csv', size: '156 KB', type: 'CSV', date: 'Yesterday' },
  { id: 3, name: 'Design_System_Notes.md', size: '12 KB', type: 'Markdown', date: '3 days ago' },
  { id: 4, name: 'API_Documentation_v2.txt', size: '45 KB', type: 'Text', date: '1 week ago' },
];

export default function FilesPage() {
  return (
    <div className="flex-1 overflow-y-auto bg-muted/20">
      <div className="container max-w-7xl mx-auto p-6 md:p-8">
        <div className="flex flex-col md:flex-row md:items-center justify-between mb-8 gap-4">
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-foreground flex items-center gap-2">
              <FileText className="w-8 h-8 text-primary" />
              Files & Documents
            </h1>
            <p className="text-muted-foreground mt-1">Upload and manage documents for your RAG knowledge base.</p>
          </div>
          <div className="relative w-full md:w-64">
            <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input placeholder="Search files..." className="pl-8 bg-card" />
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
          <div className="lg:col-span-1">
            <FileUploadWidget />
          </div>
          <div className="lg:col-span-2">
            <Card className="h-full bg-card/60 backdrop-blur-xl border-border/50">
              <CardHeader>
                <CardTitle>Recent Uploads</CardTitle>
                <CardDescription>Files successfully embedded into the vector database.</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {MOCK_FILES.map((file, idx) => (
                    <motion.div 
                      key={file.id}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: idx * 0.1 }}
                      className="flex items-center justify-between p-3 rounded-lg hover:bg-muted/50 transition-colors border border-transparent hover:border-border cursor-pointer group"
                    >
                      <div className="flex items-center gap-3">
                        <div className="p-2 bg-primary/10 rounded-lg text-primary group-hover:scale-110 transition-transform">
                          <FileType className="w-5 h-5" />
                        </div>
                        <div>
                          <p className="text-sm font-medium text-foreground">{file.name}</p>
                          <div className="flex items-center gap-2 text-xs text-muted-foreground mt-0.5">
                            <span>{file.type}</span>
                            <span>•</span>
                            <span>{file.size}</span>
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center text-xs text-muted-foreground">
                        <Clock className="w-3 h-3 mr-1" />
                        {file.date}
                      </div>
                    </motion.div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}
