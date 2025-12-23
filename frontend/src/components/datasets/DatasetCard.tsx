/**
 * Dataset Card Component
 *
 * Card view for datasets in grid layout
 */

'use client';

import { formatDistanceToNow } from 'date-fns';
import { MoreVertical, Download, Edit, Trash2, Eye } from 'lucide-react';
import { DatasetResponse } from '@/types/api';
import { Card, CardContent, CardFooter, CardHeader } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Button } from '@/components/ui/button';

interface DatasetCardProps {
  dataset: DatasetResponse;
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

export function DatasetCard({
  dataset,
  onView,
  onEdit,
  onDelete,
  onDownload,
}: DatasetCardProps) {
  const statusInfo = statusConfig[dataset.status as keyof typeof statusConfig] || statusConfig.pending;

  return (
    <Card className="group relative overflow-hidden transition-shadow hover:shadow-lg">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1 min-w-0">
            <h3
              className="font-semibold truncate cursor-pointer hover:text-primary"
              onClick={() => onView?.(dataset)}
            >
              {dataset.name}
            </h3>
            {dataset.description && (
              <p className="text-sm text-muted-foreground line-clamp-2 mt-1">
                {dataset.description}
              </p>
            )}
          </div>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" className="h-8 w-8">
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
        </div>
      </CardHeader>

      <CardContent className="pb-3">
        <div className="flex items-center gap-2 flex-wrap">
          <Badge variant={statusInfo.variant}>{statusInfo.label}</Badge>
          <span className="text-xs text-muted-foreground">
            {dataset.file_name.split('.').pop()?.toUpperCase() ?? 'FILE'}
          </span>
        </div>

        <div className="mt-4 grid grid-cols-2 gap-4 text-sm">
          <div>
            <p className="text-muted-foreground">Rows</p>
            <p className="font-medium">
              {dataset.row_count?.toLocaleString() ?? 'N/A'}
            </p>
          </div>
          <div>
            <p className="text-muted-foreground">Columns</p>
            <p className="font-medium">
              {dataset.column_count?.toLocaleString() ?? 'N/A'}
            </p>
          </div>
        </div>
      </CardContent>

      <CardFooter className="border-t bg-muted/50 py-3">
        <div className="flex items-center justify-between w-full text-xs text-muted-foreground">
          <span>
            Created {formatDistanceToNow(new Date(dataset.created_at))} ago
          </span>
        </div>
      </CardFooter>
    </Card>
  );
}
