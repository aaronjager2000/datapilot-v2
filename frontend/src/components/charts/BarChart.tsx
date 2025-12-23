/**
 * BarChart Component
 *
 * Responsive bar chart using Recharts
 */

'use client';

import {
  BarChart as RechartsBarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { Loader2 } from 'lucide-react';
import { ChartConfig } from '@/types/api';

interface BarChartProps {
  data: Record<string, unknown>[];
  config: ChartConfig;
  isLoading?: boolean;
  error?: string | null;
  theme?: 'light' | 'dark';
}

export function BarChart({
  data,
  config,
  isLoading = false,
  error = null,
  theme = 'light',
}: BarChartProps) {
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <p className="text-destructive font-medium">Error loading chart</p>
          <p className="text-sm text-muted-foreground mt-1">{error}</p>
        </div>
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <p className="text-muted-foreground">No data available</p>
        </div>
      </div>
    );
  }

  const isDark = theme === 'dark';
  const textColor = isDark ? '#94a3b8' : '#64748b';
  const gridColor = isDark ? '#334155' : '#e2e8f0';

  // Get y-axis fields (can be single or array)
  const yAxisFields = Array.isArray(config.y_axis)
    ? config.y_axis
    : config.y_axis
    ? [config.y_axis]
    : [];

  // Default colors
  const defaultColors = [
    '#3b82f6',
    '#10b981',
    '#f59e0b',
    '#ef4444',
    '#8b5cf6',
    '#ec4899',
    '#06b6d4',
    '#84cc16',
  ];

  const colors = config.colors || defaultColors;

  return (
    <ResponsiveContainer width="100%" height={400}>
      <RechartsBarChart data={data} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
        <XAxis
          dataKey={config.x_axis || 'x'}
          stroke={textColor}
          style={{ fontSize: '12px' }}
        />
        <YAxis stroke={textColor} style={{ fontSize: '12px' }} />
        <Tooltip
          contentStyle={{
            backgroundColor: isDark ? '#1e293b' : '#ffffff',
            border: `1px solid ${gridColor}`,
            borderRadius: '6px',
            color: textColor,
          }}
        />
        <Legend />
        {yAxisFields.map((field, index) => (
          <Bar
            key={field}
            dataKey={field}
            fill={colors[index % colors.length]}
            radius={[4, 4, 0, 0]}
          />
        ))}
      </RechartsBarChart>
    </ResponsiveContainer>
  );
}
