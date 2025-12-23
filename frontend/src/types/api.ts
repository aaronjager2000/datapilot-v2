/**
 * TypeScript types for API responses
 *
 * These types mirror the backend Pydantic schemas for type-safe API communication.
 * Auto-generated based on backend schemas - keep in sync with backend/app/schemas/
 */

// ============================================================================
// Common Types & Base Schemas
// ============================================================================

export interface TimestampSchema {
  created_at: string; // ISO 8601 datetime
  updated_at: string; // ISO 8601 datetime
}

export interface IDSchema {
  id: string; // UUID
}

export interface BaseDBSchema extends IDSchema, TimestampSchema {
  // Combines ID and timestamps
}

export interface MessageResponse {
  message: string;
  detail?: string;
}

export interface ErrorResponse {
  error: string;
  detail?: string;
  field?: string;
}

export interface PaginationParams {
  skip?: number;
  limit?: number;
}

export interface PaginatedResponse<T = unknown> {
  total: number;
  skip: number;
  limit: number;
  items: T[];
}

// ============================================================================
// Enums
// ============================================================================

export enum SubscriptionTier {
  FREE = "free",
  PRO = "pro",
  ENTERPRISE = "enterprise",
}

export enum SubscriptionStatus {
  ACTIVE = "active",
  TRIALING = "trialing",
  CANCELLED = "cancelled",
  PAST_DUE = "past_due",
  INCOMPLETE = "incomplete",
}

export enum ChartType {
  LINE = "line",
  BAR = "bar",
  PIE = "pie",
  SCATTER = "scatter",
  HEATMAP = "heatmap",
  TABLE = "table",
}

export enum DatasetStatus {
  UPLOADING = "uploading",
  PROCESSING = "processing",
  READY = "ready",
  FAILED = "failed",
}

export enum OAuthProvider {
  GOOGLE = "google",
  GITHUB = "github",
  MICROSOFT = "microsoft",
}

// ============================================================================
// User Types
// ============================================================================

export interface UserBase {
  email: string;
  full_name: string;
}

export interface UserCreate extends UserBase {
  password: string;
  organization_name?: string;
  organization_slug?: string;
}

export interface UserUpdate {
  email?: string;
  full_name?: string;
  password?: string;
}

export interface UserResponse extends UserBase, BaseDBSchema {
  organization_id: string; // UUID
  is_active: boolean;
  is_superuser: boolean;
  email_verified: boolean;
  last_login?: string; // ISO 8601 datetime
  oauth_provider?: string;
  oauth_id?: string;
  organization?: OrganizationSimple;
}

export interface UserSimple {
  id: string; // UUID
  email: string;
  full_name: string;
  is_active: boolean;
}

export interface UserWithRoles extends UserResponse {
  roles: string[]; // Role names
  permissions: string[]; // Permission codes
}

export interface UserInvite {
  email: string;
  full_name: string;
  role_ids?: string[]; // UUIDs
}

export interface UserStatusUpdate {
  is_active?: boolean;
  is_superuser?: boolean;
  email_verified?: boolean;
}

export interface PasswordChange {
  current_password: string;
  new_password: string;
}

export interface PasswordResetRequest {
  email: string;
}

export interface PasswordResetConfirm {
  token: string;
  new_password: string;
}

export interface EmailVerificationRequest {
  token: string;
}

// ============================================================================
// Organization Types
// ============================================================================

export interface OrganizationBase {
  name: string;
  slug: string;
  description?: string;
  website?: string;
  logo_url?: string;
}

export type OrganizationCreate = OrganizationBase;

export interface OrganizationUpdate {
  name?: string;
  slug?: string;
  description?: string;
  website?: string;
  logo_url?: string;
}

export interface OrganizationResponse extends OrganizationBase, BaseDBSchema {
  subscription_tier: string;
  subscription_status: string;
  trial_ends_at?: string; // ISO 8601 datetime
  is_active: boolean;
  max_users: number;
  max_datasets: number;
  max_storage_gb: number;
  current_users?: number;
  current_datasets?: number;
  current_storage_gb?: number;
  stripe_customer_id?: string;
  stripe_subscription_id?: string;
}

export interface OrganizationSimple {
  id: string; // UUID
  name: string;
  slug: string;
  logo_url?: string;
}

export interface OrganizationSettingsUpdate {
  settings: Record<string, unknown>;
}

export interface OrganizationSubscriptionUpdate {
  subscription_tier: string;
  max_users?: number;
  max_datasets?: number;
  max_storage_gb?: number;
}

export interface OrganizationStats {
  total_users: number;
  active_users: number;
  total_datasets: number;
  total_storage_gb: number;
  total_queries: number;
  queries_this_month: number;
}

// ============================================================================
// Authentication Types
// ============================================================================

export interface LoginRequest {
  email: string;
  password: string;
  remember_me?: boolean;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number; // seconds
}

export interface TokenRefreshRequest {
  refresh_token: string;
}

export interface TokenPayload {
  sub: string; // user_id (UUID)
  org_id: string; // organization_id (UUID)
  exp: number; // expiration timestamp
  type: string; // "access" or "refresh"
  email?: string;
  is_superuser: boolean;
  iat?: number; // issued at timestamp
  jti?: string; // JWT ID
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: UserResponse;
}

export interface OAuthLoginRequest {
  provider: string;
  code: string;
  redirect_uri: string;
}

export interface OAuthCallbackRequest {
  code: string;
  state?: string;
}

export interface LogoutRequest {
  refresh_token?: string;
}

export interface VerifyTokenRequest {
  token: string;
}

export interface VerifyTokenResponse {
  valid: boolean;
  user_id?: string; // UUID
  organization_id?: string; // UUID
  email?: string;
  expires_at?: number;
}

// ============================================================================
// Dataset Types
// ============================================================================

export interface ColumnInfo {
  name: string;
  type: string;
  nullable: boolean;
  sample_values: unknown[];
  unique_count?: number;
  null_count?: number;
}

export interface DatasetBase {
  name: string;
  description?: string;
}

export interface DatasetCreate extends DatasetBase {
  file_name: string;
  file_size: number;
  file_hash: string;
  file_path: string;
}

export interface DatasetUpdate {
  name?: string;
  description?: string;
  status?: DatasetStatus;
  processing_error?: string;
  row_count?: number;
  column_count?: number;
  schema_info?: Record<string, unknown>;
}

export interface DatasetInDB extends BaseDBSchema {
  organization_id: string; // UUID
  name: string;
  description?: string;
  file_name: string;
  file_size: number;
  file_hash: string;
  file_path: string;
  status: string;
  processing_error?: string;
  row_count?: number;
  column_count?: number;
  schema_info?: Record<string, unknown>;
  created_by?: string; // UUID
}

export interface DatasetResponse extends DatasetInDB {
  file_size_mb: number;
  columns: string[];
}

export interface DatasetList {
  id: string; // UUID
  organization_id: string; // UUID
  name: string;
  description?: string;
  file_name: string;
  file_size_mb: number;
  status: string;
  row_count?: number;
  column_count?: number;
  created_by?: string; // UUID
  created_at: string;
  updated_at: string;
}

export interface DatasetListResponse {
  items: DatasetList[];
  total: number;
  skip: number;
  limit: number;
}

export interface DatasetPreviewRecord {
  row_number: number;
  data: Record<string, unknown>;
  is_valid: boolean;
}

export interface DatasetPreview {
  columns: string[];
  records: DatasetPreviewRecord[];
  total_count: number;
  preview_count: number;
}

export interface DatasetStats {
  dataset_id: string;
  total_rows?: number;
  total_columns?: number;
  column_stats: Record<string, unknown>;
}

export interface DatasetReprocessRequest {
  validation_rules?: Record<string, unknown>;
  cleaning_options?: Record<string, unknown>;
  normalization_options?: Record<string, unknown>;
}

// ============================================================================
// Visualization Types
// ============================================================================

export interface ChartConfig {
  x_axis?: string;
  y_axis?: string | string[];
  grouping?: string;
  aggregation?: "sum" | "avg" | "count" | "min" | "max" | "median";
  filters?: Record<string, unknown>;
  colors?: string[];
  theme?: "light" | "dark";
  options?: Record<string, unknown>;
}

export interface VisualizationBase {
  name: string;
  description?: string;
  chart_type: ChartType;
  dataset_id: string; // UUID
  config: ChartConfig;
}

export type VisualizationCreate = VisualizationBase;

export interface VisualizationUpdate {
  name?: string;
  description?: string;
  chart_type?: ChartType;
  config?: ChartConfig;
}

export interface VisualizationInDB extends VisualizationBase {
  id: string; // UUID
  organization_id: string; // UUID
  created_by: string; // UUID
  created_at: string;
  updated_at: string;
}

export interface VisualizationResponse extends VisualizationInDB {
  chart_data?: Record<string, unknown>;
  dataset_name?: string;
  creator_name?: string;
}

export interface ChartSuggestion {
  chart_type: ChartType;
  title: string;
  config: ChartConfig;
  reasoning: string;
  confidence: number; // 0-1
  priority?: number;
  alternative_charts?: ChartType[];
}

export interface ChartSuggestionRequest {
  dataset_id: string; // UUID
  question?: string;
  use_ai?: boolean;
  max_suggestions?: number;
}

export interface ChartSuggestionsResponse {
  dataset_id: string; // UUID
  dataset_name: string;
  suggestions: ChartSuggestion[];
  total_count: number;
}

export interface VisualizationListResponse {
  items: VisualizationResponse[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface ChartDataExport {
  visualization_id: string; // UUID
  name: string;
  chart_type: ChartType;
  data: Record<string, unknown>;
  config: ChartConfig;
  exported_at: string;
}

// ============================================================================
// Insight Types
// ============================================================================

export type InsightType =
  | "trend"
  | "anomaly"
  | "correlation"
  | "distribution"
  | "outlier"
  | "pattern"
  | "recommendation";

export interface InsightBase {
  title: string;
  description: string;
  insight_type: InsightType;
  dataset_id: string; // UUID
  confidence: number; // 0-1
  supporting_data?: Record<string, unknown>;
}

export type InsightCreate = InsightBase;

export interface InsightUpdate {
  title?: string;
  description?: string;
  confidence?: number;
  supporting_data?: Record<string, unknown>;
  is_dismissed?: boolean;
}

export interface InsightInDB extends InsightBase {
  id: string; // UUID
  organization_id: string; // UUID
  created_by?: string; // UUID
  is_dismissed: boolean;
  created_at: string;
  updated_at: string;
}

export interface InsightResponse extends InsightInDB {
  dataset_name?: string;
  creator_name?: string;
}

// ============================================================================
// Permission & Role Types
// ============================================================================

export interface PermissionBase {
  code: string;
  name: string;
  description?: string;
  category: string;
}

export type PermissionCreate = PermissionBase;

export interface PermissionUpdate {
  name?: string;
  description?: string;
  category?: string;
}

export interface PermissionResponse extends PermissionBase {
  id: string; // UUID
  created_at: string;
  updated_at: string;
}

export interface PermissionListResponse {
  permissions: PermissionResponse[];
  total: number;
}

export interface RoleBase {
  name: string;
  description?: string;
  is_default: boolean;
}

export interface RoleCreate extends RoleBase {
  permission_codes?: string[];
}

export interface RoleUpdate {
  name?: string;
  description?: string;
  is_default?: boolean;
}

export interface RoleResponse extends RoleBase {
  id: string; // UUID
  organization_id: string; // UUID
  is_system: boolean;
  created_at: string;
  updated_at: string;
}

export interface RoleWithPermissions extends RoleResponse {
  permissions: PermissionResponse[];
}

export interface RoleListResponse {
  roles: RoleResponse[];
  total: number;
}

export interface AssignRoleRequest {
  role_id: string; // UUID
}

export interface AssignPermissionRequest {
  permission_code: string;
}

// ============================================================================
// API Error Types
// ============================================================================

export interface ApiError {
  error: string;
  detail?: string;
  field?: string;
  status?: number;
}

export class ApiException extends Error {
  status: number;
  error: string;
  detail?: string;
  field?: string;

  constructor(error: ApiError) {
    super(error.error);
    this.name = "ApiException";
    this.status = error.status || 500;
    this.error = error.error;
    this.detail = error.detail;
    this.field = error.field;
  }
}

// ============================================================================
// Type Guards
// ============================================================================

export function isApiError(error: unknown): error is ApiError {
  return (
    typeof error === "object" &&
    error !== null &&
    "error" in error &&
    typeof (error as ApiError).error === "string"
  );
}

export function isPaginatedResponse<T>(
  response: unknown
): response is PaginatedResponse<T> {
  return (
    typeof response === "object" &&
    response !== null &&
    "items" in response &&
    "total" in response &&
    "skip" in response &&
    "limit" in response &&
    Array.isArray((response as PaginatedResponse<T>).items)
  );
}
