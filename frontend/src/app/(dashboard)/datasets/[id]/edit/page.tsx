/**
 * Dataset Edit Page
 *
 * Edit dataset metadata
 */

'use client';

import { useState } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { ArrowLeft, Loader2 } from 'lucide-react';
import { useDataset, useUpdateDataset } from '@/lib/hooks/useDatasets';
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

// Validation Schema
const editSchema = z.object({
  name: z.string().min(1, 'Name is required').max(255, 'Name is too long'),
  description: z.string().max(1000, 'Description is too long').optional(),
});

type EditFormData = z.infer<typeof editSchema>;

export default function DatasetEditPage() {
  const router = useRouter();
  const params = useParams();
  const datasetId = params.id as string;
  const [error, setError] = useState<string | null>(null);

  // Fetch dataset data
  const { data: dataset, isLoading } = useDataset(datasetId);

  // Update mutation
  const updateMutation = useUpdateDataset({
    onSuccess: () => {
      router.push(`/datasets/${datasetId}`);
    },
    onError: (err) => {
      setError(err.detail || 'Failed to update dataset');
    },
  });

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<EditFormData>({
    resolver: zodResolver(editSchema),
    defaultValues: {
      name: dataset?.name || '',
      description: dataset?.description || '',
    },
    values: dataset
      ? {
          name: dataset.name,
          description: dataset.description || '',
        }
      : undefined,
  });

  const onSubmit = async (data: EditFormData) => {
    setError(null);
    await updateMutation.mutateAsync({
      id: datasetId,
      updates: {
        name: data.name,
        description: data.description || undefined,
      },
    });
  };

  const handleCancel = () => {
    router.push(`/datasets/${datasetId}`);
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
        <div className="text-center">
          <h2 className="text-2xl font-bold">Dataset not found</h2>
          <p className="text-muted-foreground mt-2">
            The dataset you&apos;re trying to edit doesn&apos;t exist.
          </p>
          <Button onClick={() => router.push('/datasets')} className="mt-4">
            Back to Datasets
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-2xl">
      {/* Header */}
      <div>
        <Button
          variant="ghost"
          size="sm"
          onClick={handleCancel}
          className="mb-4"
        >
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Dataset
        </Button>
        <h1 className="text-3xl font-bold">Edit Dataset</h1>
        <p className="text-muted-foreground mt-1">
          Update dataset name and description
        </p>
      </div>

      {/* Edit Form */}
      <Card>
        <CardHeader>
          <CardTitle>Dataset Information</CardTitle>
          <CardDescription>
            Modify the metadata for &quot;{dataset.name}&quot;
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            {/* Name Field */}
            <div className="space-y-2">
              <Label htmlFor="name">Dataset Name *</Label>
              <Input
                id="name"
                placeholder="My Dataset"
                {...register('name')}
                disabled={updateMutation.isPending}
                aria-invalid={errors.name ? 'true' : 'false'}
              />
              {errors.name && (
                <p className="text-sm text-destructive">{errors.name.message}</p>
              )}
            </div>

            {/* Description Field */}
            <div className="space-y-2">
              <Label htmlFor="description">Description</Label>
              <textarea
                id="description"
                placeholder="Add a description for this dataset..."
                {...register('description')}
                disabled={updateMutation.isPending}
                rows={4}
                className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
              />
              {errors.description && (
                <p className="text-sm text-destructive">
                  {errors.description.message}
                </p>
              )}
            </div>

            {/* Error Message */}
            {error && (
              <div className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">
                {error}
              </div>
            )}

            {/* Form Actions */}
            <div className="flex gap-3 justify-end pt-4">
              <Button
                type="button"
                variant="outline"
                onClick={handleCancel}
                disabled={updateMutation.isPending}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={updateMutation.isPending}>
                {updateMutation.isPending ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Saving...
                  </>
                ) : (
                  'Save Changes'
                )}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
