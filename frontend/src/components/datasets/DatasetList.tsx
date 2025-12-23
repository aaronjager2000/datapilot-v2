/**
 * Dataset List Component
 *
 * Table view for datasets with sorting, filtering, and pagination
 */

'use client';

import { useMemo } from 'react';
import { formatDistanceToNow } from 'date-fns';
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  flexRender,
  SortingState,
  ColumnDef,
  OnChangeFn,
} from '@tanstack/react-table';
import { ArrowUpDown, MoreVertical, Download, Edit, Trash2, Eye } from 'lucide-react';
import { DatasetResponse } from '@/types/api';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Skeleton } from '@/components/ui/skeleton';

interface DatasetListProps {
  datasets: DatasetResponse[];
  isLoading?: boolean;
  sorting?: SortingState;
  onSortingChange?: OnChangeFn<SortingState>;
  onView?: (dataset: DatasetResponse) => void;
  onEdit?: (dataset: DatasetResponse) => void;
  onDelete?: (dataset: DatasetResponse) => void;
  onDownload?: (dataset: DatasetResponse) => void;
}

const statusConfig = {
  pending: { variant: 'outline' as const, label: 'Pending' },
  processing: { variant: 'warning' as const, label: 'Processing' },
  ready: { variant: 'success' as const, label: 'Ready' },
  error: { variant: 'destructive' as const, label: 'Error' },
};

export function DatasetList({
  datasets,
  isLoading,
  sorting,
  onSortingChange,
  onView,
  onEdit,
  onDelete,
  onDownload,
}: DatasetListProps) {
  const columns = useMemo<ColumnDef<DatasetResponse>[]>(
    () => [
      {
        accessorKey: 'name',
        header: ({ column }) => {
          return (
            <Button
              variant="ghost"
              onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
            >
              Name
              <ArrowUpDown className="ml-2 h-4 w-4" />
            </Button>
          );
        },
        cell: ({ row }) => {
          const dataset = row.original;
          return (
            <div className="min-w-[200px]">
              <div
                className="font-medium cursor-pointer hover:text-primary"
                onClick={() => onView?.(dataset)}
              >
                {dataset.name}
              </div>
              {dataset.description && (
                <div className="text-sm text-muted-foreground line-clamp-1">
                  {dataset.description}
                </div>
              )}
            </div>
          );
        },
      },
      {
        accessorKey: 'status',
        header: 'Status',
        cell: ({ row }) => {
          const status = row.getValue('status') as string;
          const config = statusConfig[status as keyof typeof statusConfig] || statusConfig.pending;
          return <Badge variant={config.variant}>{config.label}</Badge>;
        },
      },
      {
        accessorKey: 'file_name',
        header: 'Type',
        cell: ({ row }) => {
          const fileName = row.getValue('file_name') as string;
          const fileExt = fileName?.split('.').pop()?.toUpperCase() ?? 'N/A';
          return (
            <span className="text-sm text-muted-foreground">
              {fileExt}
            </span>
          );
        },
      },
      {
        accessorKey: 'row_count',
        header: ({ column }) => {
          return (
            <Button
              variant="ghost"
              onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
            >
              Rows
              <ArrowUpDown className="ml-2 h-4 w-4" />
            </Button>
          );
        },
        cell: ({ row }) => {
          const count = row.getValue('row_count') as number;
          return <div className="text-right">{count?.toLocaleString() ?? 'N/A'}</div>;
        },
      },
      {
        accessorKey: 'column_count',
        header: 'Columns',
        cell: ({ row }) => {
          const count = row.getValue('column_count') as number;
          return <div className="text-right">{count?.toLocaleString() ?? 'N/A'}</div>;
        },
      },
      {
        accessorKey: 'created_at',
        header: ({ column }) => {
          return (
            <Button
              variant="ghost"
              onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
            >
              Created
              <ArrowUpDown className="ml-2 h-4 w-4" />
            </Button>
          );
        },
        cell: ({ row }) => {
          const date = row.getValue('created_at') as string;
          return (
            <div className="text-sm text-muted-foreground">
              {formatDistanceToNow(new Date(date))} ago
            </div>
          );
        },
      },
      {
        id: 'actions',
        cell: ({ row }) => {
          const dataset = row.original;
          return (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="icon">
                  <MoreVertical className="h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem onClick={() => onView?.(dataset)}>
                  <Eye className="mr-2 h-4 w-4" />
                  View Details
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => onEdit?.(dataset)}>
                  <Edit className="mr-2 h-4 w-4" />
                  Edit
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => onDownload?.(dataset)}>
                  <Download className="mr-2 h-4 w-4" />
                  Download
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem
                  onClick={() => onDelete?.(dataset)}
                  className="text-destructive"
                >
                  <Trash2 className="mr-2 h-4 w-4" />
                  Delete
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          );
        },
      },
    ],
    [onView, onEdit, onDelete, onDownload]
  );

  const table = useReactTable({
    data: datasets,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    state: {
      sorting,
    },
    onSortingChange,
    manualSorting: !!onSortingChange,
  });

  if (isLoading) {
    return (
      <div className="space-y-3">
        {[...Array(5)].map((_, i) => (
          <Skeleton key={i} className="h-16 w-full" />
        ))}
      </div>
    );
  }

  if (datasets.length === 0) {
    return (
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
              d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z"
            />
          </svg>
        </div>
        <h3 className="text-lg font-semibold mb-2">No datasets found</h3>
        <p className="text-muted-foreground mb-4">
          Get started by uploading your first dataset
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-md border">
      <Table>
        <TableHeader>
          {table.getHeaderGroups().map((headerGroup) => (
            <TableRow key={headerGroup.id}>
              {headerGroup.headers.map((header) => (
                <TableHead key={header.id}>
                  {header.isPlaceholder
                    ? null
                    : flexRender(
                        header.column.columnDef.header,
                        header.getContext()
                      )}
                </TableHead>
              ))}
            </TableRow>
          ))}
        </TableHeader>
        <TableBody>
          {table.getRowModel().rows.map((row) => (
            <TableRow key={row.id}>
              {row.getVisibleCells().map((cell) => (
                <TableCell key={cell.id}>
                  {flexRender(cell.column.columnDef.cell, cell.getContext())}
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
