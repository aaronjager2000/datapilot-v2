/**
 * Dashboard Layout
 *
 * Main dashboard layout with header, sidebar, and content area
 */

'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/hooks/useAuth';
import { Header } from '@/components/layout/Header';
import { Sidebar } from '@/components/layout/Sidebar';

interface DashboardLayoutProps {
  children: React.ReactNode;
}

export default function DashboardLayout({ children }: DashboardLayoutProps) {
  const { isAuthenticated, isInitialized, isLoading, initialize } = useAuth();
  const router = useRouter();
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  // Initialize auth and check authentication
  useEffect(() => {
    if (!isInitialized && !isLoading) {
      initialize();
    }
  }, [isInitialized, isLoading, initialize]);

  // Redirect to login if not authenticated
  useEffect(() => {
    if (isInitialized && !isLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, isInitialized, isLoading, router]);

  // Show loading state while checking authentication
  if (!isInitialized || isLoading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="text-center">
          <div className="mb-4 inline-block h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
          <p className="text-sm text-muted-foreground">Loading...</p>
        </div>
      </div>
    );
  }

  // Don't render dashboard if not authenticated
  if (!isAuthenticated) {
    return null;
  }

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      {/* Sidebar - Desktop */}
      <aside className="hidden md:flex md:w-64 md:flex-col">
        <Sidebar />
      </aside>

      {/* Sidebar - Mobile */}
      {isSidebarOpen && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 z-40 bg-black/50 md:hidden"
            onClick={() => setIsSidebarOpen(false)}
          />
          {/* Sliding sidebar */}
          <aside className="fixed inset-y-0 left-0 z-50 w-64 md:hidden">
            <Sidebar />
          </aside>
        </>
      )}

      {/* Main content area */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Header */}
        <Header onMenuClick={() => setIsSidebarOpen(!isSidebarOpen)} />

        {/* Page content */}
        <main className="flex-1 overflow-y-auto">
          <div className="container mx-auto p-6">{children}</div>
        </main>
      </div>
    </div>
  );
}
