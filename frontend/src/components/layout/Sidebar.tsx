/**
 * Sidebar Component
 *
 * Navigation sidebar for dashboard with route highlighting
 */

'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils/cn';
import { useAuth } from '@/lib/hooks/useAuth';
import {
  LayoutDashboard,
  Database,
  BarChart3,
  Lightbulb,
  Users,
  Settings,
  CreditCard,
} from 'lucide-react';
import { Separator } from '@/components/ui/separator';

const navigationItems = [
  {
    name: 'Dashboard',
    href: '/dashboard',
    icon: LayoutDashboard,
  },
  {
    name: 'Datasets',
    href: '/datasets',
    icon: Database,
  },
  {
    name: 'Visualizations',
    href: '/visualizations',
    icon: BarChart3,
  },
  {
    name: 'Insights',
    href: '/insights',
    icon: Lightbulb,
  },
  {
    name: 'Team',
    href: '/team',
    icon: Users,
  },
  {
    name: 'Settings',
    href: '/settings',
    icon: Settings,
  },
  {
    name: 'Billing',
    href: '/billing',
    icon: CreditCard,
  },
];

interface SidebarProps {
  className?: string;
}

export function Sidebar({ className }: SidebarProps) {
  const pathname = usePathname();
  const { getOrganization } = useAuth();
  const organization = getOrganization();

  return (
    <div className={cn('flex h-full w-64 flex-col bg-card border-r', className)}>
      {/* Organization Info */}
      <div className="p-6">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary">
            <BarChart3 className="h-6 w-6 text-primary-foreground" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold truncate">
              {organization?.name || 'DataPilot'}
            </p>
            <p className="text-xs text-muted-foreground truncate">
              {organization?.slug || 'organization'}
            </p>
          </div>
        </div>
      </div>

      <Separator />

      {/* Navigation */}
      <nav className="flex-1 space-y-1 p-4">
        {navigationItems.map((item) => {
          const isActive = pathname === item.href || pathname?.startsWith(item.href + '/');
          const Icon = item.icon;

          return (
            <Link
              key={item.name}
              href={item.href}
              className={cn(
                'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                isActive
                  ? 'bg-primary text-primary-foreground'
                  : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
              )}
            >
              <Icon className="h-5 w-5" />
              <span>{item.name}</span>
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="p-4">
        <div className="rounded-lg bg-muted p-4">
          <p className="text-xs font-medium">Need help?</p>
          <p className="mt-1 text-xs text-muted-foreground">
            Check our{' '}
            <Link href="/docs" className="text-primary hover:underline">
              documentation
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
