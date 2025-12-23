/**
 * StatsCard Component
 *
 * Display key metrics with trends and sparklines
 */

'use client';

import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { cn } from '@/lib/utils/cn';

interface StatsCardProps {
  title: string;
  value: string | number;
  trend?: {
    value: number;
    isPositive: boolean;
  };
  icon?: React.ReactNode;
  description?: string;
  onClick?: () => void;
  className?: string;
}

export function StatsCard({
  title,
  value,
  trend,
  icon,
  description,
  onClick,
  className,
}: StatsCardProps) {
  const getTrendIcon = () => {
    if (!trend) return null;
    
    if (trend.value === 0) {
      return <Minus className="h-4 w-4 text-muted-foreground" />;
    }
    
    return trend.isPositive ? (
      <TrendingUp className="h-4 w-4 text-green-600" />
    ) : (
      <TrendingDown className="h-4 w-4 text-red-600" />
    );
  };

  const getTrendColor = () => {
    if (!trend || trend.value === 0) return 'text-muted-foreground';
    return trend.isPositive ? 'text-green-600' : 'text-red-600';
  };

  return (
    <Card
      className={cn(
        'transition-all hover:shadow-md',
        onClick && 'cursor-pointer',
        className
      )}
      onClick={onClick}
    >
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
        {icon && <div className="text-muted-foreground">{icon}</div>}
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        {trend && (
          <div className={cn('flex items-center gap-1 text-xs mt-1', getTrendColor())}>
            {getTrendIcon()}
            <span>
              {Math.abs(trend.value)}% from last period
            </span>
          </div>
        )}
        {description && (
          <p className="text-xs text-muted-foreground mt-1">{description}</p>
        )}
      </CardContent>
    </Card>
  );
}
