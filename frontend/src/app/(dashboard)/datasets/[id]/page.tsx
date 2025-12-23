/**
 * Dataset Detail Page
 *
 * Displays dataset information with tabs for overview, preview, statistics, and insights
 */

'use client';

import { useState, useCallback } from 'react';
import { useRouter, useParams } from 'next/navigation';
import {
  FileText,
  Calendar,
  Database,
  Download,
  Trash2,
  Edit,
  RefreshCw,
  AlertCircle,
  CheckCircle2,
  Clock,
  Loader2,
  BarChart3,
  Table as TableIcon,
  Lightbulb,
  TrendingUp,
} from 'lucide-react';
import { format } from 'date-fns';
import {
  useDataset,
  useDatasetPreview,
  useDatasetStats,
  useDeleteDataset,
  useReprocessDataset,
} from '@/lib/hooks/useDatasets';
import { useDatasetWebSocket } from '@/lib/hooks/useWebSocket';
import { DatasetPreview } from '@/components/datasets/DatasetPreview';
import { NaturalLanguageQuery } from '@/components/query/NaturalLanguageQuery';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from '@/components/ui/tabs';
import { cn } from '@/lib/utils/cn';

export default function DatasetDetailPage() {
  const router = useRouter();
  const params = useParams();
  const datasetId = params.id as string;
  const [activeTab, setActiveTab] = useState('overview');

  // Fetch dataset data
  const { data: dataset, isLoading, refetch: refetchDataset } = useDataset(datasetId);
  const { data: preview } = useDatasetPreview(datasetId, 100);
  const { data: stats } = useDatasetStats(datasetId);

  // WebSocket for real-time updates
  const handleDatasetUpdate = useCallback(
    (data: unknown) => {
      const update = data as { dataset_id: string; status: string; type: string };
      if (update.dataset_id === datasetId) {
        // Refetch dataset data when status changes
        refetchDataset();
      }
    },
    [datasetId, refetchDataset]
  );

  const { isConnected } = useDatasetWebSocket(datasetId, handleDatasetUpdate);

  // Mutations
  const deleteMutation = useDeleteDataset({
    onSuccess: () => {
      router.push('/datasets');
    },
  });

  const reprocessMutation = useReprocessDataset({
    onSuccess: () => {
      console.log('Dataset reprocessing started');
    },
  });

  const handleDelete = async () => {
    if (
      confirm(
        `Are you sure you want to delete "${dataset?.name}"? This action cannot be undone.`
      )
    ) {
      await deleteMutation.mutateAsync(datasetId);
    }
  };

  const handleReprocess = async () => {
    await reprocessMutation.mutateAsync(datasetId);
  };

  const handleDownload = () => {
    // TODO: Implement download
    console.log('Download dataset:', datasetId);
  };

  const handleEdit = () => {
    router.push(`/datasets/${datasetId}/edit`);
  };

  const getStatusBadge = (status: string) => {
    const statusConfig = {
      ready: { variant: 'success' as const, icon: CheckCircle2, label: 'Ready' },
      processing: { variant: 'warning' as const, icon: Clock, label: 'Processing' },
      error: { variant: 'destructive' as const, icon: AlertCircle, label: 'Error' },
      pending: { variant: 'secondary' as const, icon: Clock, label: 'Pending' },
    };

    const config = statusConfig[status as keyof typeof statusConfig] || statusConfig.pending;
    const Icon = config.icon;

    return (
      <Badge variant={config.variant} className="flex items-center gap-1 w-fit">
        <Icon className="h-3 w-3" />
        {config.label}
      </Badge>
    );
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!dataset) {
    return (
      <div className="flex flex-col items-center justify-center h-96 gap-4">
        <AlertCircle className="h-12 w-12 text-muted-foreground" />
        <div className="text-center">
          <h2 className="text-2xl font-bold">Dataset not found</h2>
          <p className="text-muted-foreground mt-2">
            The dataset you&apos;re looking for doesn&apos;t exist or has been deleted.
          </p>
          <Button onClick={() => router.push('/datasets')} className="mt-4">
            Back to Datasets
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
        <div className="space-y-1">
          <div className="flex items-center gap-3">
            <h1 className="text-3xl font-bold">{dataset.name}</h1>
            {getStatusBadge(dataset.status)}
            {isConnected && dataset.status === 'processing' && (
              <Badge variant="outline" className="text-green-600 dark:text-green-400">
                ● Live Updates
              </Badge>
            )}
          </div>
          {dataset.description && (
            <p className="text-muted-foreground">{dataset.description}</p>
          )}
          <div className="flex items-center gap-4 text-sm text-muted-foreground mt-2">
            <div className="flex items-center gap-1">
              <FileText className="h-4 w-4" />
              {dataset.file_name}
            </div>
            <div className="flex items-center gap-1">
              <Calendar className="h-4 w-4" />
              {format(new Date(dataset.created_at), 'MMM d, yyyy')}
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={handleEdit}>
            <Edit className="h-4 w-4 mr-2" />
            Edit
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={handleReprocess}
            disabled={reprocessMutation.isPending}
          >
            <RefreshCw
              className={cn('h-4 w-4 mr-2', reprocessMutation.isPending && 'animate-spin')}
            />
            Reprocess
          </Button>
          <Button variant="outline" size="sm" onClick={handleDownload}>
            <Download className="h-4 w-4 mr-2" />
            Download
          </Button>
          <Button
            variant="destructive"
            size="sm"
            onClick={handleDelete}
            disabled={deleteMutation.isPending}
          >
            <Trash2 className="h-4 w-4 mr-2" />
            Delete
          </Button>
        </div>
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
        <TabsList>
          <TabsTrigger value="overview">
            <Database className="h-4 w-4 mr-2" />
            Overview
          </TabsTrigger>
          <TabsTrigger value="preview">
            <TableIcon className="h-4 w-4 mr-2" />
            Data Preview
          </TabsTrigger>
          <TabsTrigger value="statistics">
            <BarChart3 className="h-4 w-4 mr-2" />
            Statistics
          </TabsTrigger>
          <TabsTrigger value="insights">
            <Lightbulb className="h-4 w-4 mr-2" />
            Insights
          </TabsTrigger>
        </TabsList>

        {/* Tab 1: Overview */}
        <TabsContent value="overview" className="space-y-6">
          {/* Stats Cards */}
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Total Rows</CardTitle>
                <Database className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {dataset.row_count?.toLocaleString() || 'N/A'}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Total Columns</CardTitle>
                <TableIcon className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {dataset.column_count || dataset.columns?.length || 'N/A'}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">File Size</CardTitle>
                <FileText className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {dataset.file_size_mb.toFixed(2)} MB
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Status</CardTitle>
                <TrendingUp className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold capitalize">{dataset.status}</div>
              </CardContent>
            </Card>
          </div>

          {/* Metadata */}
          <Card>
            <CardHeader>
              <CardTitle>Metadata</CardTitle>
              <CardDescription>Dataset information and properties</CardDescription>
            </CardHeader>
            <CardContent>
              <dl className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <dt className="text-sm font-medium text-muted-foreground">Name</dt>
                  <dd className="text-sm mt-1">{dataset.name}</dd>
                </div>
                <div>
                  <dt className="text-sm font-medium text-muted-foreground">File Name</dt>
                  <dd className="text-sm mt-1">{dataset.file_name}</dd>
                </div>
                <div>
                  <dt className="text-sm font-medium text-muted-foreground">Created At</dt>
                  <dd className="text-sm mt-1">
                    {format(new Date(dataset.created_at), 'PPpp')}
                  </dd>
                </div>
                <div>
                  <dt className="text-sm font-medium text-muted-foreground">Updated At</dt>
                  <dd className="text-sm mt-1">
                    {format(new Date(dataset.updated_at), 'PPpp')}
                  </dd>
                </div>
                <div>
                  <dt className="text-sm font-medium text-muted-foreground">File Hash</dt>
                  <dd className="text-sm mt-1 font-mono break-all">
                    {dataset.file_hash}
                  </dd>
                </div>
                <div>
                  <dt className="text-sm font-medium text-muted-foreground">Organization ID</dt>
                  <dd className="text-sm mt-1 font-mono">{dataset.organization_id}</dd>
                </div>
              </dl>
            </CardContent>
          </Card>

          {/* Schema Table */}
          {dataset.columns && dataset.columns.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Schema</CardTitle>
                <CardDescription>
                  Column structure and data types ({dataset.columns.length} columns)
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Column Name</TableHead>
                      <TableHead>Type</TableHead>
                      <TableHead>Nullable</TableHead>
                      <TableHead className="text-right">Unique Values</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {dataset.columns.map((column, index) => (
                      <TableRow key={index}>
                        <TableCell className="font-medium">{column}</TableCell>
                        <TableCell>
                          <Badge variant="outline">String</Badge>
                        </TableCell>
                        <TableCell>Yes</TableCell>
                        <TableCell className="text-right">-</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          )}

          {/* Error Message */}
          {dataset.processing_error && (
            <Card className="border-destructive">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-destructive">
                  <AlertCircle className="h-5 w-5" />
                  Processing Error
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground">
                  {dataset.processing_error}
                </p>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* Tab 2: Data Preview */}
        <TabsContent value="preview" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Data Preview</CardTitle>
              <CardDescription>
                Sample data from the dataset with type information and highlighting
              </CardDescription>
            </CardHeader>
            <CardContent>
              {preview ? (
                <DatasetPreview data={preview} showRowNumbers maxHeight="600px" />
              ) : (
                <div className="flex flex-col items-center justify-center py-12 text-center">
                  <Database className="h-12 w-12 text-muted-foreground mb-4" />
                  <p className="text-muted-foreground">Loading preview...</p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Tab 3: Statistics */}
        <TabsContent value="statistics" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Statistical Analysis</CardTitle>
              <CardDescription>
                Column-level statistics and data quality metrics
              </CardDescription>
            </CardHeader>
            <CardContent>
              {stats ? (
                <div className="space-y-6">
                  <div className="grid gap-4 md:grid-cols-2">
                    <div>
                      <div className="text-sm font-medium text-muted-foreground mb-1">
                        Total Rows
                      </div>
                      <div className="text-2xl font-bold">
                        {stats.total_rows?.toLocaleString() || 'N/A'}
                      </div>
                    </div>
                    <div>
                      <div className="text-sm font-medium text-muted-foreground mb-1">
                        Total Columns
                      </div>
                      <div className="text-2xl font-bold">
                        {stats.total_columns || 'N/A'}
                      </div>
                    </div>
                  </div>

                  {Object.keys(stats.column_stats || {}).length > 0 ? (
                    <div className="space-y-4">
                      <h4 className="font-semibold">Column Statistics</h4>
                      <div className="grid gap-4">
                        {Object.entries(stats.column_stats).map(([column, columnStats]) => (
                          <Card key={column}>
                            <CardHeader>
                              <CardTitle className="text-base">{column}</CardTitle>
                            </CardHeader>
                            <CardContent>
                              <pre className="text-xs overflow-auto">
                                {JSON.stringify(columnStats, null, 2)}
                              </pre>
                            </CardContent>
                          </Card>
                        ))}
                      </div>
                    </div>
                  ) : (
                    <p className="text-muted-foreground text-center py-8">
                      No detailed column statistics available
                    </p>
                  )}
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center py-12 text-center">
                  <BarChart3 className="h-12 w-12 text-muted-foreground mb-4" />
                  <p className="text-muted-foreground">
                    Statistics are being calculated...
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Tab 4: Insights */}
        <TabsContent value="insights" className="space-y-4">
          {/* Natural Language Query */}
          <NaturalLanguageQuery
            datasetId={datasetId}
            datasetName={dataset.name}
            onVisualizationSuggested={(suggestion) => {
              console.log('Visualization suggested:', suggestion);
              // TODO: Navigate to visualization builder with suggestion
            }}
          />

          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>AI-Generated Insights</CardTitle>
                  <CardDescription>
                    Discover patterns and anomalies in your data
                  </CardDescription>
                </div>
                <Button>
                  <TrendingUp className="h-4 w-4 mr-2" />
                  Generate Insights
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <div className="flex flex-col items-center justify-center py-12 text-center">
                <Lightbulb className="h-12 w-12 text-muted-foreground mb-4" />
                <h3 className="text-lg font-semibold mb-2">No insights yet</h3>
                <p className="text-muted-foreground mb-4">
                  Generate AI insights to discover patterns, anomalies, and recommendations
                  for your dataset.
                </p>
                <Button variant="outline">
                  <TrendingUp className="h-4 w-4 mr-2" />
                  Generate Your First Insight
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
