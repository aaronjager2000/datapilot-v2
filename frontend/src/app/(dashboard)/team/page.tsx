/**
 * Team Management Page
 *
 * Manage team members and invitations
 */

"use client";

import { useState } from "react";
import {
  Users,
  UserPlus,
  MoreVertical,
  Shield,
  UserX,
  Mail,
  Loader2,
  CheckCircle2,
  XCircle,
  Clock,
} from "lucide-react";
import { format } from "date-fns";
import {
  useTeamMembers,
  useUpdateUserRole,
  useUpdateUserStatus,
  useRemoveUser,
  useResendInvitation,
  useRoles,
} from "@/lib/hooks/useTeam";
import { UserInviteForm } from "@/components/forms/UserInviteForm";
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
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useToast } from "@/components/ui/toast";
import { Label } from "@/components/ui/label";

export default function TeamPage() {
  const { addToast } = useToast();
  const [inviteDialogOpen, setInviteDialogOpen] = useState(false);
  const [editRoleDialogOpen, setEditRoleDialogOpen] = useState(false);
  const [removeUserDialogOpen, setRemoveUserDialogOpen] = useState(false);
  const [selectedUser, setSelectedUser] = useState<string | null>(null);
  const [selectedRoleIds, setSelectedRoleIds] = useState<string[]>([]);

  // Queries
  const { data: teamData, isLoading } = useTeamMembers(1, 100);
  const { data: roles } = useRoles();

  // Mutations
  const updateRoleMutation = useUpdateUserRole({
    onSuccess: () => {
      addToast({
        type: "success",
        title: "Role updated",
        description: "User role has been updated successfully",
      });
      setEditRoleDialogOpen(false);
      setSelectedUser(null);
    },
  });

  const updateStatusMutation = useUpdateUserStatus({
    onSuccess: (data) => {
      addToast({
        type: "success",
        title: data.is_active ? "User activated" : "User deactivated",
        description: `User has been ${data.is_active ? "activated" : "deactivated"} successfully`,
      });
    },
  });

  const removeUserMutation = useRemoveUser({
    onSuccess: () => {
      addToast({
        type: "success",
        title: "User removed",
        description: "User has been removed from the organization",
      });
      setRemoveUserDialogOpen(false);
      setSelectedUser(null);
    },
  });

  const resendInvitationMutation = useResendInvitation({
    onSuccess: () => {
      addToast({
        type: "success",
        title: "Invitation resent",
        description: "Invitation email has been sent again",
      });
    },
  });

  // Handlers
  const handleEditRole = (userId: string, currentRoleIds: string[]) => {
    setSelectedUser(userId);
    setSelectedRoleIds(currentRoleIds);
    setEditRoleDialogOpen(true);
  };

  const handleSaveRole = () => {
    if (selectedUser) {
      updateRoleMutation.mutate({
        userId: selectedUser,
        roleIds: selectedRoleIds,
      });
    }
  };

  const handleToggleStatus = (userId: string, isActive: boolean) => {
    updateStatusMutation.mutate({
      userId,
      updates: { is_active: !isActive },
    });
  };

  const handleRemoveUser = (userId: string) => {
    setSelectedUser(userId);
    setRemoveUserDialogOpen(true);
  };

  const confirmRemoveUser = () => {
    if (selectedUser) {
      removeUserMutation.mutate(selectedUser);
    }
  };

  const handleResendInvitation = (userId: string) => {
    resendInvitationMutation.mutate(userId);
  };

  const getUserStatusBadge = (user: {
    is_active: boolean;
    email_verified: boolean;
  }) => {
    if (!user.is_active) {
      return (
        <Badge variant="secondary" className="flex items-center gap-1">
          <XCircle className="h-3 w-3" />
          Inactive
        </Badge>
      );
    }
    if (!user.email_verified) {
      return (
        <Badge variant="outline" className="flex items-center gap-1">
          <Clock className="h-3 w-3" />
          Pending
        </Badge>
      );
    }
    return (
      <Badge variant="success" className="flex items-center gap-1">
        <CheckCircle2 className="h-3 w-3" />
        Active
      </Badge>
    );
  };

  if (isLoading) {
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
            <Users className="h-8 w-8" />
            Team Management
          </h1>
          <p className="text-muted-foreground">
            Manage team members and their roles
          </p>
        </div>
        <Button onClick={() => setInviteDialogOpen(true)}>
          <UserPlus className="mr-2 h-4 w-4" />
          Invite Member
        </Button>
      </div>

      {/* Team Members Table */}
      <Card>
        <CardHeader>
          <CardTitle>Team Members</CardTitle>
          <CardDescription>
            {teamData?.total || 0} member{teamData?.total !== 1 ? "s" : ""} in
            your organization
          </CardDescription>
        </CardHeader>
        <CardContent>
          {teamData?.items && teamData.items.length > 0 ? (
            <div className="rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>Email</TableHead>
                    <TableHead>Role</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Last Login</TableHead>
                    <TableHead className="w-[50px]"></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {teamData.items.map((member) => (
                    <TableRow key={member.id}>
                      <TableCell className="font-medium">
                        {member.full_name}
                        {member.is_superuser && (
                          <Badge variant="outline" className="ml-2 text-xs">
                            Admin
                          </Badge>
                        )}
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {member.email}
                      </TableCell>
                      <TableCell>
                        <div className="flex flex-wrap gap-1">
                          {member.role_names && member.role_names.length > 0 ? (
                            member.role_names.map((role) => (
                              <Badge
                                key={role}
                                variant="outline"
                                className="text-xs"
                              >
                                <Shield className="h-3 w-3 mr-1" />
                                {role}
                              </Badge>
                            ))
                          ) : (
                            <span className="text-sm text-muted-foreground">
                              No role
                            </span>
                          )}
                        </div>
                      </TableCell>
                      <TableCell>{getUserStatusBadge(member)}</TableCell>
                      <TableCell className="text-muted-foreground">
                        {member.last_login
                          ? format(new Date(member.last_login), "PP")
                          : "Never"}
                      </TableCell>
                      <TableCell>
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="icon">
                              <MoreVertical className="h-4 w-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuLabel>Actions</DropdownMenuLabel>
                            <DropdownMenuSeparator />
                            <DropdownMenuItem
                              onClick={() =>
                                handleEditRole(
                                  member.id,
                                  roles
                                    ?.filter((r) =>
                                      member.role_names?.includes(r.name)
                                    )
                                    .map((r) => r.id) || []
                                )
                              }
                            >
                              <Shield className="mr-2 h-4 w-4" />
                              Edit Role
                            </DropdownMenuItem>

                            {!member.email_verified && (
                              <DropdownMenuItem
                                onClick={() =>
                                  handleResendInvitation(member.id)
                                }
                                disabled={resendInvitationMutation.isPending}
                              >
                                <Mail className="mr-2 h-4 w-4" />
                                Resend Invitation
                              </DropdownMenuItem>
                            )}

                            <DropdownMenuItem
                              onClick={() =>
                                handleToggleStatus(member.id, member.is_active)
                              }
                              disabled={updateStatusMutation.isPending}
                            >
                              {member.is_active ? (
                                <>
                                  <XCircle className="mr-2 h-4 w-4" />
                                  Deactivate
                                </>
                              ) : (
                                <>
                                  <CheckCircle2 className="mr-2 h-4 w-4" />
                                  Activate
                                </>
                              )}
                            </DropdownMenuItem>

                            <DropdownMenuSeparator />

                            <DropdownMenuItem
                              onClick={() => handleRemoveUser(member.id)}
                              className="text-destructive"
                            >
                              <UserX className="mr-2 h-4 w-4" />
                              Remove User
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          ) : (
            <div className="text-center py-12">
              <Users className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <h3 className="text-lg font-semibold mb-2">No team members</h3>
              <p className="text-muted-foreground mb-4">
                Start by inviting your first team member
              </p>
              <Button onClick={() => setInviteDialogOpen(true)}>
                <UserPlus className="mr-2 h-4 w-4" />
                Invite Member
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Invite User Dialog */}
      <UserInviteForm
        open={inviteDialogOpen}
        onOpenChange={setInviteDialogOpen}
        onSuccess={() => {
          addToast({
            type: "success",
            title: "Invitation sent",
            description: "Team member invitation has been sent",
          });
        }}
      />

      {/* Edit Role Dialog */}
      <Dialog open={editRoleDialogOpen} onOpenChange={setEditRoleDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit User Role</DialogTitle>
            <DialogDescription>
              Change the role for this team member
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Role</Label>
              <Select
                value={selectedRoleIds[0] || ""}
                onValueChange={(value) => setSelectedRoleIds([value])}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select a role" />
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
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setEditRoleDialogOpen(false)}
              disabled={updateRoleMutation.isPending}
            >
              Cancel
            </Button>
            <Button
              onClick={handleSaveRole}
              disabled={
                updateRoleMutation.isPending || selectedRoleIds.length === 0
              }
            >
              {updateRoleMutation.isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Saving...
                </>
              ) : (
                "Save Changes"
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Remove User Dialog */}
      <Dialog
        open={removeUserDialogOpen}
        onOpenChange={setRemoveUserDialogOpen}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Remove Team Member</DialogTitle>
            <DialogDescription>
              Are you sure you want to remove this team member? This action
              cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <p className="text-sm text-muted-foreground">
              The user will lose access to all organization data and resources.
            </p>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setRemoveUserDialogOpen(false)}
              disabled={removeUserMutation.isPending}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={confirmRemoveUser}
              disabled={removeUserMutation.isPending}
            >
              {removeUserMutation.isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Removing...
                </>
              ) : (
                <>
                  <UserX className="mr-2 h-4 w-4" />
                  Remove User
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
