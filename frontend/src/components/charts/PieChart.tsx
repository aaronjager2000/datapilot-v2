/**
 * PieChart Component
 *
 * Responsive pie chart using Recharts
 */

'use client';

import {
  PieChart as RechartsPieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { Loader2 } from 'lucide-react';
import { ChartConfig } from '@/types/api';

interface PieChartProps {
  data: Record<string, unknown>[];
  config: ChartConfig;
  isLoading?: boolean;
  error?: string | null;
  theme?: 'light' | 'dark';
}

export function PieChart({
  data,
  config,
  isLoading = false,
  error = null,
  theme = 'light',
}: PieChartProps) {
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
    '#f97316',
    '#14b8a6',
  ];

  const colors = config.colors || defaultColors;

  // For pie charts, we need name and value fields
  const nameKey = config.x_axis || 'name';
  const valueKey = Array.isArray(config.y_axis)
    ? config.y_axis[0]
    : config.y_axis || 'value';

  return (
    <ResponsiveContainer width="100%" height={400}>
      <RechartsPieChart>
        <Pie
          data={data}
          dataKey={valueKey}
          nameKey={nameKey}
          cx="50%"
          cy="50%"
          outerRadius={120}
          // eslint-disable-next-line
          label={(entry: any) => {
            const name = entry[nameKey];
            const value = entry[valueKey];
            return `${name}: ${value}`;
          }}
          labelLine={{ stroke: textColor }}
        >
          {data.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={colors[index % colors.length]} />
          ))}
        </Pie>
        <Tooltip
          contentStyle={{
            backgroundColor: isDark ? '#1e293b' : '#ffffff',
            border: `1px solid ${isDark ? '#334155' : '#e2e8f0'}`,
            borderRadius: '6px',
            color: textColor,
          }}
        />
        <Legend />
      </RechartsPieChart>
    </ResponsiveContainer>
  );
}
