/**
 * Settings Page
 *
 * User and organization settings
 */

"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import {
  User,
  Building2,
  Plug2,
  Loader2,
  Save,
  Trash2,
  Key,
  Plus,
  Copy,
  CheckCircle2,
  Link as LinkIcon,
  Settings as SettingsIcon,
} from "lucide-react";
import { format } from "date-fns";
import {
  useUserProfile,
  useUpdateUserProfile,
  useChangePassword,
  useNotificationSettings,
  useUpdateNotificationSettings,
  useDeleteAccount,
  useOrganization,
  useUpdateOrganization,
  useOrganizationSettings,
  useUpdateOrganizationSettings,
  useApiKeys,
  useCreateApiKey,
  useRevokeApiKey,
  useWebhooks,
  useCreateWebhook,
  useDeleteWebhook,
  useToggleWebhook,
  useOAuthConnections,
  useDisconnectOAuth,
} from "@/lib/hooks/useSettings";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { useToast } from "@/components/ui/toast";

// ============================================================================
// Schemas
// ============================================================================

const profileSchema = z.object({
  full_name: z.string().min(1, "Name is required"),
  email: z.string().email("Invalid email address"),
});

const passwordSchema = z
  .object({
    current_password: z.string().min(1, "Current password is required"),
    new_password: z.string().min(8, "Password must be at least 8 characters"),
    confirm_password: z.string(),
  })
  .refine((data) => data.new_password === data.confirm_password, {
    message: "Passwords don't match",
    path: ["confirm_password"],
  });

const organizationSchema = z.object({
  name: z.string().min(1, "Organization name is required"),
  description: z.string().optional(),
  website: z.string().url("Invalid URL").optional().or(z.literal("")),
});

const apiKeySchema = z.object({
  name: z.string().min(1, "Key name is required"),
  expires_in_days: z.number().optional(),
});

const webhookSchema = z.object({
  url: z.string().url("Invalid webhook URL"),
  events: z.array(z.string()).min(1, "Select at least one event"),
});

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState("profile");
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deletePassword, setDeletePassword] = useState("");
  const [apiKeyDialogOpen, setApiKeyDialogOpen] = useState(false);
  const [webhookDialogOpen, setWebhookDialogOpen] = useState(false);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);
  const { addToast } = useToast();

  // Queries
  const { data: user, isLoading: userLoading } = useUserProfile();
  const { data: notifications } = useNotificationSettings();
  const { data: organization, isLoading: orgLoading } = useOrganization();
  const { data: orgSettings } = useOrganizationSettings();
  const { data: apiKeys } = useApiKeys();
  const { data: webhooks } = useWebhooks();
  const { data: oauthConnections } = useOAuthConnections();

  // Mutations
  const updateProfileMutation = useUpdateUserProfile({
    onSuccess: () => {
      addToast({
        type: "success",
        title: "Profile updated",
        description: "Your profile has been updated successfully",
      });
    },
  });

  const changePasswordMutation = useChangePassword({
    onSuccess: () => {
      addToast({
        type: "success",
        title: "Password changed",
        description: "Your password has been changed successfully",
      });
      passwordForm.reset();
    },
  });

  const updateNotificationsMutation = useUpdateNotificationSettings();

  const deleteAccountMutation = useDeleteAccount({
    onSuccess: () => {
      addToast({
        type: "success",
        title: "Account deleted",
        description: "Your account has been deleted",
      });
      // Redirect to login
      window.location.href = "/login";
    },
  });

  const updateOrganizationMutation = useUpdateOrganization({
    onSuccess: () => {
      addToast({
        type: "success",
        title: "Organization updated",
        description: "Organization settings have been updated",
      });
    },
  });

  const updateOrgSettingsMutation = useUpdateOrganizationSettings();

  const createApiKeyMutation = useCreateApiKey({
    onSuccess: () => {
      addToast({
        type: "success",
        title: "API key created",
        description: "Your new API key has been generated",
      });
      setApiKeyDialogOpen(false);
      apiKeyForm.reset();
    },
  });

  const revokeApiKeyMutation = useRevokeApiKey({
    onSuccess: () => {
      addToast({
        type: "success",
        title: "API key revoked",
        description: "The API key has been revoked",
      });
    },
  });

  const createWebhookMutation = useCreateWebhook({
    onSuccess: () => {
      addToast({
        type: "success",
        title: "Webhook created",
        description: "Your webhook has been created",
      });
      setWebhookDialogOpen(false);
      webhookForm.reset();
    },
  });

  const deleteWebhookMutation = useDeleteWebhook({
    onSuccess: () => {
      addToast({
        type: "success",
        title: "Webhook deleted",
        description: "The webhook has been deleted",
      });
    },
  });

  const toggleWebhookMutation = useToggleWebhook();
  const disconnectOAuthMutation = useDisconnectOAuth({
    onSuccess: () => {
      addToast({
        type: "success",
        title: "OAuth disconnected",
        description: "OAuth connection has been removed",
      });
    },
  });

  // Forms
  const profileForm = useForm({
    resolver: zodResolver(profileSchema),
    values: {
      full_name: user?.full_name || "",
      email: user?.email || "",
    },
  });

  const passwordForm = useForm({
    resolver: zodResolver(passwordSchema),
    defaultValues: {
      current_password: "",
      new_password: "",
      confirm_password: "",
    },
  });

  const organizationForm = useForm({
    resolver: zodResolver(organizationSchema),
    values: {
      name: organization?.name || "",
      description: organization?.description || "",
      website: organization?.website || "",
    },
  });

  const apiKeyForm = useForm({
    resolver: zodResolver(apiKeySchema),
    defaultValues: {
      name: "",
      expires_in_days: 365,
    },
  });

  const webhookForm = useForm({
    resolver: zodResolver(webhookSchema),
    defaultValues: {
      url: "",
      events: [],
    },
  });

  // Handlers
  const handleProfileSubmit = (data: z.infer<typeof profileSchema>) => {
    updateProfileMutation.mutate(data);
  };

  const handlePasswordSubmit = (data: z.infer<typeof passwordSchema>) => {
    changePasswordMutation.mutate({
      current_password: data.current_password,
      new_password: data.new_password,
    });
  };

  const handleOrganizationSubmit = (
    data: z.infer<typeof organizationSchema>
  ) => {
    updateOrganizationMutation.mutate(data);
  };

  const handleApiKeySubmit = (data: z.infer<typeof apiKeySchema>) => {
    createApiKeyMutation.mutate(data);
  };

  const handleWebhookSubmit = (data: z.infer<typeof webhookSchema>) => {
    createWebhookMutation.mutate(data);
  };

  const handleDeleteAccount = () => {
    if (deletePassword) {
      deleteAccountMutation.mutate(deletePassword);
    }
  };

  const copyToClipboard = (text: string, keyId: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(keyId);
    setTimeout(() => setCopiedKey(null), 2000);
    addToast({
      type: "success",
      title: "Copied",
      description: "API key copied to clipboard",
    });
  };

  if (userLoading || orgLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-5xl">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold flex items-center gap-2">
          <SettingsIcon className="h-8 w-8" />
          Settings
        </h1>
        <p className="text-muted-foreground">
          Manage your account and organization settings
        </p>
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full max-w-md grid-cols-3">
          <TabsTrigger value="profile">
            <User className="h-4 w-4 mr-2" />
            Profile
          </TabsTrigger>
          <TabsTrigger value="organization">
            <Building2 className="h-4 w-4 mr-2" />
            Organization
          </TabsTrigger>
          <TabsTrigger value="integrations">
            <Plug2 className="h-4 w-4 mr-2" />
            Integrations
          </TabsTrigger>
        </TabsList>

        {/* Profile Tab */}
        <TabsContent value="profile" className="space-y-6">
          {/* User Info */}
          <Card>
            <CardHeader>
              <CardTitle>Profile Information</CardTitle>
              <CardDescription>
                Update your personal information
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form
                onSubmit={profileForm.handleSubmit(handleProfileSubmit)}
                className="space-y-4"
              >
                <div className="space-y-2">
                  <Label htmlFor="full_name">Full Name</Label>
                  <Input
                    id="full_name"
                    {...profileForm.register("full_name")}
                  />
                  {profileForm.formState.errors.full_name && (
                    <p className="text-sm text-destructive">
                      {profileForm.formState.errors.full_name.message}
                    </p>
                  )}
                </div>

                <div className="space-y-2">
                  <Label htmlFor="email">Email</Label>
                  <Input id="email" {...profileForm.register("email")} />
                  {profileForm.formState.errors.email && (
                    <p className="text-sm text-destructive">
                      {profileForm.formState.errors.email.message}
                    </p>
                  )}
                </div>

                <Button
                  type="submit"
                  disabled={updateProfileMutation.isPending}
                >
                  {updateProfileMutation.isPending ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Saving...
                    </>
                  ) : (
                    <>
                      <Save className="mr-2 h-4 w-4" />
                      Save Changes
                    </>
                  )}
                </Button>
              </form>
            </CardContent>
          </Card>

          {/* Change Password */}
          <Card>
            <CardHeader>
              <CardTitle>Change Password</CardTitle>
              <CardDescription>
                Update your password to keep your account secure
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form
                onSubmit={passwordForm.handleSubmit(handlePasswordSubmit)}
                className="space-y-4"
              >
                <div className="space-y-2">
                  <Label htmlFor="current_password">Current Password</Label>
                  <Input
                    id="current_password"
                    type="password"
                    {...passwordForm.register("current_password")}
                  />
                  {passwordForm.formState.errors.current_password && (
                    <p className="text-sm text-destructive">
                      {passwordForm.formState.errors.current_password.message}
                    </p>
                  )}
                </div>

                <div className="space-y-2">
                  <Label htmlFor="new_password">New Password</Label>
                  <Input
                    id="new_password"
                    type="password"
                    {...passwordForm.register("new_password")}
                  />
                  {passwordForm.formState.errors.new_password && (
                    <p className="text-sm text-destructive">
                      {passwordForm.formState.errors.new_password.message}
                    </p>
                  )}
                </div>

                <div className="space-y-2">
                  <Label htmlFor="confirm_password">Confirm Password</Label>
                  <Input
                    id="confirm_password"
                    type="password"
                    {...passwordForm.register("confirm_password")}
                  />
                  {passwordForm.formState.errors.confirm_password && (
                    <p className="text-sm text-destructive">
                      {passwordForm.formState.errors.confirm_password.message}
                    </p>
                  )}
                </div>

                <Button
                  type="submit"
                  disabled={changePasswordMutation.isPending}
                >
                  {changePasswordMutation.isPending ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Changing...
                    </>
                  ) : (
                    "Change Password"
                  )}
                </Button>
              </form>
            </CardContent>
          </Card>

          {/* Email Notifications */}
          <Card>
            <CardHeader>
              <CardTitle>Email Notifications</CardTitle>
              <CardDescription>
                Manage your email notification preferences
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {notifications && (
                <>
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium">Email Notifications</p>
                      <p className="text-sm text-muted-foreground">
                        Receive notifications via email
                      </p>
                    </div>
                    <Switch
                      checked={notifications.email_notifications}
                      onCheckedChange={(checked: boolean) =>
                        updateNotificationsMutation.mutate({
                          email_notifications: checked,
                        })
                      }
                    />
                  </div>

                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium">Dataset Updates</p>
                      <p className="text-sm text-muted-foreground">
                        Notify when datasets are processed
                      </p>
                    </div>
                    <Switch
                      checked={notifications.dataset_updates}
                      onCheckedChange={(checked: boolean) =>
                        updateNotificationsMutation.mutate({
                          dataset_updates: checked,
                        })
                      }
                    />
                  </div>

                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium">Insight Alerts</p>
                      <p className="text-sm text-muted-foreground">
                        Notify when new insights are generated
                      </p>
                    </div>
                    <Switch
                      checked={notifications.insight_alerts}
                      onCheckedChange={(checked) =>
                        updateNotificationsMutation.mutate({
                          insight_alerts: checked,
                        })
                      }
                    />
                  </div>

                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium">Weekly Summary</p>
                      <p className="text-sm text-muted-foreground">
                        Receive a weekly summary of your activity
                      </p>
                    </div>
                    <Switch
                      checked={notifications.weekly_summary}
                      onCheckedChange={(checked: boolean) =>
                        updateNotificationsMutation.mutate({
                          weekly_summary: checked,
                        })
                      }
                    />
                  </div>

                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium">Marketing Emails</p>
                      <p className="text-sm text-muted-foreground">
                        Receive updates about new features
                      </p>
                    </div>
                    <Switch
                      checked={notifications.marketing_emails}
                      onCheckedChange={(checked: boolean) =>
                        updateNotificationsMutation.mutate({
                          marketing_emails: checked,
                        })
                      }
                    />
                  </div>
                </>
              )}
            </CardContent>
          </Card>

          {/* Delete Account */}
          <Card className="border-destructive">
            <CardHeader>
              <CardTitle className="text-destructive">Danger Zone</CardTitle>
              <CardDescription>
                Permanently delete your account and all associated data
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Button
                variant="destructive"
                onClick={() => setDeleteDialogOpen(true)}
              >
                <Trash2 className="mr-2 h-4 w-4" />
                Delete Account
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Organization Tab */}
        <TabsContent value="organization" className="space-y-6">
          {/* Organization Info */}
          <Card>
            <CardHeader>
              <CardTitle>Organization Details</CardTitle>
              <CardDescription>
                Manage your organization information
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form
                onSubmit={organizationForm.handleSubmit(
                  handleOrganizationSubmit
                )}
                className="space-y-4"
              >
                <div className="space-y-2">
                  <Label htmlFor="org_name">Organization Name</Label>
                  <Input
                    id="org_name"
                    {...organizationForm.register("name")}
                  />
                  {organizationForm.formState.errors.name && (
                    <p className="text-sm text-destructive">
                      {organizationForm.formState.errors.name.message}
                    </p>
                  )}
                </div>

                <div className="space-y-2">
                  <Label htmlFor="org_description">Description</Label>
                  <Input
                    id="org_description"
                    {...organizationForm.register("description")}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="org_website">Website</Label>
                  <Input
                    id="org_website"
                    {...organizationForm.register("website")}
                    placeholder="https://"
                  />
                  {organizationForm.formState.errors.website && (
                    <p className="text-sm text-destructive">
                      {organizationForm.formState.errors.website.message}
                    </p>
                  )}
                </div>

                <Button
                  type="submit"
                  disabled={updateOrganizationMutation.isPending}
                >
                  {updateOrganizationMutation.isPending ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Saving...
                    </>
                  ) : (
                    <>
                      <Save className="mr-2 h-4 w-4" />
                      Save Changes
                    </>
                  )}
                </Button>
              </form>
            </CardContent>
          </Card>

          {/* Organization Settings */}
          <Card>
            <CardHeader>
              <CardTitle>Organization Settings</CardTitle>
              <CardDescription>
                Configure timezone and regional settings
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {orgSettings && (
                <>
                  <div className="space-y-2">
                    <Label>Timezone</Label>
                    <Select
                      value={orgSettings.timezone}
                      onValueChange={(value) =>
                        updateOrgSettingsMutation.mutate({ timezone: value })
                      }
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="UTC">UTC</SelectItem>
                        <SelectItem value="America/New_York">
                          Eastern Time
                        </SelectItem>
                        <SelectItem value="America/Chicago">
                          Central Time
                        </SelectItem>
                        <SelectItem value="America/Denver">
                          Mountain Time
                        </SelectItem>
                        <SelectItem value="America/Los_Angeles">
                          Pacific Time
                        </SelectItem>
                        <SelectItem value="Europe/London">London</SelectItem>
                        <SelectItem value="Europe/Paris">Paris</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label>Date Format</Label>
                    <Select
                      value={orgSettings.date_format}
                      onValueChange={(value) =>
                        updateOrgSettingsMutation.mutate({ date_format: value })
                      }
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="MM/DD/YYYY">MM/DD/YYYY</SelectItem>
                        <SelectItem value="DD/MM/YYYY">DD/MM/YYYY</SelectItem>
                        <SelectItem value="YYYY-MM-DD">YYYY-MM-DD</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label>Currency</Label>
                    <Select
                      value={orgSettings.currency}
                      onValueChange={(value) =>
                        updateOrgSettingsMutation.mutate({ currency: value })
                      }
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="USD">USD ($)</SelectItem>
                        <SelectItem value="EUR">EUR (€)</SelectItem>
                        <SelectItem value="GBP">GBP (£)</SelectItem>
                        <SelectItem value="JPY">JPY (¥)</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </>
              )}
            </CardContent>
          </Card>

          {/* Storage & Limits */}
          {organization && (
            <Card>
              <CardHeader>
                <CardTitle>Storage & Limits</CardTitle>
                <CardDescription>
                  Your current usage and limits
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-3 gap-4">
                  <div className="space-y-1">
                    <p className="text-sm text-muted-foreground">Users</p>
                    <p className="text-2xl font-bold">
                      {organization.current_users || 0} /{" "}
                      {organization.max_users}
                    </p>
                  </div>
                  <div className="space-y-1">
                    <p className="text-sm text-muted-foreground">Datasets</p>
                    <p className="text-2xl font-bold">
                      {organization.current_datasets || 0} /{" "}
                      {organization.max_datasets}
                    </p>
                  </div>
                  <div className="space-y-1">
                    <p className="text-sm text-muted-foreground">Storage</p>
                    <p className="text-2xl font-bold">
                      {organization.current_storage_gb?.toFixed(2) || 0} /{" "}
                      {organization.max_storage_gb} GB
                    </p>
                  </div>
                </div>

                <div className="pt-4 border-t">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium">Subscription</p>
                      <p className="text-sm text-muted-foreground capitalize">
                        {organization.subscription_tier}
                      </p>
                    </div>
                    <Badge variant="default">
                      {organization.subscription_status}
                    </Badge>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* API Keys */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>API Keys</CardTitle>
                  <CardDescription>
                    Manage API keys for programmatic access
                  </CardDescription>
                </div>
                <Button
                  size="sm"
                  onClick={() => setApiKeyDialogOpen(true)}
                >
                  <Plus className="mr-2 h-4 w-4" />
                  Generate Key
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {apiKeys && apiKeys.length > 0 ? (
                <div className="space-y-3">
                  {apiKeys.map((key) => (
                    <div
                      key={key.id}
                      className="flex items-center justify-between p-3 border rounded-lg"
                    >
                      <div className="flex-1">
                        <p className="font-medium">{key.name}</p>
                        <div className="flex items-center gap-2 mt-1">
                          <code className="text-xs bg-muted px-2 py-1 rounded">
                            {key.key.substring(0, 20)}...
                          </code>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => copyToClipboard(key.key, key.id)}
                          >
                            {copiedKey === key.id ? (
                              <CheckCircle2 className="h-3 w-3 text-green-600" />
                            ) : (
                              <Copy className="h-3 w-3" />
                            )}
                          </Button>
                        </div>
                        <p className="text-xs text-muted-foreground mt-1">
                          Created {format(new Date(key.created_at), "PPP")}
                          {key.last_used &&
                            ` • Last used ${format(new Date(key.last_used), "PPP")}`}
                        </p>
                      </div>
                      <Button
                        variant="destructive"
                        size="sm"
                        onClick={() => revokeApiKeyMutation.mutate(key.id)}
                        disabled={revokeApiKeyMutation.isPending}
                      >
                        Revoke
                      </Button>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground text-center py-8">
                  No API keys yet. Generate one to get started.
                </p>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Integrations Tab */}
        <TabsContent value="integrations" className="space-y-6">
          {/* OAuth Connections */}
          <Card>
            <CardHeader>
              <CardTitle>OAuth Connections</CardTitle>
              <CardDescription>
                Manage your connected accounts
              </CardDescription>
            </CardHeader>
            <CardContent>
              {oauthConnections && oauthConnections.length > 0 ? (
                <div className="space-y-3">
                  {oauthConnections.map((connection) => (
                    <div
                      key={connection.provider}
                      className="flex items-center justify-between p-3 border rounded-lg"
                    >
                      <div>
                        <p className="font-medium capitalize">
                          {connection.provider}
                        </p>
                        <p className="text-sm text-muted-foreground">
                          {connection.email || "Connected"}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          Connected{" "}
                          {format(new Date(connection.connected_at), "PPP")}
                        </p>
                      </div>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() =>
                          disconnectOAuthMutation.mutate(connection.provider)
                        }
                        disabled={disconnectOAuthMutation.isPending}
                      >
                        Disconnect
                      </Button>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground text-center py-8">
                  No OAuth connections
                </p>
              )}
            </CardContent>
          </Card>

          {/* Webhooks */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>Webhooks</CardTitle>
                  <CardDescription>
                    Configure webhooks for event notifications
                  </CardDescription>
                </div>
                <Button
                  size="sm"
                  onClick={() => setWebhookDialogOpen(true)}
                >
                  <Plus className="mr-2 h-4 w-4" />
                  Add Webhook
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {webhooks && webhooks.length > 0 ? (
                <div className="space-y-3">
                  {webhooks.map((webhook) => (
                    <div
                      key={webhook.id}
                      className="flex items-center justify-between p-3 border rounded-lg"
                    >
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <p className="font-medium">{webhook.url}</p>
                          <Badge
                            variant={
                              webhook.is_active ? "default" : "secondary"
                            }
                          >
                            {webhook.is_active ? "Active" : "Inactive"}
                          </Badge>
                        </div>
                        <p className="text-sm text-muted-foreground mt-1">
                          Events: {webhook.events.join(", ")}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          Created {format(new Date(webhook.created_at), "PPP")}
                        </p>
                      </div>
                      <div className="flex gap-2">
                        <Switch
                          checked={webhook.is_active}
                          onCheckedChange={(checked: boolean) =>
                            toggleWebhookMutation.mutate({
                              webhookId: webhook.id,
                              isActive: checked,
                            })
                          }
                        />
                        <Button
                          variant="destructive"
                          size="sm"
                          onClick={() =>
                            deleteWebhookMutation.mutate(webhook.id)
                          }
                          disabled={deleteWebhookMutation.isPending}
                        >
                          Delete
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground text-center py-8">
                  No webhooks configured. Add one to receive event
                  notifications.
                </p>
              )}
            </CardContent>
          </Card>

          {/* API Access Settings */}
          <Card>
            <CardHeader>
              <CardTitle>API Access</CardTitle>
              <CardDescription>
                Configure API access and rate limits
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between p-3 border rounded-lg">
                <div>
                  <p className="font-medium">Enable API Access</p>
                  <p className="text-sm text-muted-foreground">
                    Allow programmatic access to your data
                  </p>
                </div>
                <Switch defaultChecked />
              </div>

              <div className="flex items-center justify-between p-3 border rounded-lg">
                <div>
                  <p className="font-medium">Require API Key Authentication</p>
                  <p className="text-sm text-muted-foreground">
                    All API requests must include a valid API key
                  </p>
                </div>
                <Switch defaultChecked />
              </div>

              <div className="p-3 border rounded-lg space-y-2">
                <p className="font-medium">Rate Limits</p>
                <p className="text-sm text-muted-foreground">
                  1000 requests per hour
                </p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Delete Account Dialog */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Account</DialogTitle>
            <DialogDescription>
              This action cannot be undone. All your data, datasets,
              visualizations, and insights will be permanently deleted.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="delete_password">
                Enter your password to confirm
              </Label>
              <Input
                id="delete_password"
                type="password"
                value={deletePassword}
                onChange={(e) => setDeletePassword(e.target.value)}
                placeholder="Password"
              />
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setDeleteDialogOpen(false);
                setDeletePassword("");
              }}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleDeleteAccount}
              disabled={
                !deletePassword || deleteAccountMutation.isPending
              }
            >
              {deleteAccountMutation.isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Deleting...
                </>
              ) : (
                <>
                  <Trash2 className="mr-2 h-4 w-4" />
                  Delete Account
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* API Key Dialog */}
      <Dialog open={apiKeyDialogOpen} onOpenChange={setApiKeyDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Generate API Key</DialogTitle>
            <DialogDescription>
              Create a new API key for programmatic access
            </DialogDescription>
          </DialogHeader>
          <form
            onSubmit={apiKeyForm.handleSubmit(handleApiKeySubmit)}
            className="space-y-4 py-4"
          >
            <div className="space-y-2">
              <Label htmlFor="key_name">Key Name</Label>
              <Input
                id="key_name"
                {...apiKeyForm.register("name")}
                placeholder="Production API Key"
              />
              {apiKeyForm.formState.errors.name && (
                <p className="text-sm text-destructive">
                  {apiKeyForm.formState.errors.name.message}
                </p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="expires_in_days">Expires In (Days)</Label>
              <Input
                id="expires_in_days"
                type="number"
                {...apiKeyForm.register("expires_in_days", {
                  valueAsNumber: true,
                })}
                placeholder="365"
              />
            </div>

            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => setApiKeyDialogOpen(false)}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={createApiKeyMutation.isPending}
              >
                {createApiKeyMutation.isPending ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Generating...
                  </>
                ) : (
                  <>
                    <Key className="mr-2 h-4 w-4" />
                    Generate Key
                  </>
                )}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Webhook Dialog */}
      <Dialog open={webhookDialogOpen} onOpenChange={setWebhookDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add Webhook</DialogTitle>
            <DialogDescription>
              Configure a webhook to receive event notifications
            </DialogDescription>
          </DialogHeader>
          <form
            onSubmit={webhookForm.handleSubmit(handleWebhookSubmit)}
            className="space-y-4 py-4"
          >
            <div className="space-y-2">
              <Label htmlFor="webhook_url">Webhook URL</Label>
              <Input
                id="webhook_url"
                {...webhookForm.register("url")}
                placeholder="https://example.com/webhook"
              />
              {webhookForm.formState.errors.url && (
                <p className="text-sm text-destructive">
                  {webhookForm.formState.errors.url.message}
                </p>
              )}
            </div>

            <div className="space-y-2">
              <Label>Events</Label>
              <div className="space-y-2">
                {[
                  "dataset.created",
                  "dataset.processed",
                  "insight.generated",
                  "visualization.created",
                ].map((event) => (
                  <div key={event} className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      id={event}
                      value={event}
                      {...webhookForm.register("events")}
                    />
                    <Label htmlFor={event} className="font-normal">
                      {event}
                    </Label>
                  </div>
                ))}
              </div>
              {webhookForm.formState.errors.events && (
                <p className="text-sm text-destructive">
                  {webhookForm.formState.errors.events.message}
                </p>
              )}
            </div>

            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => setWebhookDialogOpen(false)}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={createWebhookMutation.isPending}
              >
                {createWebhookMutation.isPending ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Creating...
                  </>
                ) : (
                  <>
                    <LinkIcon className="mr-2 h-4 w-4" />
                    Add Webhook
                  </>
                )}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
