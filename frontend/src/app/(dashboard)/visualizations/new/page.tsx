/**
 * New Visualization Page
 *
 * Multi-step wizard for creating visualizations
 */

'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import {
  ArrowLeft,
  ArrowRight,
  Check,
  Database,
  BarChart3,
  Loader2,
} from 'lucide-react';
import { ChartType } from '@/types/api';
import { useDatasets, useDataset } from '@/lib/hooks/useDatasets';
import { useCreateVisualization } from '@/lib/hooks/useVisualizations';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
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
import { ChartContainer } from '@/components/charts/ChartContainer';
import { cn } from '@/lib/utils/cn';

// Validation Schema
const visualizationSchema = z.object({
  name: z.string().min(1, 'Name is required'),
  description: z.string().optional(),
  dataset_id: z.string().min(1, 'Dataset is required'),
  chart_type: z.nativeEnum(ChartType),
  x_axis: z.string().min(1, 'X axis is required'),
  y_axis: z.string().min(1, 'Y axis is required'),
  grouping: z.string().optional(),
  aggregation: z.enum(['sum', 'avg', 'count', 'min', 'max', 'median']).optional(),
});

type VisualizationFormData = z.infer<typeof visualizationSchema>;

const CHART_TYPES = [
  {
    type: ChartType.BAR,
    name: 'Bar Chart',
    description: 'Compare values across categories',
    icon: '📊',
  },
  {
    type: ChartType.LINE,
    name: 'Line Chart',
    description: 'Show trends over time',
    icon: '📈',
  },
  {
    type: ChartType.PIE,
    name: 'Pie Chart',
    description: 'Show proportions of a whole',
    icon: '🥧',
  },
  {
    type: ChartType.SCATTER,
    name: 'Scatter Plot',
    description: 'Show correlation between variables',
    icon: '⚡',
  },
];

export default function NewVisualizationPage() {
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [selectedDataset, setSelectedDataset] = useState<string>('');

  const { data: datasetsData, isLoading: datasetsLoading } = useDatasets(
    {},
    { page: 1, page_size: 100 }
  );

  // Fetch full dataset details to get columns
  const { data: datasetDetails } = useDataset(selectedDataset, {
    enabled: !!selectedDataset,
  });

  const createMutation = useCreateVisualization({
    onSuccess: (data) => {
      router.push(`/visualizations/${data.id}`);
    },
  });

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    formState: { errors },
  } = useForm<VisualizationFormData>({
    resolver: zodResolver(visualizationSchema),
    defaultValues: {
      aggregation: 'sum',
    },
  });

  const watchedValues = watch();

  const handleDatasetSelect = (datasetId: string) => {
    setSelectedDataset(datasetId);
    setValue('dataset_id', datasetId);
  };

  // Get columns from the fetched dataset details
  const datasetColumns = datasetDetails?.columns || [];

  const onSubmit = async (data: VisualizationFormData) => {
    await createMutation.mutateAsync({
      name: data.name,
      description: data.description,
      chart_type: data.chart_type,
      dataset_id: data.dataset_id,
      config: {
        x_axis: data.x_axis,
        y_axis: data.y_axis,
        grouping: data.grouping,
        aggregation: data.aggregation,
      },
    });
  };

  const renderStep = () => {
    switch (step) {
      case 1:
        return (
          <div className="space-y-4">
            <div>
              <h2 className="text-2xl font-bold mb-2">Select Dataset</h2>
              <p className="text-muted-foreground">
                Choose the dataset you want to visualize
              </p>
            </div>

            {datasetsLoading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
              </div>
            ) : datasetsData?.items && datasetsData.items.length > 0 ? (
              <div className="grid gap-4 md:grid-cols-2">
                {datasetsData.items.map((dataset) => (
                  <Card
                    key={dataset.id}
                    className={cn(
                      'cursor-pointer transition-all hover:border-primary',
                      selectedDataset === dataset.id && 'border-primary bg-primary/5'
                    )}
                    onClick={() => handleDatasetSelect(dataset.id)}
                  >
                    <CardHeader>
                      <div className="flex items-start justify-between">
                        <Database className="h-5 w-5 text-muted-foreground" />
                        {selectedDataset === dataset.id && (
                          <Check className="h-5 w-5 text-primary" />
                        )}
                      </div>
                      <CardTitle className="text-lg">{dataset.name}</CardTitle>
                      <CardDescription>
                        {dataset.row_count?.toLocaleString()} rows ·{' '}
                        {dataset.column_count} columns
                      </CardDescription>
                    </CardHeader>
                  </Card>
                ))}
              </div>
            ) : (
              <Card>
                <CardContent className="py-12 text-center">
                  <p className="text-muted-foreground">
                    No datasets available. Please upload a dataset first.
                  </p>
                  <Button
                    variant="outline"
                    className="mt-4"
                    onClick={() => router.push('/datasets')}
                  >
                    Go to Datasets
                  </Button>
                </CardContent>
              </Card>
            )}
          </div>
        );

      case 2:
        return (
          <div className="space-y-4">
            <div>
              <h2 className="text-2xl font-bold mb-2">Select Chart Type</h2>
              <p className="text-muted-foreground">
                Choose the type of visualization that best represents your data
              </p>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              {CHART_TYPES.map((chartType) => (
                <Card
                  key={chartType.type}
                  className={cn(
                    'cursor-pointer transition-all hover:border-primary',
                    watchedValues.chart_type === chartType.type &&
                      'border-primary bg-primary/5'
                  )}
                  onClick={() => setValue('chart_type', chartType.type)}
                >
                  <CardHeader>
                    <div className="flex items-start justify-between">
                      <div className="text-4xl">{chartType.icon}</div>
                      {watchedValues.chart_type === chartType.type && (
                        <Check className="h-5 w-5 text-primary" />
                      )}
                    </div>
                    <CardTitle className="text-lg">{chartType.name}</CardTitle>
                    <CardDescription>{chartType.description}</CardDescription>
                  </CardHeader>
                </Card>
              ))}
            </div>
          </div>
        );

      case 3:
        return (
          <div className="space-y-6">
            <div>
              <h2 className="text-2xl font-bold mb-2">Configure Chart</h2>
              <p className="text-muted-foreground">
                Select columns and configure how your data should be displayed
              </p>
            </div>

            <div className="space-y-4">
              {/* X Axis */}
              <div className="space-y-2">
                <Label htmlFor="x_axis">X Axis *</Label>
                <Input
                  id="x_axis"
                  placeholder="Enter column name (e.g., date, category)"
                  {...register('x_axis')}
                />
                {errors.x_axis && (
                  <p className="text-sm text-destructive">{errors.x_axis.message}</p>
                )}
                {datasetColumns.length > 0 && (
                  <p className="text-xs text-muted-foreground">
                    Available columns: {datasetColumns.join(', ')}
                  </p>
                )}
              </div>

              {/* Y Axis */}
              <div className="space-y-2">
                <Label htmlFor="y_axis">Y Axis *</Label>
                <Input
                  id="y_axis"
                  placeholder="Enter column name (e.g., sales, value)"
                  {...register('y_axis')}
                />
                {errors.y_axis && (
                  <p className="text-sm text-destructive">{errors.y_axis.message}</p>
                )}
                {datasetColumns.length > 0 && (
                  <p className="text-xs text-muted-foreground">
                    Available columns: {datasetColumns.join(', ')}
                  </p>
                )}
              </div>

              {/* Aggregation */}
              <div className="space-y-2">
                <Label htmlFor="aggregation">Aggregation</Label>
                <Select
                  value={watchedValues.aggregation}
                  onValueChange={(value: 'sum' | 'avg' | 'count' | 'min' | 'max' | 'median') => setValue('aggregation', value)}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select aggregation" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="sum">Sum</SelectItem>
                    <SelectItem value="avg">Average</SelectItem>
                    <SelectItem value="count">Count</SelectItem>
                    <SelectItem value="min">Minimum</SelectItem>
                    <SelectItem value="max">Maximum</SelectItem>
                    <SelectItem value="median">Median</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* Grouping (Optional) */}
              {datasetColumns.length > 0 && (
                <div className="space-y-2">
                  <Label htmlFor="grouping">Grouping (Optional)</Label>
                  <Select
                    value={watchedValues.grouping || undefined}
                    onValueChange={(value: string) => setValue('grouping', value || undefined)}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="None" />
                    </SelectTrigger>
                    <SelectContent>
                      {datasetColumns.map((column) => (
                        <SelectItem key={column} value={column}>
                          {column}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              )}
            </div>
          </div>
        );

      case 4:
        return (
          <div className="space-y-6">
            <div>
              <h2 className="text-2xl font-bold mb-2">Customize & Save</h2>
              <p className="text-muted-foreground">
                Add a title and description for your visualization
              </p>
            </div>

            <div className="space-y-4">
              {/* Name */}
              <div className="space-y-2">
                <Label htmlFor="name">Name *</Label>
                <Input
                  id="name"
                  placeholder="My Chart"
                  {...register('name')}
                />
                {errors.name && (
                  <p className="text-sm text-destructive">{errors.name.message}</p>
                )}
              </div>

              {/* Description */}
              <div className="space-y-2">
                <Label htmlFor="description">Description</Label>
                <textarea
                  id="description"
                  placeholder="Add a description..."
                  {...register('description')}
                  rows={3}
                  className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                />
              </div>
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  const canProceed = () => {
    switch (step) {
      case 1:
        return !!selectedDataset;
      case 2:
        return !!watchedValues.chart_type;
      case 3:
        return !!watchedValues.x_axis && !!watchedValues.y_axis;
      case 4:
        return !!watchedValues.name;
      default:
        return false;
    }
  };

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => (step === 1 ? router.push('/visualizations') : setStep(step - 1))}
        >
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back
        </Button>
        <div className="flex-1">
          <h1 className="text-3xl font-bold">Create Visualization</h1>
          <p className="text-muted-foreground">Step {step} of 4</p>
        </div>
      </div>

      {/* Progress */}
      <div className="flex gap-2">
        {[1, 2, 3, 4].map((s) => (
          <div
            key={s}
            className={cn(
              'flex-1 h-2 rounded-full transition-colors',
              s <= step ? 'bg-primary' : 'bg-muted'
            )}
          />
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Left: Form Steps */}
        <Card>
          <CardContent className="pt-6">{renderStep()}</CardContent>
        </Card>

        {/* Right: Preview */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BarChart3 className="h-5 w-5" />
              Preview
            </CardTitle>
            <CardDescription>
              See how your visualization will look
            </CardDescription>
          </CardHeader>
          <CardContent>
            {step >= 2 && watchedValues.chart_type ? (
              <div className="border rounded-lg p-4">
                <ChartContainer
                  title={watchedValues.name || 'Preview'}
                  description={watchedValues.description}
                  chartType={watchedValues.chart_type}
                  data={[]} // Mock data would go here
                  config={{
                    x_axis: watchedValues.x_axis,
                    y_axis: watchedValues.y_axis,
                    grouping: watchedValues.grouping,
                    aggregation: watchedValues.aggregation,
                  }}
                  showActions={false}
                />
              </div>
            ) : (
              <div className="flex items-center justify-center h-96 border rounded-lg">
                <p className="text-muted-foreground">
                  Select a chart type to see preview
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Actions */}
      <div className="flex justify-between">
        <Button
          variant="outline"
          onClick={() => setStep(step - 1)}
          disabled={step === 1}
        >
          <ArrowLeft className="h-4 w-4 mr-2" />
          Previous
        </Button>

        {step < 4 ? (
          <Button onClick={() => setStep(step + 1)} disabled={!canProceed()}>
            Next
            <ArrowRight className="h-4 w-4 ml-2" />
          </Button>
        ) : (
          <Button
            onClick={handleSubmit(onSubmit)}
            disabled={!canProceed() || createMutation.isPending}
          >
            {createMutation.isPending ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Creating...
              </>
            ) : (
              <>
                <Check className="h-4 w-4 mr-2" />
                Create Visualization
              </>
            )}
          </Button>
        )}
      </div>
    </div>
  );
}
