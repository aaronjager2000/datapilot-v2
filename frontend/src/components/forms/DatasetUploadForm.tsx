/**
 * DatasetUploadForm Component
 *
 * Form for uploading datasets with drag-and-drop support
 */

'use client';

import { useState, useRef, useCallback, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { Upload, File, X, CheckCircle2, AlertCircle } from 'lucide-react';
import { useUploadDataset } from '@/lib/hooks/useDatasets';
import { UploadProgress } from '@/lib/api/datasets';
import { useWebSocket, WebSocketMessage } from '@/lib/hooks/useWebSocket';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Progress } from '@/components/ui/progress';
import { cn } from '@/lib/utils/cn';

// Validation Schema
const uploadSchema = z.object({
  name: z.string().min(1, 'Name is required').max(255, 'Name is too long'),
  description: z.string().max(1000, 'Description is too long').optional(),
});

type UploadFormData = z.infer<typeof uploadSchema>;

// Allowed file types
const ALLOWED_FILE_TYPES = [
  'text/csv',
  'application/vnd.ms-excel',
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  'application/json',
];

const ALLOWED_EXTENSIONS = ['.csv', '.xlsx', '.xls', '.json'];

// Max file size: 100MB
const MAX_FILE_SIZE = 100 * 1024 * 1024;

interface DatasetUploadFormProps {
  onSuccess?: () => void;
  onCancel?: () => void;
}

export function DatasetUploadForm({ onSuccess, onCancel }: DatasetUploadFormProps) {
  const [file, setFile] = useState<File | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<UploadProgress | null>(null);
  const [processingStatus, setProcessingStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [uploadedDatasetId, setUploadedDatasetId] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // WebSocket for real-time processing updates
  const handleWebSocketMessage = useCallback((message: WebSocketMessage) => {
    if (message.type === 'dataset_processing' && uploadedDatasetId) {
      const data = message.data as { dataset_id: string; status: string; progress?: number };
      if (data.dataset_id === uploadedDatasetId) {
        setProcessingStatus(data.status);
        if (data.status === 'ready') {
          setSuccess(true);
        } else if (data.status === 'error') {
          setError('Dataset processing failed');
        }
      }
    }
  }, [uploadedDatasetId]);

  const { isConnected } = useWebSocket(handleWebSocketMessage, {
    channels: ['datasets'],
    autoReconnect: true,
  });

  const {
    register,
    handleSubmit,
    formState: { errors },
    setValue,
  } = useForm<UploadFormData>({
    resolver: zodResolver(uploadSchema),
    defaultValues: {
      name: '',
      description: '',
    },
  });

  const uploadMutation = useUploadDataset(
    (progress) => setUploadProgress(progress),
    {
      onSuccess: (dataset) => {
        setUploadedDatasetId(dataset.id);
        setProcessingStatus('processing');
        setError(null);
        // Don't immediately set success - wait for WebSocket update
      },
      onError: (err) => {
        setError(err.detail || 'Failed to upload dataset');
        setUploadProgress(null);
      },
    }
  );

  // Auto-close on success after delay
  useEffect(() => {
    if (success) {
      const timeout = setTimeout(() => {
        onSuccess?.();
      }, 2000);
      return () => clearTimeout(timeout);
    }
  }, [success, onSuccess]);

  const validateFile = (file: File): string | null => {
    // Check file type
    const extension = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
    if (!ALLOWED_FILE_TYPES.includes(file.type) && !ALLOWED_EXTENSIONS.includes(extension)) {
      return 'Invalid file type. Please upload a CSV, Excel, or JSON file.';
    }

    // Check file size
    if (file.size > MAX_FILE_SIZE) {
      return `File is too large. Maximum size is ${MAX_FILE_SIZE / 1024 / 1024}MB.`;
    }

    return null;
  };

  const handleFileSelect = useCallback((selectedFile: File) => {
    const validationError = validateFile(selectedFile);
    if (validationError) {
      setError(validationError);
      return;
    }

    setFile(selectedFile);
    setError(null);
    setSuccess(false);
    setUploadProgress(null);

    // Auto-fill name if empty
    const nameWithoutExtension = selectedFile.name.substring(
      0,
      selectedFile.name.lastIndexOf('.')
    );
    setValue('name', nameWithoutExtension);
  }, [setValue]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);

    const droppedFiles = Array.from(e.dataTransfer.files);
    if (droppedFiles.length > 0) {
      handleFileSelect(droppedFiles[0]);
    }
  }, [handleFileSelect]);

  const handleFileInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = e.target.files;
    if (selectedFiles && selectedFiles.length > 0) {
      handleFileSelect(selectedFiles[0]);
    }
  }, [handleFileSelect]);

  const handleRemoveFile = useCallback(() => {
    setFile(null);
    setError(null);
    setSuccess(false);
    setUploadProgress(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  }, []);

  const onSubmit = async (data: UploadFormData) => {
    if (!file) {
      setError('Please select a file to upload');
      return;
    }

    // Generate a simple hash from file metadata
    const fileHash = `${file.name}-${file.size}-${file.lastModified}`;

    await uploadMutation.mutateAsync({
      file,
      metadata: {
        name: data.name,
        description: data.description || undefined,
        file_name: file.name,
        file_hash: fileHash,
      },
    });
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  const isUploading = uploadMutation.isPending;
  const isDisabled = isUploading || success;

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
      {/* File Drop Zone */}
      <div className="space-y-2">
        <Label>File</Label>
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => !isDisabled && fileInputRef.current?.click()}
          className={cn(
            'relative rounded-lg border-2 border-dashed p-8 text-center transition-colors cursor-pointer',
            isDragOver && 'border-primary bg-primary/5',
            !isDragOver && 'border-muted-foreground/25 hover:border-primary/50',
            isDisabled && 'opacity-50 cursor-not-allowed'
          )}
        >
          <input
            ref={fileInputRef}
            type="file"
            onChange={handleFileInputChange}
            accept={ALLOWED_EXTENSIONS.join(',')}
            disabled={isDisabled}
            className="hidden"
          />

          {!file ? (
            <div className="flex flex-col items-center gap-2">
              <div className="rounded-full bg-primary/10 p-3">
                <Upload className="h-6 w-6 text-primary" />
              </div>
              <div>
                <p className="font-medium">Drop your file here, or click to browse</p>
                <p className="text-sm text-muted-foreground mt-1">
                  Supports CSV, Excel, and JSON files (max {MAX_FILE_SIZE / 1024 / 1024}MB)
                </p>
              </div>
            </div>
          ) : (
            <div className="flex items-center gap-4">
              <div className="shrink-0 rounded-full bg-primary/10 p-2">
                <File className="h-5 w-5 text-primary" />
              </div>
              <div className="flex-1 text-left">
                <p className="font-medium">{file.name}</p>
                <p className="text-sm text-muted-foreground">
                  {formatFileSize(file.size)}
                </p>
              </div>
              {!isDisabled && (
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleRemoveFile();
                  }}
                >
                  <X className="h-4 w-4" />
                </Button>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Name Field */}
      <div className="space-y-2">
        <Label htmlFor="name">Dataset Name *</Label>
        <Input
          id="name"
          placeholder="My Dataset"
          {...register('name')}
          disabled={isDisabled}
          aria-invalid={errors.name ? 'true' : 'false'}
        />
        {errors.name && (
          <p className="text-sm text-destructive">{errors.name.message}</p>
        )}
      </div>

      {/* Description Field */}
      <div className="space-y-2">
        <Label htmlFor="description">Description</Label>
        <textarea
          id="description"
          placeholder="Add a description for this dataset..."
          {...register('description')}
          disabled={isDisabled}
          rows={3}
          className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
        />
        {errors.description && (
          <p className="text-sm text-destructive">{errors.description.message}</p>
        )}
      </div>

      {/* Upload Progress */}
      {uploadProgress && (
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Uploading...</span>
            <span className="font-medium">{uploadProgress.percentage}%</span>
          </div>
          <Progress value={uploadProgress.percentage} />
        </div>
      )}

      {/* Processing Status */}
      {processingStatus && !success && (
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">
              {processingStatus === 'processing' ? 'Processing dataset...' : `Status: ${processingStatus}`}
            </span>
            {isConnected && (
              <span className="text-xs text-green-600 dark:text-green-400">● Live</span>
            )}
          </div>
          {processingStatus === 'processing' && (
            <Progress value={undefined} className="animate-pulse" />
          )}
        </div>
      )}

      {/* Success Message */}
      {success && (
        <div className="rounded-md bg-green-50 dark:bg-green-950/20 p-3 flex items-center gap-2 text-green-700 dark:text-green-400">
          <CheckCircle2 className="h-5 w-5" />
          <p className="text-sm font-medium">Dataset uploaded successfully!</p>
        </div>
      )}

      {/* Error Message */}
      {error && (
        <div className="rounded-md bg-destructive/10 p-3 flex items-start gap-2 text-destructive">
          <AlertCircle className="h-5 w-5 shrink-0 mt-0.5" />
          <p className="text-sm">{error}</p>
        </div>
      )}

      {/* Form Actions */}
      <div className="flex gap-3 justify-end">
        <Button
          type="button"
          variant="outline"
          onClick={onCancel}
          disabled={isUploading}
        >
          Cancel
        </Button>
        <Button type="submit" disabled={isDisabled || !file}>
          {isUploading ? (
            <>
              <span className="mr-2 h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
              Uploading...
            </>
          ) : (
            <>
              <Upload className="mr-2 h-4 w-4" />
              Upload Dataset
            </>
          )}
        </Button>
      </div>
    </form>
  );
}
