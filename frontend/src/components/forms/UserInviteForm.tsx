/**
 * UserInviteForm Component
 *
 * Form for inviting users to the organization
 */

"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Loader2, UserPlus, Mail, Shield } from "lucide-react";
import { useInviteUser, useRoles } from "@/lib/hooks/useTeam";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
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

// ============================================================================
// Schema
// ============================================================================

const inviteSchema = z.object({
  email: z.string().email("Invalid email address"),
  full_name: z.string().min(1, "Name is required"),
  role_id: z.string().min(1, "Please select a role"),
});

type InviteFormData = z.infer<typeof inviteSchema>;

// ============================================================================
// Component
// ============================================================================

interface UserInviteFormProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
}

export function UserInviteForm({
  open,
  onOpenChange,
  onSuccess,
}: UserInviteFormProps) {
  const [showSuccess, setShowSuccess] = useState(false);

  const { data: roles, isLoading: rolesLoading } = useRoles();

  const inviteMutation = useInviteUser({
    onSuccess: () => {
      setShowSuccess(true);
      setTimeout(() => {
        setShowSuccess(false);
        onOpenChange(false);
        form.reset();
        onSuccess?.();
      }, 2000);
    },
  });

  const form = useForm<InviteFormData>({
    resolver: zodResolver(inviteSchema),
    defaultValues: {
      email: "",
      full_name: "",
      role_id: "",
    },
  });

  const onSubmit = (data: InviteFormData) => {
    inviteMutation.mutate({
      email: data.email,
      full_name: data.full_name,
      role_ids: [data.role_id],
      send_email: true,
    });
  };

  const handleClose = () => {
    if (!inviteMutation.isPending) {
      form.reset();
      onOpenChange(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <UserPlus className="h-5 w-5" />
            Invite Team Member
          </DialogTitle>
          <DialogDescription>
            Send an invitation to join your organization
          </DialogDescription>
        </DialogHeader>

        {showSuccess ? (
          <div className="py-12 text-center">
            <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-green-100 dark:bg-green-950">
              <Mail className="h-6 w-6 text-green-600 dark:text-green-400" />
            </div>
            <h3 className="text-lg font-semibold mb-2">Invitation Sent!</h3>
            <p className="text-sm text-muted-foreground">
              An email invitation has been sent
            </p>
          </div>
        ) : (
          <form onSubmit={form.handleSubmit((data) => onSubmit(data))} className="space-y-4">
            {/* Email Field */}
            <div className="space-y-2">
              <Label htmlFor="email">Email Address</Label>
              <Input
                id="email"
                type="email"
                placeholder="colleague@example.com"
                {...form.register("email")}
                disabled={inviteMutation.isPending}
              />
              {form.formState.errors.email && (
                <p className="text-sm text-destructive">
                  {form.formState.errors.email.message}
                </p>
              )}
            </div>

            {/* Full Name Field */}
            <div className="space-y-2">
              <Label htmlFor="full_name">Full Name</Label>
              <Input
                id="full_name"
                placeholder="John Doe"
                {...form.register("full_name")}
                disabled={inviteMutation.isPending}
              />
              {form.formState.errors.full_name && (
                <p className="text-sm text-destructive">
                  {form.formState.errors.full_name.message}
                </p>
              )}
            </div>

            {/* Role Selector */}
            <div className="space-y-2">
              <Label htmlFor="role_id">Role</Label>
              {rolesLoading ? (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Loading roles...
                </div>
              ) : (
                <>
                  <Select
                    value={form.watch("role_id")}
                    onValueChange={(value) => form.setValue("role_id", value)}
                    disabled={inviteMutation.isPending}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select a role">
                        {form.watch("role_id") && (
                          <div className="flex items-center gap-2">
                            <Shield className="h-4 w-4" />
                            {roles?.find((r) => r.id === form.watch("role_id"))
                              ?.name || "Select a role"}
                          </div>
                        )}
                      </SelectValue>
                    </SelectTrigger>
                    <SelectContent>
                      {roles?.map((role) => (
                        <SelectItem key={role.id} value={role.id}>
                          <div className="flex flex-col">
                            <span className="font-medium">{role.name}</span>
                            {role.description && (
                              <span className="text-xs text-muted-foreground">
                                {role.description}
                              </span>
                            )}
                          </div>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  {form.formState.errors.role_id && (
                    <p className="text-sm text-destructive">
                      {form.formState.errors.role_id.message}
                    </p>
                  )}
                </>
              )}
            </div>

            {/* Error Message */}
            {inviteMutation.isError && (
              <div className="rounded-lg bg-destructive/10 p-3 text-sm text-destructive">
                <p className="font-medium">Failed to send invitation</p>
                <p className="text-xs mt-1">
                  {(inviteMutation.error as { detail?: string })?.detail ||
                    "Please try again or contact support."}
                </p>
              </div>
            )}

            {/* Footer */}
            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={handleClose}
                disabled={inviteMutation.isPending}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={inviteMutation.isPending}>
                {inviteMutation.isPending ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Sending...
                  </>
                ) : (
                  <>
                    <Mail className="mr-2 h-4 w-4" />
                    Send Invitation
                  </>
                )}
              </Button>
            </DialogFooter>
          </form>
        )}
      </DialogContent>
    </Dialog>
  );
}
