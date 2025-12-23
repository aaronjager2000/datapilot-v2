/**
 * Insights Page
 *
 * View and manage AI-generated insights
 */

'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  Lightbulb,
  TrendingUp,
  AlertTriangle,
  BarChart3,
  Zap,
  Eye,
  X,
  Plus,
  Filter,
  Search,
  Loader2,
  Sparkles,
} from 'lucide-react';
import { format } from 'date-fns';
import { useInsights, useDismissInsight, useGenerateInsights } from '@/lib/hooks/useInsights';
import { useDatasets } from '@/lib/hooks/useDatasets';
import { InsightType } from '@/types/api';
import { NaturalLanguageQuery } from '@/components/query/NaturalLanguageQuery';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { cn } from '@/lib/utils/cn';

const INSIGHT_TYPES: { value: InsightType; label: string; icon: React.ComponentType<{ className?: string }> }[] = [
  { value: 'trend', label: 'Trend', icon: TrendingUp },
  { value: 'anomaly', label: 'Anomaly', icon: AlertTriangle },
  { value: 'correlation', label: 'Correlation', icon: BarChart3 },
  { value: 'distribution', label: 'Distribution', icon: Sparkles },
  { value: 'outlier', label: 'Outlier', icon: Zap },
  { value: 'pattern', label: 'Pattern', icon: Lightbulb },
  { value: 'recommendation', label: 'Recommendation', icon: Plus },
];

// #region agent log
if (typeof window !== 'undefined') {
  fetch('http://127.0.0.1:7242/ingest/5e4385f0-2486-4cd2-a67c-6474b9a29e18',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'insights/page.tsx:66',message:'INSIGHT_TYPES array values',data:{types:INSIGHT_TYPES.map(t=>({value:t.value,valueType:typeof t.value,valueLength:t.value?.length}))},timestamp:Date.now(),sessionId:'debug-session',hypothesisId:'H2'})}).catch(()=>{});
}
// #endregion

export default function InsightsPage() {
  const router = useRouter();
  const [search, setSearch] = useState('');
  const [selectedDataset, setSelectedDataset] = useState<string>('');
  const [selectedType, setSelectedType] = useState<string>('');
  const [minConfidence, setMinConfidence] = useState<string>('');
  const [sortBy, setSortBy] = useState<'confidence' | 'created_at'>('confidence');
  const [generateModalOpen, setGenerateModalOpen] = useState(false);
  const [selectedDatasetForGeneration, setSelectedDatasetForGeneration] = useState<string>('');

  // #region agent log
  React.useEffect(() => {
    fetch('http://127.0.0.1:7242/ingest/5e4385f0-2486-4cd2-a67c-6474b9a29e18',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'insights/page.tsx:76',message:'State values changed',data:{selectedDataset,selectedDatasetType:typeof selectedDataset,selectedDatasetIsEmpty:selectedDataset==='',selectedType,selectedTypeType:typeof selectedType,selectedTypeIsEmpty:selectedType==='',minConfidence,minConfidenceType:typeof minConfidence,minConfidenceIsEmpty:minConfidence===''},timestamp:Date.now(),sessionId:'debug-session',hypothesisId:'H3'})}).catch(()=>{});
  }, [selectedDataset, selectedType, minConfidence]);
  // #endregion

  // Fetch insights
  const { data, isLoading } = useInsights(
    {
      search: search || undefined,
      dataset_id: selectedDataset || undefined,
      insight_type: selectedType || undefined,
      min_confidence: minConfidence ? parseFloat(minConfidence) : undefined,
      is_dismissed: false,
    },
    {
      page: 1,
      page_size: 50,
      sort_by: sortBy,
      sort_order: 'desc',
    }
  );

  // Fetch datasets for filter
  const { data: datasetsData } = useDatasets({}, { page: 1, page_size: 100 });

  // #region agent log
  React.useEffect(() => {
    fetch('http://127.0.0.1:7242/ingest/5e4385f0-2486-4cd2-a67c-6474b9a29e18',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'insights/page.tsx:97',message:'Datasets data fetched',data:{datasetsCount:datasetsData?.items?.length||0,datasetIds:datasetsData?.items?.map(d=>({id:d.id,name:d.name,idType:typeof d.id,idLength:d.id?.length}))},timestamp:Date.now(),sessionId:'debug-session',hypothesisId:'H1'})}).catch(()=>{});
  }, [datasetsData]);
  // #endregion

  // Mutations
  const dismissMutation = useDismissInsight({
    onSuccess: () => {
      console.log('Insight dismissed');
    },
  });

  const generateMutation = useGenerateInsights({
    onSuccess: () => {
      setGenerateModalOpen(false);
      // TODO: Show generation progress
      console.log('Insights generation started');
    },
  });

  const getInsightIcon = (type: InsightType) => {
    const insight = INSIGHT_TYPES.find((t) => t.value === type);
    return insight?.icon || Lightbulb;
  };

  const getInsightColor = (type: InsightType) => {
    const colors: Record<InsightType, string> = {
      trend: 'bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300',
      anomaly: 'bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300',
      correlation: 'bg-green-100 text-green-800 dark:bg-green-950 dark:text-green-300',
      distribution: 'bg-purple-100 text-purple-800 dark:bg-purple-950 dark:text-purple-300',
      outlier: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-950 dark:text-yellow-300',
      pattern: 'bg-indigo-100 text-indigo-800 dark:bg-indigo-950 dark:text-indigo-300',
      recommendation: 'bg-orange-100 text-orange-800 dark:bg-orange-950 dark:text-orange-300',
    };
    return colors[type] || colors.pattern;
  };

  const getConfidenceBadge = (confidence: number) => {
    const percentage = Math.round(confidence * 100);
    let variant: 'default' | 'secondary' | 'success' = 'secondary';
    
    if (percentage >= 80) variant = 'success';
    else if (percentage >= 60) variant = 'default';
    
    return (
      <Badge variant={variant} className="font-mono">
        {percentage}% confidence
      </Badge>
    );
  };

  const handleDismiss = async (insightId: string) => {
    await dismissMutation.mutateAsync(insightId);
  };

  const handleGenerateInsights = async () => {
    if (selectedDatasetForGeneration) {
      await generateMutation.mutateAsync({
        dataset_id: selectedDatasetForGeneration,
        min_confidence: 0.5,
      });
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-3xl font-bold">AI Insights</h1>
          <p className="text-muted-foreground">
            Discover patterns and trends in your data
          </p>
        </div>
        <Button onClick={() => setGenerateModalOpen(true)}>
          <Sparkles className="mr-2 h-4 w-4" />
          Generate Insights
        </Button>
      </div>

      {/* Natural Language Query */}
      {selectedDataset && (
        <NaturalLanguageQuery
          datasetId={selectedDataset}
          datasetName={
            datasetsData?.items.find((d) => d.id === selectedDataset)?.name
          }
          onVisualizationSuggested={(suggestion) => {
            console.log('Visualization suggested:', suggestion);
            router.push('/visualizations/new');
          }}
        />
      )}

      {/* Filters */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Filter className="h-4 w-4" />
            Filters
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-5">
            {/* Search */}
            <div className="relative">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Search insights..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-9"
              />
            </div>

            {/* Dataset Filter */}
            <Select value={selectedDataset || undefined} onValueChange={(value) => setSelectedDataset(value || '')}>
              <SelectTrigger>
                <SelectValue placeholder="All Datasets" />
              </SelectTrigger>
              <SelectContent>
                {datasetsData?.items.map((dataset) => (
                  <SelectItem key={dataset.id} value={dataset.id}>
                    {dataset.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            {/* Type Filter */}
            <Select value={selectedType || undefined} onValueChange={(value) => setSelectedType(value || '')}>
              <SelectTrigger>
                <SelectValue placeholder="All Types" />
              </SelectTrigger>
              <SelectContent>
                {INSIGHT_TYPES.map((type) => (
                  <SelectItem key={type.value} value={type.value}>
                    {type.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            {/* Confidence Filter */}
            <Select value={minConfidence || undefined} onValueChange={(value) => setMinConfidence(value || '')}>
              <SelectTrigger>
                <SelectValue placeholder="Min Confidence" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="0.8">80%+</SelectItem>
                <SelectItem value="0.6">60%+</SelectItem>
                <SelectItem value="0.4">40%+</SelectItem>
              </SelectContent>
            </Select>

            {/* Sort By */}
            <Select value={sortBy} onValueChange={(value: 'confidence' | 'created_at') => setSortBy(value)}>
              <SelectTrigger>
                <SelectValue placeholder="Sort By" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="confidence">Confidence</SelectItem>
                <SelectItem value="created_at">Date</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Insights List */}
      {isLoading ? (
        <div className="flex items-center justify-center h-96">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      ) : data?.items && data.items.length > 0 ? (
        <div className="grid gap-4 md:grid-cols-2">
          {data.items.map((insight) => {
            const Icon = getInsightIcon(insight.insight_type);
            return (
              <Card key={insight.id} className="hover:shadow-md transition-shadow">
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div className="flex items-start gap-3 flex-1">
                      <div className={cn('p-2 rounded-md', getInsightColor(insight.insight_type))}>
                        <Icon className="h-5 w-5" />
                      </div>
                      <div className="space-y-1 flex-1">
                        <CardTitle className="text-lg">{insight.title}</CardTitle>
                        <div className="flex items-center gap-2 flex-wrap">
                          <Badge variant="outline" className="text-xs">
                            {insight.insight_type}
                          </Badge>
                          {getConfidenceBadge(insight.confidence)}
                        </div>
                      </div>
                    </div>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => handleDismiss(insight.id)}
                      disabled={dismissMutation.isPending}
                    >
                      <X className="h-4 w-4" />
                    </Button>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  <CardDescription className="text-sm">
                    {insight.description}
                  </CardDescription>

                  {insight.dataset_name && (
                    <div className="text-xs text-muted-foreground">
                      Dataset: <span className="font-medium">{insight.dataset_name}</span>
                    </div>
                  )}

                  <div className="flex items-center justify-between pt-2 border-t">
                    <span className="text-xs text-muted-foreground">
                      {format(new Date(insight.created_at), 'MMM d, yyyy')}
                    </span>
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => router.push(`/insights/${insight.id}`)}
                      >
                        <Eye className="h-3 w-3 mr-1" />
                        View Details
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => {
                          // TODO: Add to dashboard
                          console.log('Add to dashboard:', insight.id);
                        }}
                      >
                        <Plus className="h-3 w-3 mr-1" />
                        Add to Dashboard
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      ) : (
        <Card>
          <CardContent className="py-12">
            <div className="flex flex-col items-center justify-center text-center">
              <Lightbulb className="h-12 w-12 text-muted-foreground mb-4" />
              <h3 className="text-lg font-semibold mb-2">No insights yet</h3>
              <p className="text-muted-foreground mb-4 max-w-md">
                Generate AI-powered insights from your datasets to discover patterns,
                trends, and anomalies automatically.
              </p>
              <Button onClick={() => setGenerateModalOpen(true)}>
                <Sparkles className="mr-2 h-4 w-4" />
                Generate Your First Insight
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Generate Insights Modal */}
      <Dialog open={generateModalOpen} onOpenChange={setGenerateModalOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Generate AI Insights</DialogTitle>
            <DialogDescription>
              Select a dataset to analyze and generate insights
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Select Dataset</label>
              <Select
                value={selectedDatasetForGeneration}
                onValueChange={setSelectedDatasetForGeneration}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Choose a dataset" />
                </SelectTrigger>
                <SelectContent>
                  {datasetsData?.items.map((dataset) => (
                    <SelectItem key={dataset.id} value={dataset.id}>
                      {dataset.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="flex justify-end gap-2">
              <Button
                variant="outline"
                onClick={() => setGenerateModalOpen(false)}
                disabled={generateMutation.isPending}
              >
                Cancel
              </Button>
              <Button
                onClick={handleGenerateInsights}
                disabled={!selectedDatasetForGeneration || generateMutation.isPending}
              >
                {generateMutation.isPending ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Generating...
                  </>
                ) : (
                  <>
                    <Sparkles className="mr-2 h-4 w-4" />
                    Generate Insights
                  </>
                )}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
