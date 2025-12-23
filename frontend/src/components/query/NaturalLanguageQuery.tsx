/**
 * NaturalLanguageQuery Component
 *
 * Ask questions about datasets in natural language
 */

"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import {
  MessageSquare,
  Send,
  Loader2,
  Sparkles,
  Save,
  BarChart3,
  CheckCircle2,
} from "lucide-react";
import { askQuestion, saveQueryAsInsight, NLQueryResponse } from "@/lib/api/nlq";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { ChartSuggestion } from "@/types/api";

interface NaturalLanguageQueryProps {
  datasetId: string;
  datasetName?: string;
  onVisualizationSuggested?: (suggestion: ChartSuggestion) => void;
  className?: string;
}

export function NaturalLanguageQuery({
  datasetId,
  datasetName,
  onVisualizationSuggested,
  className,
}: NaturalLanguageQueryProps) {
  const [question, setQuestion] = useState("");
  const [response, setResponse] = useState<NLQueryResponse | null>(null);
  const [saved, setSaved] = useState(false);

  const queryMutation = useMutation({
    mutationFn: askQuestion,
    onSuccess: (data) => {
      setResponse(data);
      setSaved(false);
    },
  });

  const saveMutation = useMutation({
    mutationFn: () =>
      saveQueryAsInsight(
        datasetId,
        question,
        response?.answer || "",
        response?.supporting_data
      ),
    onSuccess: () => {
      setSaved(true);
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (question.trim()) {
      queryMutation.mutate({
        dataset_id: datasetId,
        question: question.trim(),
        include_visualization: true,
      });
    }
  };

  const handleSaveAsInsight = () => {
    if (response) {
      saveMutation.mutate();
    }
  };

  const handleUseVisualization = () => {
    if (response?.visualization_suggestion) {
      onVisualizationSuggested?.(response.visualization_suggestion);
    }
  };

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <MessageSquare className="h-5 w-5" />
          Ask About Your Data
        </CardTitle>
        <CardDescription>
          {datasetName
            ? `Ask questions about "${datasetName}" in natural language`
            : "Ask questions about your dataset in natural language"}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Query Input */}
        <form onSubmit={handleSubmit} className="flex gap-2">
          <Input
            placeholder="e.g., What are the top 5 values in column X?"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            disabled={queryMutation.isPending}
            className="flex-1"
          />
          <Button
            type="submit"
            disabled={!question.trim() || queryMutation.isPending}
          >
            {queryMutation.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <>
                <Send className="h-4 w-4 mr-2" />
                Ask
              </>
            )}
          </Button>
        </form>

        {/* Loading State */}
        {queryMutation.isPending && (
          <div className="flex items-center justify-center py-8">
            <div className="text-center space-y-3">
              <Loader2 className="h-8 w-8 animate-spin text-primary mx-auto" />
              <p className="text-sm text-muted-foreground">
                Analyzing your data...
              </p>
            </div>
          </div>
        )}

        {/* Error State */}
        {queryMutation.isError && (
          <div className="rounded-lg bg-destructive/10 p-4 text-sm text-destructive">
            <p className="font-medium">Failed to process question</p>
            <p className="text-xs mt-1">
              {(queryMutation.error as { detail?: string })?.detail ||
                "Please try again or rephrase your question."}
            </p>
          </div>
        )}

        {/* Response */}
        {response && !queryMutation.isPending && (
          <div className="space-y-4">
            <div className="rounded-lg border bg-muted/50 p-4">
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-2">
                  <Sparkles className="h-4 w-4 text-primary" />
                  <span className="text-sm font-medium">Answer</span>
                </div>
                <Badge variant="outline" className="font-mono text-xs">
                  {Math.round(response.confidence * 100)}% confidence
                </Badge>
              </div>
              <p className="text-sm leading-relaxed">{response.answer}</p>

              {/* Execution Time */}
              {response.execution_time_ms && (
                <p className="text-xs text-muted-foreground mt-3">
                  Executed in {response.execution_time_ms}ms
                </p>
              )}
            </div>

            {/* Supporting Data */}
            {response.supporting_data && (
              <div className="rounded-lg border p-4">
                <h4 className="text-sm font-medium mb-2">Supporting Data</h4>
                <pre className="text-xs overflow-auto max-h-48 bg-muted p-2 rounded">
                  {JSON.stringify(response.supporting_data, null, 2)}
                </pre>
              </div>
            )}

            {/* SQL Query */}
            {response.sql_query && (
              <details className="rounded-lg border p-4">
                <summary className="text-sm font-medium cursor-pointer">
                  View SQL Query
                </summary>
                <pre className="text-xs overflow-auto max-h-32 bg-muted p-2 rounded mt-2">
                  {response.sql_query}
                </pre>
              </details>
            )}

            {/* Visualization Suggestion */}
            {response.visualization_suggestion && (
              <div className="rounded-lg border border-primary/20 bg-primary/5 p-4">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <BarChart3 className="h-4 w-4 text-primary" />
                      <h4 className="text-sm font-medium">
                        Visualization Suggested
                      </h4>
                    </div>
                    <p className="text-sm text-muted-foreground">
                      {response.visualization_suggestion.title}
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">
                      {response.visualization_suggestion.reasoning}
                    </p>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleUseVisualization}
                  >
                    Create Chart
                  </Button>
                </div>
              </div>
            )}

            {/* Actions */}
            <div className="flex justify-end gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={handleSaveAsInsight}
                disabled={saveMutation.isPending || saved}
              >
                {saved ? (
                  <>
                    <CheckCircle2 className="h-4 w-4 mr-2 text-green-600" />
                    Saved
                  </>
                ) : saveMutation.isPending ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Saving...
                  </>
                ) : (
                  <>
                    <Save className="h-4 w-4 mr-2" />
                    Save as Insight
                  </>
                )}
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setQuestion("");
                  setResponse(null);
                  setSaved(false);
                }}
              >
                Ask Another Question
              </Button>
            </div>
          </div>
        )}

        {/* Suggestions */}
        {!response && !queryMutation.isPending && (
          <div className="space-y-2">
            <p className="text-xs text-muted-foreground">Try asking:</p>
            <div className="flex flex-wrap gap-2">
              {[
                "What are the top 10 values?",
                "Show me the average by category",
                "Are there any outliers?",
                "What trends do you see?",
              ].map((suggestion) => (
                <Button
                  key={suggestion}
                  variant="outline"
                  size="sm"
                  onClick={() => setQuestion(suggestion)}
                  className="text-xs h-7"
                >
                  {suggestion}
                </Button>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
