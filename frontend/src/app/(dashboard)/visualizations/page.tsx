/**
 * Visualizations Page
 *
 * List and create visualizations
 */

'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Plus, Grid, List as ListIcon, Loader2 } from 'lucide-react';
import { useVisualizations, useDeleteVisualization } from '@/lib/hooks/useVisualizations';
import { VisualizationResponse } from '@/types/api';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { ChartContainer } from '@/components/charts/ChartContainer';

type ViewMode = 'grid' | 'list';

export default function VisualizationsPage() {
  const router = useRouter();
  const [viewMode, setViewMode] = useState<ViewMode>('grid');

  // Fetch visualizations
  const { data, isLoading } = useVisualizations(
    {},
    { page: 1, page_size: 20 }
  );

  // Delete mutation
  const deleteMutation = useDeleteVisualization({
    onSuccess: () => {
      console.log('Visualization deleted successfully');
    },
  });

  const handleCreate = () => {
    router.push('/visualizations/new');
  };

  const handleEdit = (viz: VisualizationResponse) => {
    router.push(`/visualizations/${viz.id}/edit`);
  };

  const handleDuplicate = async (viz: VisualizationResponse) => {
    // TODO: Implement duplicate
    console.log('Duplicate visualization:', viz.id);
  };

  const handleDelete = async (viz: VisualizationResponse) => {
    if (confirm(`Are you sure you want to delete "${viz.name}"?`)) {
      await deleteMutation.mutateAsync(viz.id);
    }
  };

  const handleRefresh = (viz: VisualizationResponse) => {
    // TODO: Implement refresh
    console.log('Refresh visualization:', viz.id);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-3xl font-bold">Visualizations</h1>
          <p className="text-muted-foreground">
            Create and manage your data visualizations
          </p>
        </div>
        <div className="flex items-center gap-2">
          {/* View Mode Toggle */}
          <div className="flex rounded-md border">
            <Button
              variant={viewMode === 'list' ? 'secondary' : 'ghost'}
              size="icon"
              onClick={() => setViewMode('list')}
              className="rounded-r-none"
            >
              <ListIcon className="h-4 w-4" />
            </Button>
            <Button
              variant={viewMode === 'grid' ? 'secondary' : 'ghost'}
              size="icon"
              onClick={() => setViewMode('grid')}
              className="rounded-l-none border-l"
            >
              <Grid className="h-4 w-4" />
            </Button>
          </div>
          <Button onClick={handleCreate}>
            <Plus className="mr-2 h-4 w-4" />
            Create Visualization
          </Button>
        </div>
      </div>

      {/* Visualizations Grid/List */}
      {isLoading ? (
        <div className="flex items-center justify-center h-96">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      ) : data?.items && data.items.length > 0 ? (
        <div
          className={
            viewMode === 'grid'
              ? 'grid gap-6 md:grid-cols-2'
              : 'flex flex-col gap-4'
          }
        >
          {data.items.map((viz) => (
            <ChartContainer
              key={viz.id}
              id={viz.id}
              title={viz.name}
              description={viz.description}
              chartType={viz.chart_type}
              data={viz.chart_data ? [viz.chart_data] : []}
              config={viz.config}
              showActions
              onEdit={() => handleEdit(viz)}
              onDuplicate={() => handleDuplicate(viz)}
              onDelete={() => handleDelete(viz)}
              onRefresh={() => handleRefresh(viz)}
            />
          ))}
        </div>
      ) : (
        <Card>
          <CardHeader>
            <CardTitle>No visualizations yet</CardTitle>
            <CardDescription>
              Get started by creating your first visualization
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <div className="rounded-full bg-muted p-6 mb-4">
                <svg
                  className="h-12 w-12 text-muted-foreground"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
                  />
                </svg>
              </div>
              <h3 className="text-lg font-semibold mb-2">Create Your First Chart</h3>
              <p className="text-muted-foreground mb-4 max-w-md">
                Transform your data into beautiful, interactive visualizations with our
                easy-to-use chart builder.
              </p>
              <Button onClick={handleCreate}>
                <Plus className="mr-2 h-4 w-4" />
                Create Visualization
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
