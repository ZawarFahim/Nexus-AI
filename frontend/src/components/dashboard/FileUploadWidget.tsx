'use client';

import React, { useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Upload, FileText, Loader2, CheckCircle2 } from 'lucide-react';

export function FileUploadWidget() {
  const [isUploading, setIsUploading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    setSuccess(false);
    setError(null);

    const formData = new FormData();
    formData.append('file', file);

    const token = localStorage.getItem('access_token');

    try {
      const response = await fetch('http://localhost:8000/api/v1/files/upload', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        },
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Upload failed');
      }

      setSuccess(true);
      setTimeout(() => setSuccess(false), 5000);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsUploading(false);
      // clear input
      event.target.value = '';
    }
  };

  return (
    <Card className="shadow-lg border-primary/10">
      <CardHeader>
        <CardTitle className="text-sm font-medium flex items-center">
          <FileText className="w-4 h-4 mr-2 text-primary" />
          RAG Knowledge Base
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex flex-col items-center justify-center border-2 border-dashed border-muted-foreground/20 rounded-xl p-6 bg-muted/30 transition-colors hover:bg-muted/50 relative">
          <input
            type="file"
            accept=".txt,.md,.json,.csv"
            className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
            onChange={handleFileUpload}
            disabled={isUploading}
          />
          {isUploading ? (
            <div className="flex flex-col items-center text-primary">
              <Loader2 className="w-8 h-8 animate-spin mb-2" />
              <span className="text-sm font-medium">Indexing file...</span>
            </div>
          ) : success ? (
            <div className="flex flex-col items-center text-green-500">
              <CheckCircle2 className="w-8 h-8 mb-2" />
              <span className="text-sm font-medium">Indexed to Memory!</span>
            </div>
          ) : (
            <>
              <Upload className="w-8 h-8 text-muted-foreground mb-3" />
              <p className="text-sm font-medium text-foreground">Upload a file</p>
              <p className="text-xs text-muted-foreground text-center mt-1">
                Drag & drop or click to upload text files for the AI to learn.
              </p>
            </>
          )}
        </div>
        {error && (
          <p className="text-xs text-red-500 mt-3 text-center">{error}</p>
        )}
      </CardContent>
    </Card>
  );
}
