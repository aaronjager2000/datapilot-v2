/**
 * Billing Page
 *
 * Subscription management and billing
 */

"use client";

import { useState } from "react";
import {
  CreditCard,
  TrendingUp,
  Download,
  Loader2,
  Check,
  ExternalLink,
  AlertCircle,
  Zap,
} from "lucide-react";
import { format } from "date-fns";
import {
  useCurrentSubscription,
  useUsageStats,
  usePlans,
  useBillingHistory,
  usePaymentMethods,
  useCreateCheckoutSession,
  useCreatePortalSession,
  useCancelSubscription,
  useResumeSubscription,
  useSetDefaultPaymentMethod,
  useRemovePaymentMethod,
} from "@/lib/hooks/useBilling";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Progress } from "@/components/ui/progress";
import { useToast } from "@/components/ui/toast";
import { cn } from "@/lib/utils/cn";

export default function BillingPage() {
  const { addToast } = useToast();
  const [billingPeriod, setBillingPeriod] = useState<"monthly" | "yearly">(
    "monthly"
  );
  const [cancelDialogOpen, setCancelDialogOpen] = useState(false);

  // Queries
  const { data: subscription, isLoading: subLoading } =
    useCurrentSubscription();
  const { data: usage } = useUsageStats();
  const { data: plans } = usePlans();
  const { data: history } = useBillingHistory();
  const { data: paymentMethods } = usePaymentMethods();

  // Mutations
  const createCheckoutMutation = useCreateCheckoutSession({
    onSuccess: (data) => {
      // Redirect to Stripe Checkout
      window.location.href = data.url;
    },
    onError: () => {
      addToast({
        type: "error",
        title: "Checkout failed",
        description: "Failed to create checkout session",
      });
    },
  });

  const createPortalMutation = useCreatePortalSession({
    onSuccess: (data) => {
      // Redirect to Stripe Portal
      window.location.href = data.url;
    },
  });

  const cancelMutation = useCancelSubscription({
    onSuccess: () => {
      addToast({
        type: "success",
        title: "Subscription canceled",
        description: "Your subscription will end at the current period",
      });
      setCancelDialogOpen(false);
    },
  });

  const resumeMutation = useResumeSubscription({
    onSuccess: () => {
      addToast({
        type: "success",
        title: "Subscription resumed",
        description: "Your subscription has been reactivated",
      });
    },
  });

  const setDefaultPaymentMutation = useSetDefaultPaymentMethod({
    onSuccess: () => {
      addToast({
        type: "success",
        title: "Default payment method updated",
        description: "Payment method has been set as default",
      });
    },
  });

  const removePaymentMutation = useRemovePaymentMethod({
    onSuccess: () => {
      addToast({
        type: "success",
        title: "Payment method removed",
        description: "Payment method has been deleted",
      });
    },
  });

  // Handlers
  const handleUpgrade = (planId: string) => {
    createCheckoutMutation.mutate({ planId, billingPeriod });
  };

  const handleManageBilling = () => {
    createPortalMutation.mutate();
  };

  const handleCancelSubscription = () => {
    cancelMutation.mutate();
  };

  const handleResumeSubscription = () => {
    resumeMutation.mutate();
  };

  const getUsagePercentage = (current: number, limit: number) => {
    return Math.min((current / limit) * 100, 100);
  };

  const getUsageColor = (percentage: number) => {
    if (percentage >= 90) return "text-red-600";
    if (percentage >= 75) return "text-yellow-600";
    return "text-green-600";
  };

  const getPlanBadgeColor = (tier: string) => {
    switch (tier) {
      case "free":
        return "bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-300";
      case "pro":
        return "bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300";
      case "enterprise":
        return "bg-purple-100 text-purple-800 dark:bg-purple-950 dark:text-purple-300";
      default:
        return "bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-300";
    }
  };

  if (subLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2">
            <CreditCard className="h-8 w-8" />
            Billing & Subscription
          </h1>
          <p className="text-muted-foreground">
            Manage your subscription and billing
          </p>
        </div>
        <Button
          variant="outline"
          onClick={handleManageBilling}
          disabled={createPortalMutation.isPending}
        >
          {createPortalMutation.isPending ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Loading...
            </>
          ) : (
            <>
              <ExternalLink className="mr-2 h-4 w-4" />
              Manage Billing
            </>
          )}
        </Button>
      </div>

      {/* Current Plan */}
      {subscription && (
        <Card>
          <CardHeader>
            <div className="flex items-start justify-between">
              <div>
                <CardTitle>Current Plan</CardTitle>
                <CardDescription>Your active subscription</CardDescription>
              </div>
              <Badge className={getPlanBadgeColor(subscription.tier)}>
                {subscription.plan_name}
              </Badge>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid md:grid-cols-3 gap-4">
              <div className="space-y-1">
                <p className="text-sm text-muted-foreground">Status</p>
                <p className="text-lg font-semibold capitalize">
                  {subscription.status}
                </p>
              </div>
              <div className="space-y-1">
                <p className="text-sm text-muted-foreground">Current Period</p>
                <p className="text-sm font-medium">
                  {format(new Date(subscription.current_period_start), "PP")} -{" "}
                  {format(new Date(subscription.current_period_end), "PP")}
                </p>
              </div>
              <div className="space-y-1">
                <p className="text-sm text-muted-foreground">Next Billing</p>
                <p className="text-sm font-medium">
                  {subscription.cancel_at_period_end ? (
                    <span className="text-destructive">
                      Cancels{" "}
                      {format(new Date(subscription.current_period_end), "PP")}
                    </span>
                  ) : (
                    format(new Date(subscription.current_period_end), "PP")
                  )}
                </p>
              </div>
            </div>

            {subscription.cancel_at_period_end ? (
              <div className="flex items-start gap-3 p-4 bg-yellow-50 dark:bg-yellow-950/20 border border-yellow-200 dark:border-yellow-900 rounded-lg">
                <AlertCircle className="h-5 w-5 text-yellow-600 dark:text-yellow-500 mt-0.5" />
                <div className="flex-1">
                  <p className="font-medium text-yellow-900 dark:text-yellow-100">
                    Subscription Scheduled for Cancellation
                  </p>
                  <p className="text-sm text-yellow-800 dark:text-yellow-200 mt-1">
                    Your subscription will end on{" "}
                    {format(new Date(subscription.current_period_end), "PPP")}.
                    You can resume it before then.
                  </p>
                  <Button
                    size="sm"
                    onClick={handleResumeSubscription}
                    disabled={resumeMutation.isPending}
                    className="mt-3"
                  >
                    Resume Subscription
                  </Button>
                </div>
              </div>
            ) : subscription.tier !== "free" ? (
              <Button
                variant="outline"
                size="sm"
                onClick={() => setCancelDialogOpen(true)}
                disabled={cancelMutation.isPending}
              >
                Cancel Subscription
              </Button>
            ) : null}
          </CardContent>
        </Card>
      )}

      {/* Usage Stats */}
      {usage && (
        <Card>
          <CardHeader>
            <CardTitle>Usage & Limits</CardTitle>
            <CardDescription>
              Current usage across your organization
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Users */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <p className="text-sm font-medium">Team Members</p>
                <p className="text-sm text-muted-foreground">
                  <span
                    className={getUsageColor(
                      getUsagePercentage(
                        usage.users.current,
                        usage.users.limit
                      )
                    )}
                  >
                    {usage.users.current}
                  </span>{" "}
                  / {usage.users.limit}
                </p>
              </div>
              <Progress
                value={getUsagePercentage(
                  usage.users.current,
                  usage.users.limit
                )}
              />
            </div>

            {/* Datasets */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <p className="text-sm font-medium">Datasets</p>
                <p className="text-sm text-muted-foreground">
                  <span
                    className={getUsageColor(
                      getUsagePercentage(
                        usage.datasets.current,
                        usage.datasets.limit
                      )
                    )}
                  >
                    {usage.datasets.current}
                  </span>{" "}
                  / {usage.datasets.limit}
                </p>
              </div>
              <Progress
                value={getUsagePercentage(
                  usage.datasets.current,
                  usage.datasets.limit
                )}
              />
            </div>

            {/* Storage */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <p className="text-sm font-medium">Storage</p>
                <p className="text-sm text-muted-foreground">
                  <span
                    className={getUsageColor(
                      getUsagePercentage(
                        usage.storage_gb.current,
                        usage.storage_gb.limit
                      )
                    )}
                  >
                    {usage.storage_gb.current.toFixed(2)} GB
                  </span>{" "}
                  / {usage.storage_gb.limit} GB
                </p>
              </div>
              <Progress
                value={getUsagePercentage(
                  usage.storage_gb.current,
                  usage.storage_gb.limit
                )}
              />
            </div>

            {/* API Calls */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <p className="text-sm font-medium">API Calls (This Month)</p>
                <p className="text-sm text-muted-foreground">
                  <span
                    className={getUsageColor(
                      getUsagePercentage(
                        usage.api_calls.current,
                        usage.api_calls.limit
                      )
                    )}
                  >
                    {usage.api_calls.current.toLocaleString()}
                  </span>{" "}
                  / {usage.api_calls.limit.toLocaleString()}
                </p>
              </div>
              <Progress
                value={getUsagePercentage(
                  usage.api_calls.current,
                  usage.api_calls.limit
                )}
              />
            </div>
          </CardContent>
        </Card>
      )}

      {/* Plan Comparison */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Available Plans</CardTitle>
              <CardDescription>Choose the plan that fits your needs</CardDescription>
            </div>
            <div className="flex gap-2 p-1 bg-muted rounded-lg">
              <Button
                variant={billingPeriod === "monthly" ? "default" : "ghost"}
                size="sm"
                onClick={() => setBillingPeriod("monthly")}
              >
                Monthly
              </Button>
              <Button
                variant={billingPeriod === "yearly" ? "default" : "ghost"}
                size="sm"
                onClick={() => setBillingPeriod("yearly")}
              >
                Yearly
                <Badge variant="success" className="ml-2 text-xs">
                  Save 20%
                </Badge>
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid md:grid-cols-3 gap-6">
            {plans?.map((plan) => {
              const price =
                billingPeriod === "monthly"
                  ? plan.price_monthly
                  : plan.price_yearly / 12;
              const isCurrentPlan = subscription?.tier === plan.tier;

              return (
                <Card
                  key={plan.id}
                  className={cn(
                    "relative",
                    isCurrentPlan && "border-primary border-2"
                  )}
                >
                  {isCurrentPlan && (
                    <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                      <Badge variant="default">Current Plan</Badge>
                    </div>
                  )}
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      {plan.tier === "enterprise" && (
                        <Zap className="h-5 w-5 text-purple-500" />
                      )}
                      {plan.name}
                    </CardTitle>
                    <div className="mt-4">
                      <span className="text-4xl font-bold">
                        ${price.toFixed(0)}
                      </span>
                      <span className="text-muted-foreground">/month</span>
                      {billingPeriod === "yearly" && (
                        <p className="text-sm text-muted-foreground mt-1">
                          Billed ${plan.price_yearly} yearly
                        </p>
                      )}
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <ul className="space-y-2">
                      {plan.features.map((feature, idx) => (
                        <li key={idx} className="flex items-start gap-2 text-sm">
                          <Check className="h-4 w-4 text-green-600 mt-0.5 shrink-0" />
                          <span>{feature}</span>
                        </li>
                      ))}
                    </ul>

                    <div className="pt-4 border-t space-y-1 text-sm text-muted-foreground">
                      <p>{plan.limits.max_users} team members</p>
                      <p>{plan.limits.max_datasets} datasets</p>
                      <p>{plan.limits.max_storage_gb} GB storage</p>
                      <p>
                        {plan.limits.max_api_calls_per_month.toLocaleString()}{" "}
                        API calls/month
                      </p>
                    </div>

                    <Button
                      className="w-full"
                      variant={isCurrentPlan ? "outline" : "default"}
                      onClick={() => !isCurrentPlan && handleUpgrade(plan.id)}
                      disabled={
                        isCurrentPlan || createCheckoutMutation.isPending
                      }
                    >
                      {isCurrentPlan ? (
                        "Current Plan"
                      ) : createCheckoutMutation.isPending ? (
                        <>
                          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                          Processing...
                        </>
                      ) : (
                        <>
                          <TrendingUp className="mr-2 h-4 w-4" />
                          Upgrade to {plan.name}
                        </>
                      )}
                    </Button>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* Billing History */}
      {history && history.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Billing History</CardTitle>
            <CardDescription>Your past invoices and payments</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Date</TableHead>
                    <TableHead>Description</TableHead>
                    <TableHead>Amount</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="w-[50px]"></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {history.map((invoice) => (
                    <TableRow key={invoice.id}>
                      <TableCell className="font-medium">
                        {format(new Date(invoice.created_at), "PP")}
                      </TableCell>
                      <TableCell>{invoice.description}</TableCell>
                      <TableCell>
                        <span className="font-mono">
                          ${(invoice.amount / 100).toFixed(2)}{" "}
                          {invoice.currency.toUpperCase()}
                        </span>
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant={
                            invoice.status === "paid" ? "success" : "secondary"
                          }
                        >
                          {invoice.status}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        {invoice.invoice_pdf && (
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() =>
                              window.open(invoice.invoice_pdf, "_blank")
                            }
                          >
                            <Download className="h-4 w-4" />
                          </Button>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Payment Methods */}
      {paymentMethods && paymentMethods.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Payment Methods</CardTitle>
            <CardDescription>Manage your payment methods</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {paymentMethods.map((method) => (
                <div
                  key={method.id}
                  className="flex items-center justify-between p-4 border rounded-lg"
                >
                  <div className="flex items-center gap-3">
                    <CreditCard className="h-5 w-5 text-muted-foreground" />
                    <div>
                      <p className="font-medium">
                        {method.brand ? (
                          <span className="capitalize">{method.brand}</span>
                        ) : (
                          "Bank Account"
                        )}{" "}
                        •••• {method.last4}
                      </p>
                      {method.exp_month && method.exp_year && (
                        <p className="text-sm text-muted-foreground">
                          Expires {method.exp_month}/{method.exp_year}
                        </p>
                      )}
                    </div>
                    {method.is_default && (
                      <Badge variant="default">Default</Badge>
                    )}
                  </div>
                  <div className="flex gap-2">
                    {!method.is_default && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() =>
                          setDefaultPaymentMutation.mutate(method.id)
                        }
                        disabled={setDefaultPaymentMutation.isPending}
                      >
                        Set Default
                      </Button>
                    )}
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => removePaymentMutation.mutate(method.id)}
                      disabled={removePaymentMutation.isPending}
                    >
                      Remove
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Cancel Subscription Dialog */}
      <Dialog open={cancelDialogOpen} onOpenChange={setCancelDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Cancel Subscription</DialogTitle>
            <DialogDescription>
              Are you sure you want to cancel your subscription? You&apos;ll
              still have access until the end of your billing period.
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <p className="text-sm text-muted-foreground">
              Your subscription will remain active until{" "}
              {subscription &&
                format(new Date(subscription.current_period_end), "PPP")}
              . After that, you&apos;ll be downgraded to the Free plan.
            </p>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setCancelDialogOpen(false)}
              disabled={cancelMutation.isPending}
            >
              Keep Subscription
            </Button>
            <Button
              variant="destructive"
              onClick={handleCancelSubscription}
              disabled={cancelMutation.isPending}
            >
              {cancelMutation.isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Canceling...
                </>
              ) : (
                "Cancel Subscription"
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
