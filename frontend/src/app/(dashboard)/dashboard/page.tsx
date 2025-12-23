/**
 * Dashboard Page
 *
 * Main dashboard with draggable/resizable widgets
 */

'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  Edit,
  Plus,
  Database,
  BarChart3,
  FileText,
  Upload,
  TrendingUp,
  Users,
} from 'lucide-react';
import { useDatasets } from '@/lib/hooks/useDatasets';
import { useVisualizations } from '@/lib/hooks/useVisualizations';
import { StatsCard } from '@/components/dashboard/StatsCard';
import { RecentActivity } from '@/components/dashboard/RecentActivity';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';

export default function DashboardPage() {
  const router = useRouter();
  const [isEditMode, setIsEditMode] = useState(false);

  // Fetch data
  const { data: datasetsData } = useDatasets({}, { page: 1, page_size: 5 });
  const { data: visualizationsData } = useVisualizations({}, { page: 1, page_size: 5 });

  // Prepare activity data
  const recentActivities = [
    ...(datasetsData?.items.map((d) => ({
      id: d.id,
      type: 'dataset' as const,
      title: d.name,
      subtitle: `${d.row_count?.toLocaleString()} rows`,
      timestamp: d.created_at,
      status: d.status,
    })) || []),
    ...(visualizationsData?.items.map((v) => ({
      id: v.id,
      type: 'visualization' as const,
      title: v.name,
      subtitle: v.chart_type,
      timestamp: v.created_at,
    })) || []),
  ].sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());

  const handleActivityClick = (activity: { id: string; type: string }) => {
    if (activity.type === 'dataset') {
      router.push(`/datasets/${activity.id}`);
    } else if (activity.type === 'visualization') {
      router.push(`/visualizations/${activity.id}`);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-3xl font-bold">Dashboard</h1>
          <p className="text-muted-foreground">
            Welcome back! Here&apos;s what&apos;s happening with your data.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={() => setIsEditMode(!isEditMode)}>
            <Edit className="mr-2 h-4 w-4" />
            Customize
          </Button>
        </div>
      </div>

      {/* Stats Cards Row */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {/* Stats Cards */}
        <div>
          <StatsCard
            title="Total Datasets"
            value={datasetsData?.total || 0}
            trend={{ value: 12, isPositive: true }}
            icon={<Database className="h-4 w-4" />}
            description="Uploaded datasets"
            onClick={() => router.push('/datasets')}
          />
        </div>

        <div>
          <StatsCard
            title="Visualizations"
            value={visualizationsData?.total || 0}
            trend={{ value: 8, isPositive: true }}
            icon={<BarChart3 className="h-4 w-4" />}
            description="Created charts"
            onClick={() => router.push('/visualizations')}
          />
        </div>

        <div>
          <StatsCard
            title="AI Insights"
            value={0}
            trend={{ value: 0, isPositive: true }}
            icon={<TrendingUp className="h-4 w-4" />}
            description="Generated insights"
            onClick={() => router.push('/insights')}
          />
        </div>

        <div>
          <StatsCard
            title="Team Members"
            value={1}
            icon={<Users className="h-4 w-4" />}
            description="Active users"
            onClick={() => router.push('/team')}
          />
        </div>
      </div>

      {/* Main Content Row */}
      <div className="grid gap-6 lg:grid-cols-3">
        {/* Quick Actions */}
        <div>
          <Card className="h-full">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Plus className="h-5 w-5" />
                Quick Actions
              </CardTitle>
              <CardDescription>Get started with common tasks</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-3">
                <Button
                  variant="outline"
                  className="justify-start h-auto py-4"
                  onClick={() => router.push('/datasets')}
                >
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-md bg-blue-100 dark:bg-blue-950">
                      <Upload className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                    </div>
                    <div className="text-left">
                      <p className="font-medium">Upload Dataset</p>
                      <p className="text-xs text-muted-foreground">
                        Add new data files
                      </p>
                    </div>
                  </div>
                </Button>

                <Button
                  variant="outline"
                  className="justify-start h-auto py-4"
                  onClick={() => router.push('/visualizations/new')}
                >
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-md bg-green-100 dark:bg-green-950">
                      <BarChart3 className="h-5 w-5 text-green-600 dark:text-green-400" />
                    </div>
                    <div className="text-left">
                      <p className="font-medium">Create Visualization</p>
                      <p className="text-xs text-muted-foreground">
                        Build new charts
                      </p>
                    </div>
                  </div>
                </Button>

                <Button
                  variant="outline"
                  className="justify-start h-auto py-4"
                  onClick={() => router.push('/insights')}
                >
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-md bg-purple-100 dark:bg-purple-950">
                      <TrendingUp className="h-5 w-5 text-purple-600 dark:text-purple-400" />
                    </div>
                    <div className="text-left">
                      <p className="font-medium">Generate Insights</p>
                      <p className="text-xs text-muted-foreground">
                        AI-powered analysis
                      </p>
                    </div>
                  </div>
                </Button>

                <Button
                  variant="outline"
                  className="justify-start h-auto py-4"
                  onClick={() => router.push('/settings')}
                >
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-md bg-orange-100 dark:bg-orange-950">
                      <FileText className="h-5 w-5 text-orange-600 dark:text-orange-400" />
                    </div>
                    <div className="text-left">
                      <p className="font-medium">View Documentation</p>
                      <p className="text-xs text-muted-foreground">
                        Learn more
                      </p>
                    </div>
                  </div>
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Recent Activity */}
        <div className="lg:col-span-2">
          <RecentActivity
            activities={recentActivities}
            onItemClick={handleActivityClick}
            maxItems={5}
          />
        </div>
      </div>
    </div>
  );
}
