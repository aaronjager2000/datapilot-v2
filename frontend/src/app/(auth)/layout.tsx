/**
 * Auth Layout
 *
 * Beautiful centered card layout for authentication pages with:
 * - Gradient background
 * - Centered card container
 * - Logo and branding
 * - Footer with links
 * - Automatic redirect if already authenticated
 */

'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/lib/hooks/useAuth';
import { Card } from '@/components/ui/card';

interface AuthLayoutProps {
  children: React.ReactNode;
}

export default function AuthLayout({ children }: AuthLayoutProps) {
  const { isAuthenticated, isInitialized, isLoading } = useAuth();
  const router = useRouter();

  // Redirect to dashboard if already authenticated
  useEffect(() => {
    if (isInitialized && !isLoading && isAuthenticated) {
      router.push('/dashboard');
    }
  }, [isAuthenticated, isInitialized, isLoading, router]);

  // Show nothing while checking authentication
  if (!isInitialized || isLoading || isAuthenticated) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="relative flex min-h-screen flex-col items-center justify-center overflow-hidden">
      {/* Background Gradient */}
      <div className="absolute inset-0 -z-10 bg-gradient-to-br from-blue-50 via-white to-purple-50 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900" />

      {/* Decorative Blobs */}
      <div className="absolute -left-4 top-1/4 -z-10 h-72 w-72 rounded-full bg-blue-200/30 blur-3xl dark:bg-blue-900/20" />
      <div className="absolute -right-4 bottom-1/4 -z-10 h-72 w-72 rounded-full bg-purple-200/30 blur-3xl dark:bg-purple-900/20" />

      {/* Main Content Container */}
      <div className="w-full max-w-md px-4">
        {/* Logo */}
        <div className="mb-8 text-center">
          <Link href="/" className="inline-block">
            <div className="flex items-center justify-center gap-2">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary">
                <svg
                  className="h-6 w-6 text-primary-foreground"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
                  />
                </svg>
              </div>
              <span className="text-2xl font-bold text-foreground">DataPilot</span>
            </div>
          </Link>
          <p className="mt-2 text-sm text-muted-foreground">
            Transform your data into insights
          </p>
        </div>

        {/* Auth Card */}
        <Card className="shadow-xl">
          {children}
        </Card>

        {/* Footer Links */}
        <div className="mt-8 text-center text-sm text-muted-foreground">
          <div className="flex items-center justify-center gap-4">
            <Link
              href="/about"
              className="hover:text-foreground transition-colors"
            >
              About
            </Link>
            <span>•</span>
            <Link
              href="/privacy"
              className="hover:text-foreground transition-colors"
            >
              Privacy
            </Link>
            <span>•</span>
            <Link
              href="/terms"
              className="hover:text-foreground transition-colors"
            >
              Terms
            </Link>
            <span>•</span>
            <Link
              href="/contact"
              className="hover:text-foreground transition-colors"
            >
              Contact
            </Link>
          </div>
          <p className="mt-4 text-xs">
            � {new Date().getFullYear()} DataPilot. All rights reserved.
          </p>
        </div>
      </div>
    </div>
  );
}
