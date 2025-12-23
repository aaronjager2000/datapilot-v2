/**
 * Insight Detail Page
 *
 * View detailed information about a specific insight
 */

"use client";

import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, Lightbulb, Loader2, Trash2, BarChart3 } from "lucide-react";
import { format } from "date-fns";
import { useInsight, useDeleteInsight } from "@/lib/hooks/useInsights";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export default function InsightDetailPage() {
  const router = useRouter();
  const params = useParams();
  const insightId = params.id as string;

  const { data: insight, isLoading } = useInsight(insightId);

  const deleteMutation = useDeleteInsight({
    onSuccess: () => {
      router.push("/insights");
    },
  });

  const handleDelete = async () => {
    if (
      confirm(
        `Are you sure you want to delete this insight? This action cannot be undone.`
      )
    ) {
      await deleteMutation.mutateAsync(insightId);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!insight) {
    return (
      <div className="flex flex-col items-center justify-center h-96 gap-4">
        <Lightbulb className="h-12 w-12 text-muted-foreground" />
        <div className="text-center">
          <h2 className="text-2xl font-bold">Insight not found</h2>
          <p className="text-muted-foreground mt-2">
            The insight you&apos;re looking for doesn&apos;t exist.
          </p>
          <Button onClick={() => router.push("/insights")} className="mt-4">
            Back to Insights
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-4xl">
      {/* Header */}
      <div>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => router.push("/insights")}
          className="mb-4"
        >
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Insights
        </Button>
      </div>

      {/* Insight Card */}
      <Card>
        <CardHeader>
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-2">
                <Badge variant="outline" className="capitalize">
                  {insight.insight_type}
                </Badge>
                <Badge variant="default" className="font-mono">
                  {Math.round(insight.confidence * 100)}% confidence
                </Badge>
              </div>
              <CardTitle className="text-2xl">{insight.title}</CardTitle>
              <CardDescription className="mt-2">
                {format(new Date(insight.created_at), "PPpp")}
              </CardDescription>
            </div>
            <Button
              variant="destructive"
              size="sm"
              onClick={handleDelete}
              disabled={deleteMutation.isPending}
            >
              <Trash2 className="h-4 w-4 mr-2" />
              Delete
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Description */}
          <div>
            <h3 className="text-sm font-medium mb-2">Description</h3>
            <p className="text-sm text-muted-foreground leading-relaxed">
              {insight.description}
            </p>
          </div>

          {/* Dataset Info */}
          {insight.dataset_name && (
            <div>
              <h3 className="text-sm font-medium mb-2">Dataset</h3>
              <Button
                variant="outline"
                size="sm"
                onClick={() => router.push(`/datasets/${insight.dataset_id}`)}
              >
                <BarChart3 className="h-4 w-4 mr-2" />
                {insight.dataset_name}
              </Button>
            </div>
          )}

          {/* Supporting Data */}
          {insight.supporting_data && (
            <div>
              <h3 className="text-sm font-medium mb-2">Supporting Data</h3>
              <div className="rounded-lg border bg-muted/50 p-4">
                <pre className="text-xs overflow-auto max-h-96">
                  {JSON.stringify(insight.supporting_data, null, 2)}
                </pre>
              </div>
            </div>
          )}

          {/* Metadata */}
          <div className="border-t pt-6">
            <h3 className="text-sm font-medium mb-4">Metadata</h3>
            <dl className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <dt className="text-muted-foreground">Insight ID</dt>
                <dd className="font-mono mt-1">{insight.id}</dd>
              </div>
              <div>
                <dt className="text-muted-foreground">Created</dt>
                <dd className="mt-1">
                  {format(new Date(insight.created_at), "PPpp")}
                </dd>
              </div>
              <div>
                <dt className="text-muted-foreground">Updated</dt>
                <dd className="mt-1">
                  {format(new Date(insight.updated_at), "PPpp")}
                </dd>
              </div>
              <div>
                <dt className="text-muted-foreground">Dismissed</dt>
                <dd className="mt-1">{insight.is_dismissed ? "Yes" : "No"}</dd>
              </div>
            </dl>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
