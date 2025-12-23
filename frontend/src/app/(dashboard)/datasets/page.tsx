/**
 * Datasets Page
 *
 * Main page for viewing and managing datasets
 */

'use client';

import { useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { SortingState } from '@tanstack/react-table';
import { Upload, Grid, List, Search, Filter } from 'lucide-react';
import { useDatasets, useDeleteDataset } from '@/lib/hooks/useDatasets';
import { DatasetFilters, DatasetPagination } from '@/lib/api/datasets';
import { DatasetResponse } from '@/types/api';
import { useWebSocket } from '@/lib/hooks/useWebSocket';
import { DatasetList } from '@/components/datasets/DatasetList';
import { DatasetCard } from '@/components/datasets/DatasetCard';
import { DatasetUploadForm } from '@/components/forms/DatasetUploadForm';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

type ViewMode = 'table' | 'grid';

export default function DatasetsPage() {
  const router = useRouter();
  const [viewMode, setViewMode] = useState<ViewMode>('table');
  const [search, setSearch] = useState('');
  const [filters, setFilters] = useState<DatasetFilters>({});
  const [pagination, setPagination] = useState<DatasetPagination>({
    page: 1,
    page_size: 20,
  });
  const [sorting, setSorting] = useState<SortingState>([]);
  const [uploadModalOpen, setUploadModalOpen] = useState(false);

  // Fetch datasets
  const { data, isLoading, refetch } = useDatasets(
    { ...filters, search },
    pagination
  );

  // WebSocket for real-time dataset updates
  const handleDatasetUpdate = useCallback(() => {
    // Refetch datasets when any dataset is updated
    refetch();
  }, [refetch]);

  useWebSocket(handleDatasetUpdate, {
    channels: ['datasets'],
    autoReconnect: true,
  });

  // Delete mutation
  const deleteMutation = useDeleteDataset({
    onSuccess: () => {
      // Show success message (you can add a toast here)
      console.log('Dataset deleted successfully');
    },
  });

  const handleView = (dataset: DatasetResponse) => {
    router.push(`/datasets/${dataset.id}`);
  };

  const handleEdit = (dataset: DatasetResponse) => {
    router.push(`/datasets/${dataset.id}/edit`);
  };

  const handleDelete = async (dataset: DatasetResponse) => {
    if (confirm(`Are you sure you want to delete "${dataset.name}"?`)) {
      await deleteMutation.mutateAsync(dataset.id);
    }
  };

  const handleDownload = (dataset: DatasetResponse) => {
    // TODO: Implement download
    console.log('Download dataset:', dataset.id);
  };

  const handleUpload = () => {
    setUploadModalOpen(true);
  };

  const handleUploadSuccess = () => {
    setUploadModalOpen(false);
  };

  const handleUploadCancel = () => {
    setUploadModalOpen(false);
  };

  const handleFilterChange = (status?: string) => {
    setFilters({
      ...filters,
      status: status as DatasetFilters['status'],
    });
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-3xl font-bold">Datasets</h1>
          <p className="text-muted-foreground">
            Manage and analyze your data files
          </p>
        </div>
        <Button onClick={handleUpload}>
          <Upload className="mr-2 h-4 w-4" />
          Upload Dataset
        </Button>
      </div>

      {/* Filters and Controls */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        {/* Search */}
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search datasets..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>

        {/* Controls */}
        <div className="flex items-center gap-2">
          {/* Filter Dropdown */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="icon">
                <Filter className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuLabel>Filter by status</DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={() => handleFilterChange(undefined)}>
                All
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => handleFilterChange('ready')}>
                Ready
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => handleFilterChange('processing')}>
                Processing
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => handleFilterChange('error')}>
                Error
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>

          {/* View Mode Toggle */}
          <div className="flex rounded-md border">
            <Button
              variant={viewMode === 'table' ? 'secondary' : 'ghost'}
              size="icon"
              onClick={() => setViewMode('table')}
              className="rounded-r-none"
            >
              <List className="h-4 w-4" />
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
        </div>
      </div>

      {/* Dataset List/Grid */}
      {viewMode === 'table' ? (
        <DatasetList
          datasets={data?.items ?? []}
          isLoading={isLoading}
          sorting={sorting}
          onSortingChange={setSorting}
          onView={handleView}
          onEdit={handleEdit}
          onDelete={handleDelete}
          onDownload={handleDownload}
        />
      ) : (
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {isLoading ? (
            // Loading skeleton
            [...Array(6)].map((_, i) => (
              <div key={i} className="h-64 rounded-lg border bg-card" />
            ))
          ) : data?.items && data.items.length > 0 ? (
            data.items.map((dataset) => (
              <DatasetCard
                key={dataset.id}
                dataset={dataset}
                onView={handleView}
                onEdit={handleEdit}
                onDelete={handleDelete}
                onDownload={handleDownload}
              />
            ))
          ) : (
            <div className="col-span-full flex flex-col items-center justify-center py-12 text-center">
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
                    d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z"
                  />
                </svg>
              </div>
              <h3 className="text-lg font-semibold mb-2">No datasets found</h3>
              <p className="text-muted-foreground mb-4">
                Get started by uploading your first dataset
              </p>
              <Button onClick={handleUpload}>
                <Upload className="mr-2 h-4 w-4" />
                Upload Dataset
              </Button>
            </div>
          )}
        </div>
      )}

      {/* Pagination */}
      {data && data.total > pagination.page_size! && (
        <div className="flex items-center justify-between border-t pt-4">
          <div className="text-sm text-muted-foreground">
            Showing {((pagination.page! - 1) * pagination.page_size!) + 1} to{' '}
            {Math.min(pagination.page! * pagination.page_size!, data.total)} of{' '}
            {data.total} datasets
          </div>
          <div className="flex gap-2">
            <Button
              variant="outline"
              onClick={() =>
                setPagination({ ...pagination, page: pagination.page! - 1 })
              }
              disabled={pagination.page === 1}
            >
              Previous
            </Button>
            <Button
              variant="outline"
              onClick={() =>
                setPagination({ ...pagination, page: pagination.page! + 1 })
              }
              disabled={pagination.page! * pagination.page_size! >= data.total}
            >
              Next
            </Button>
          </div>
        </div>
      )}

      {/* Upload Modal */}
      <Dialog open={uploadModalOpen} onOpenChange={setUploadModalOpen}>
        <DialogContent className="sm:max-w-[600px]">
          <DialogHeader>
            <DialogTitle>Upload Dataset</DialogTitle>
            <DialogDescription>
              Upload a CSV, Excel, or JSON file to create a new dataset.
            </DialogDescription>
          </DialogHeader>
          <DatasetUploadForm
            onSuccess={handleUploadSuccess}
            onCancel={handleUploadCancel}
          />
        </DialogContent>
      </Dialog>
    </div>
  );
}
