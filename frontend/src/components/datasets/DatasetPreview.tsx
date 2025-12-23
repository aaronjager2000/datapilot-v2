/**
 * DatasetPreview Component
 *
 * Displays dataset data in a table format with type information and highlighting
 */

'use client';

import { useMemo } from 'react';
import { Database } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { cn } from '@/lib/utils/cn';

export interface DatasetPreviewData {
  columns: string[];
  rows: Record<string, unknown>[];
  total_rows: number;
  preview_rows: number;
}

interface DatasetPreviewProps {
  data: DatasetPreviewData;
  showRowNumbers?: boolean;
  maxHeight?: string;
}

export function DatasetPreview({
  data,
  showRowNumbers = true,
  maxHeight = '600px',
}: DatasetPreviewProps) {
  // Infer column types from data
  const columnTypes = useMemo(() => {
    const types: Record<string, string> = {};

    data.columns.forEach((column) => {
      // Sample first few non-null values to determine type
      const sampleValues = data.rows
        .slice(0, 10)
        .map((row) => row[column])
        .filter((val) => val !== null && val !== undefined);

      if (sampleValues.length === 0) {
        types[column] = 'unknown';
        return;
      }

      const firstValue = sampleValues[0];
      const type = typeof firstValue;

      if (type === 'number') {
        types[column] = Number.isInteger(firstValue) ? 'integer' : 'float';
      } else if (type === 'boolean') {
        types[column] = 'boolean';
      } else if (type === 'string') {
        // Check if it's a date-like string
        const strVal = String(firstValue);
        if (/^\d{4}-\d{2}-\d{2}/.test(strVal)) {
          types[column] = 'date';
        } else {
          types[column] = 'string';
        }
      } else {
        types[column] = 'object';
      }
    });

    return types;
  }, [data.columns, data.rows]);

  // Check if a value is an outlier (very basic heuristic)
  const isOutlier = (column: string, value: unknown): boolean => {
    if (value === null || value === undefined) return false;
    const columnType = columnTypes[column];

    if (columnType === 'integer' || columnType === 'float') {
      const numValues = data.rows
        .map((row) => row[column])
        .filter((v) => typeof v === 'number') as number[];

      if (numValues.length < 3) return false;

      const mean = numValues.reduce((a, b) => a + b, 0) / numValues.length;
      const stdDev = Math.sqrt(
        numValues.reduce((sq, n) => sq + Math.pow(n - mean, 2), 0) / numValues.length
      );

      const numValue = value as number;
      return Math.abs(numValue - mean) > 3 * stdDev;
    }

    return false;
  };

  const isNull = (value: unknown): boolean => {
    return value === null || value === undefined || value === '';
  };

  const formatValue = (value: unknown): string => {
    if (value === null || value === undefined) return '';
    if (typeof value === 'object') return JSON.stringify(value);
    return String(value);
  };

  const getTypeColor = (type: string): string => {
    const colors: Record<string, string> = {
      integer: 'bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300',
      float: 'bg-cyan-100 text-cyan-800 dark:bg-cyan-950 dark:text-cyan-300',
      string: 'bg-green-100 text-green-800 dark:bg-green-950 dark:text-green-300',
      boolean: 'bg-purple-100 text-purple-800 dark:bg-purple-950 dark:text-purple-300',
      date: 'bg-orange-100 text-orange-800 dark:bg-orange-950 dark:text-orange-300',
      object: 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-300',
      unknown: 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-300',
    };
    return colors[type] || colors.unknown;
  };

  if (!data.rows || data.rows.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <Database className="h-12 w-12 text-muted-foreground mb-4" />
        <p className="text-muted-foreground">No preview data available</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Info */}
      <div className="text-sm text-muted-foreground">
        Showing {data.preview_rows} of {data.total_rows.toLocaleString()} rows
      </div>

      {/* Table */}
      <div
        className="border rounded-lg overflow-auto"
        style={{ maxHeight }}
      >
        <Table>
          <TableHeader className="sticky top-0 bg-background z-10">
            <TableRow>
              {showRowNumbers && (
                <TableHead className="w-16 font-semibold">#</TableHead>
              )}
              {data.columns.map((column) => (
                <TableHead key={column} className="min-w-[120px]">
                  <div className="flex flex-col gap-1">
                    <span className="font-semibold">{column}</span>
                    <Badge
                      variant="outline"
                      className={cn('text-xs w-fit', getTypeColor(columnTypes[column]))}
                    >
                      {columnTypes[column]}
                    </Badge>
                  </div>
                </TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.rows.map((row, rowIndex) => (
              <TableRow key={rowIndex}>
                {showRowNumbers && (
                  <TableCell className="font-medium text-muted-foreground">
                    {rowIndex + 1}
                  </TableCell>
                )}
                {data.columns.map((column) => {
                  const value = row[column];
                  const isNullValue = isNull(value);
                  const isOutlierValue = !isNullValue && isOutlier(column, value);

                  return (
                    <TableCell
                      key={`${rowIndex}-${column}`}
                      className={cn(
                        'max-w-[300px] truncate',
                        isNullValue && 'bg-gray-100 dark:bg-gray-900 italic text-muted-foreground',
                        isOutlierValue && 'bg-yellow-50 dark:bg-yellow-950 font-semibold'
                      )}
                      title={formatValue(value)}
                    >
                      {isNullValue ? 'null' : formatValue(value)}
                    </TableCell>
                  );
                })}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      {/* Legend */}
      <div className="flex flex-wrap gap-4 text-sm text-muted-foreground">
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 bg-gray-100 dark:bg-gray-900 border rounded" />
          <span>Null values</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 bg-yellow-50 dark:bg-yellow-950 border rounded" />
          <span>Outliers</span>
        </div>
      </div>
    </div>
  );
}
