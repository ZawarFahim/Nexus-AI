"use client";

import React, { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { GitBranch, Save, CheckCircle2 } from 'lucide-react';
import { api } from '@/lib/api';

export default function SettingsPage() {
  const [settings, setSettings] = useState({
    github_pat: '',
    n8n_webhook_url: '',
    n8n_api_key: ''
  });
  const [googleConnected, setGoogleConnected] = useState(false);
  const [googleEmail, setGoogleEmail] = useState('');
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    const fetchSettings = async () => {
      try {
        const data = await api.get<any>('/settings');
        setSettings({
          github_pat: data.github_pat || '',
          n8n_webhook_url: data.n8n_webhook_url || '',
          n8n_api_key: data.n8n_api_key || ''
        });
        setGoogleConnected(data.google_connected || false);
        setGoogleEmail(data.google_email || '');
      } catch (err) {
        console.error("Failed to load settings:", err);
      }
    };
    fetchSettings();
  }, []);

  const handleSave = async () => {
    setSaving(true);
    try {
      await api.put('/settings', settings);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (err) {
      console.error("Failed to save settings:", err);
    } finally {
      setSaving(false);
    }
  };

  const handleGoogleAuth = () => {
    window.location.href = 'http://localhost:8000/api/v1/oauth/google/login';
  };

  return (
    <div className="flex-1 overflow-y-auto bg-muted/20">
      <div className="container max-w-4xl mx-auto p-6 md:p-8">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
            <p className="text-muted-foreground mt-1">Manage your integrations and API keys.</p>
          </div>
          <Button onClick={handleSave} disabled={saving} className="gap-2">
            {saved ? <CheckCircle2 className="h-4 w-4" /> : <Save className="h-4 w-4" />}
            {saved ? 'Saved!' : saving ? 'Saving...' : 'Save Changes'}
          </Button>
        </div>

        <div className="grid gap-6">
          <Card>
            <CardHeader>
              <CardTitle>Google Workspace</CardTitle>
              <CardDescription>Connect Google to enable Gmail and Calendar features.</CardDescription>
            </CardHeader>
            <CardContent>
              {googleConnected ? (
                <div className="flex items-center justify-between bg-muted p-4 rounded-md border">
                  <div className="flex items-center gap-3">
                    <div className="bg-primary/20 p-2 rounded-full text-primary">
                      <CheckCircle2 className="h-5 w-5" />
                    </div>
                    <div>
                      <p className="font-medium">Connected</p>
                      <p className="text-sm text-muted-foreground">{googleEmail}</p>
                    </div>
                  </div>
                  <Button onClick={handleGoogleAuth} variant="outline" size="sm">
                    Reconnect
                  </Button>
                </div>
              ) : (
                <Button onClick={handleGoogleAuth} variant="outline" className="gap-2">
                  Connect Google Account
                </Button>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <GitBranch className="h-5 w-5" /> GitHub
              </CardTitle>
              <CardDescription>Provide a Personal Access Token (PAT) for GitHub integrations.</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium">GitHub Personal Access Token</label>
                  <Input 
                    type="password" 
                    placeholder="ghp_xxxxxxxxxxxxxxxxxxxx" 
                    value={settings.github_pat}
                    onChange={(e) => setSettings({...settings, github_pat: e.target.value})}
                  />
                  <p className="text-xs text-muted-foreground">Requires repo and user scopes.</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>n8n Automation</CardTitle>
              <CardDescription>Connect your n8n instance to enable workflow executions.</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium">Webhook URL</label>
                  <Input 
                    placeholder="https://your-n8n-instance.com/webhook/..." 
                    value={settings.n8n_webhook_url}
                    onChange={(e) => setSettings({...settings, n8n_webhook_url: e.target.value})}
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">API Key (Optional)</label>
                  <Input 
                    type="password" 
                    placeholder="n8n API Key" 
                    value={settings.n8n_api_key}
                    onChange={(e) => setSettings({...settings, n8n_api_key: e.target.value})}
                  />
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
