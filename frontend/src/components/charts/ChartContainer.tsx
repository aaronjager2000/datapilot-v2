/**
 * ChartContainer Component
 *
 * Wrapper component that handles chart rendering, actions, and export
 */

'use client';

import { useRef, useState } from 'react';
import html2canvas from 'html2canvas';
import {
  MoreVertical,
  Download,
  Copy,
  RefreshCw,
  Edit,
  Trash2,
  Share2,
} from 'lucide-react';
import { ChartType, ChartConfig } from '@/types/api';
import { LineChart } from './LineChart';
import { BarChart } from './BarChart';
import { PieChart } from './PieChart';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { cn } from '@/lib/utils/cn';

interface ChartContainerProps {
  id?: string;
  title: string;
  description?: string;
  chartType: ChartType;
  data: Record<string, unknown>[];
  config: ChartConfig;
  isLoading?: boolean;
  error?: string | null;
  theme?: 'light' | 'dark';
  showActions?: boolean;
  onEdit?: () => void;
  onDuplicate?: () => void;
  onDelete?: () => void;
  onRefresh?: () => void;
  onShare?: () => void;
  className?: string;
}

export function ChartContainer({
  id,
  title,
  description,
  chartType,
  data,
  config,
  isLoading = false,
  error = null,
  theme = 'light',
  showActions = true,
  onEdit,
  onDuplicate,
  onDelete,
  onRefresh,
  onShare,
  className,
}: ChartContainerProps) {
  const chartRef = useRef<HTMLDivElement>(null);
  const [isExporting, setIsExporting] = useState(false);

  const handleExportPNG = async () => {
    if (!chartRef.current) return;

    try {
      setIsExporting(true);
      const canvas = await html2canvas(chartRef.current, {
        backgroundColor: theme === 'dark' ? '#0f172a' : '#ffffff',
        scale: 2,
      });

      const link = document.createElement('a');
      link.download = `${title.replace(/\s+/g, '-').toLowerCase()}.png`;
      link.href = canvas.toDataURL();
      link.click();
    } catch (err) {
      console.error('Failed to export chart:', err);
    } finally {
      setIsExporting(false);
    }
  };

  const handleExportCSV = () => {
    if (!data || data.length === 0) return;

    // Convert data to CSV
    const keys = Object.keys(data[0]);
    const csv = [
      keys.join(','),
      ...data.map((row) =>
        keys.map((key) => JSON.stringify(row[key] ?? '')).join(',')
      ),
    ].join('\n');

    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.download = `${title.replace(/\s+/g, '-').toLowerCase()}.csv`;
    link.href = url;
    link.click();
    URL.revokeObjectURL(url);
  };

  const renderChart = () => {
    const chartProps = {
      data,
      config,
      isLoading,
      error,
      theme,
    };

    switch (chartType) {
      case ChartType.LINE:
        return <LineChart {...chartProps} />;
      case ChartType.BAR:
        return <BarChart {...chartProps} />;
      case ChartType.PIE:
        return <PieChart {...chartProps} />;
      case ChartType.SCATTER:
        // TODO: Implement scatter chart
        return (
          <div className="flex items-center justify-center h-96">
            <p className="text-muted-foreground">Scatter chart coming soon</p>
          </div>
        );
      case ChartType.HEATMAP:
        // TODO: Implement heatmap
        return (
          <div className="flex items-center justify-center h-96">
            <p className="text-muted-foreground">Heatmap coming soon</p>
          </div>
        );
      case ChartType.TABLE:
        // TODO: Implement table view
        return (
          <div className="flex items-center justify-center h-96">
            <p className="text-muted-foreground">Table view coming soon</p>
          </div>
        );
      default:
        return (
          <div className="flex items-center justify-center h-96">
            <p className="text-muted-foreground">Unsupported chart type</p>
          </div>
        );
    }
  };

  return (
    <Card className={cn('overflow-hidden', className)}>
      <CardHeader className="flex flex-row items-start justify-between space-y-0 pb-4">
        <div className="space-y-1">
          <CardTitle>{title}</CardTitle>
          {description && <CardDescription>{description}</CardDescription>}
        </div>

        {showActions && (
          <div className="flex items-center gap-2">
            {onRefresh && (
              <Button
                variant="ghost"
                size="icon"
                onClick={onRefresh}
                disabled={isLoading}
                title="Refresh data"
              >
                <RefreshCw className={cn('h-4 w-4', isLoading && 'animate-spin')} />
              </Button>
            )}

            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="icon">
                  <MoreVertical className="h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                {onEdit && (
                  <DropdownMenuItem onClick={onEdit}>
                    <Edit className="h-4 w-4 mr-2" />
                    Edit
                  </DropdownMenuItem>
                )}
                {onDuplicate && (
                  <DropdownMenuItem onClick={onDuplicate}>
                    <Copy className="h-4 w-4 mr-2" />
                    Duplicate
                  </DropdownMenuItem>
                )}
                {onShare && (
                  <DropdownMenuItem onClick={onShare}>
                    <Share2 className="h-4 w-4 mr-2" />
                    Share
                  </DropdownMenuItem>
                )}
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={handleExportPNG} disabled={isExporting}>
                  <Download className="h-4 w-4 mr-2" />
                  Export as PNG
                </DropdownMenuItem>
                <DropdownMenuItem onClick={handleExportCSV}>
                  <Download className="h-4 w-4 mr-2" />
                  Export as CSV
                </DropdownMenuItem>
                {onDelete && (
                  <>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem onClick={onDelete} className="text-destructive">
                      <Trash2 className="h-4 w-4 mr-2" />
                      Delete
                    </DropdownMenuItem>
                  </>
                )}
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        )}
      </CardHeader>

      <CardContent ref={chartRef}>{renderChart()}</CardContent>
    </Card>
  );
}
