/**
 * RecentActivity Component
 *
 * Display recent datasets, visualizations, and insights
 */

'use client';

import { formatDistanceToNow } from 'date-fns';
import {
  Database,
  BarChart3,
  Lightbulb,
  Clock,
  ChevronRight,
} from 'lucide-react';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils/cn';

type ActivityType = 'dataset' | 'visualization' | 'insight';

interface Activity {
  id: string;
  type: ActivityType;
  title: string;
  subtitle?: string;
  timestamp: string;
  status?: string;
}

interface RecentActivityProps {
  activities: Activity[];
  onItemClick?: (activity: Activity) => void;
  maxItems?: number;
  className?: string;
}

export function RecentActivity({
  activities,
  onItemClick,
  maxItems = 10,
  className,
}: RecentActivityProps) {
  const getIcon = (type: ActivityType) => {
    switch (type) {
      case 'dataset':
        return <Database className="h-4 w-4" />;
      case 'visualization':
        return <BarChart3 className="h-4 w-4" />;
      case 'insight':
        return <Lightbulb className="h-4 w-4" />;
      default:
        return <Clock className="h-4 w-4" />;
    }
  };

  const getTypeColor = (type: ActivityType) => {
    switch (type) {
      case 'dataset':
        return 'bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300';
      case 'visualization':
        return 'bg-green-100 text-green-800 dark:bg-green-950 dark:text-green-300';
      case 'insight':
        return 'bg-purple-100 text-purple-800 dark:bg-purple-950 dark:text-purple-300';
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-300';
    }
  };

  const displayActivities = activities.slice(0, maxItems);

  if (activities.length === 0) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle>Recent Activity</CardTitle>
          <CardDescription>Your latest actions and updates</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <Clock className="h-12 w-12 text-muted-foreground mb-4" />
            <p className="text-sm text-muted-foreground">No recent activity</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle>Recent Activity</CardTitle>
        <CardDescription>Your latest actions and updates</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {displayActivities.map((activity) => (
            <div
              key={activity.id}
              className={cn(
                'flex items-center gap-3 p-3 rounded-lg border transition-colors',
                onItemClick && 'cursor-pointer hover:bg-accent'
              )}
              onClick={() => onItemClick?.(activity)}
            >
              <div className={cn('p-2 rounded-md', getTypeColor(activity.type))}>
                {getIcon(activity.type)}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <p className="text-sm font-medium truncate">{activity.title}</p>
                  {activity.status && (
                    <Badge variant="outline" className="text-xs">
                      {activity.status}
                    </Badge>
                  )}
                </div>
                {activity.subtitle && (
                  <p className="text-xs text-muted-foreground truncate">
                    {activity.subtitle}
                  </p>
                )}
                <p className="text-xs text-muted-foreground mt-1">
                  {formatDistanceToNow(new Date(activity.timestamp), {
                    addSuffix: true,
                  })}
                </p>
              </div>
              {onItemClick && (
                <ChevronRight className="h-4 w-4 text-muted-foreground shrink-0" />
              )}
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
