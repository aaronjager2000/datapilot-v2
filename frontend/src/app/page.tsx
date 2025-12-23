/**
 * Landing Page
 *
 * Main public-facing page
 */

import Link from "next/link";
import {
  ArrowRight,
  BarChart3,
  Database,
  Lightbulb,
  Shield,
  Users,
  Sparkles,
  CheckCircle2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export default function LandingPage() {
  return (
    <div className="flex flex-col min-h-screen">
      {/* Navigation */}
      <nav className="border-b sticky top-0 bg-background/95 backdrop-blur supports-backdrop-filter:bg-background/60 z-50">
        <div className="container mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="p-2 rounded-lg bg-primary">
              <BarChart3 className="h-5 w-5 text-primary-foreground" />
            </div>
            <span className="text-xl font-bold">DataPilot</span>
          </div>
          <div className="flex items-center gap-4">
            <Link href="/login">
              <Button variant="ghost">Sign In</Button>
            </Link>
            <Link href="/register">
              <Button>
                Get Started
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="container mx-auto px-4 py-20 md:py-32">
        <div className="max-w-5xl mx-auto text-center space-y-8">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary/10 text-primary text-sm font-medium">
            <Sparkles className="h-4 w-4" />
            AI-Powered Data Analytics
          </div>
          <h1 className="text-5xl md:text-7xl font-bold tracking-tight">
            Transform Your Data Into
            <span className="block mt-2 bg-linear-to-r from-primary to-purple-600 bg-clip-text text-transparent">
              Actionable Insights
            </span>
          </h1>
          <p className="text-xl text-muted-foreground max-w-3xl mx-auto">
            DataPilot empowers teams to analyze, visualize, and understand their
            data with cutting-edge AI. No data science degree required.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center pt-4">
            <Link href="/register">
              <Button size="lg" className="text-lg h-12 px-8">
                Start Free Trial
                <ArrowRight className="ml-2 h-5 w-5" />
              </Button>
            </Link>
            <Link href="#features">
              <Button size="lg" variant="outline" className="text-lg h-12 px-8">
                Learn More
              </Button>
            </Link>
          </div>
          <div className="flex items-center justify-center gap-8 pt-8 text-sm text-muted-foreground">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-green-600" />
              No credit card required
            </div>
            <div className="flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-green-600" />
              14-day free trial
            </div>
            <div className="flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-green-600" />
              Cancel anytime
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="bg-muted/50 py-20 md:py-32">
        <div className="container mx-auto px-4">
          <div className="max-w-5xl mx-auto">
            <div className="text-center space-y-4 mb-16">
              <Badge variant="outline" className="text-sm">
                Features
              </Badge>
              <h2 className="text-4xl md:text-5xl font-bold">
                Everything you need to succeed
              </h2>
              <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
                Powerful tools designed for modern data teams
              </p>
            </div>

            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
              {/* Feature Cards */}
              <Card className="border-2 hover:border-primary/50 transition-colors">
                <CardHeader>
                  <div className="p-3 w-fit rounded-lg bg-blue-100 dark:bg-blue-950 mb-4">
                    <Database className="h-6 w-6 text-blue-600 dark:text-blue-400" />
                  </div>
                  <CardTitle>Dataset Management</CardTitle>
                  <CardDescription>
                    Upload, organize, and process datasets with ease. Support for
                    CSV, Excel, JSON, and more.
                  </CardDescription>
                </CardHeader>
              </Card>

              <Card className="border-2 hover:border-primary/50 transition-colors">
                <CardHeader>
                  <div className="p-3 w-fit rounded-lg bg-purple-100 dark:bg-purple-950 mb-4">
                    <Sparkles className="h-6 w-6 text-purple-600 dark:text-purple-400" />
                  </div>
                  <CardTitle>AI-Powered Insights</CardTitle>
                  <CardDescription>
                    Let AI analyze your data and discover patterns, trends, and
                    anomalies automatically.
                  </CardDescription>
                </CardHeader>
              </Card>

              <Card className="border-2 hover:border-primary/50 transition-colors">
                <CardHeader>
                  <div className="p-3 w-fit rounded-lg bg-green-100 dark:bg-green-950 mb-4">
                    <BarChart3 className="h-6 w-6 text-green-600 dark:text-green-400" />
                  </div>
                  <CardTitle>Beautiful Visualizations</CardTitle>
                  <CardDescription>
                    Create stunning charts and graphs with our intuitive
                    visualization builder.
                  </CardDescription>
                </CardHeader>
              </Card>

              <Card className="border-2 hover:border-primary/50 transition-colors">
                <CardHeader>
                  <div className="p-3 w-fit rounded-lg bg-orange-100 dark:bg-orange-950 mb-4">
                    <Lightbulb className="h-6 w-6 text-orange-600 dark:text-orange-400" />
                  </div>
                  <CardTitle>Natural Language Queries</CardTitle>
                  <CardDescription>
                    Ask questions about your data in plain English. Get instant
                    answers powered by AI.
                  </CardDescription>
                </CardHeader>
              </Card>

              <Card className="border-2 hover:border-primary/50 transition-colors">
                <CardHeader>
                  <div className="p-3 w-fit rounded-lg bg-pink-100 dark:bg-pink-950 mb-4">
                    <Users className="h-6 w-6 text-pink-600 dark:text-pink-400" />
                  </div>
                  <CardTitle>Team Collaboration</CardTitle>
                  <CardDescription>
                    Share insights, collaborate on visualizations, and manage team
                    access with ease.
                  </CardDescription>
                </CardHeader>
              </Card>

              <Card className="border-2 hover:border-primary/50 transition-colors">
                <CardHeader>
                  <div className="p-3 w-fit rounded-lg bg-red-100 dark:bg-red-950 mb-4">
                    <Shield className="h-6 w-6 text-red-600 dark:text-red-400" />
                  </div>
                  <CardTitle>Enterprise Security</CardTitle>
                  <CardDescription>
                    Bank-level encryption, role-based access control, and SOC 2
                    compliance.
                  </CardDescription>
                </CardHeader>
              </Card>
            </div>
          </div>
        </div>
      </section>

      {/* Stats Section */}
      <section className="py-20 md:py-32">
        <div className="container mx-auto px-4">
          <div className="max-w-5xl mx-auto">
            <div className="grid md:grid-cols-4 gap-8 text-center">
              <div className="space-y-2">
                <div className="text-4xl md:text-5xl font-bold text-primary">
                  10M+
                </div>
                <div className="text-muted-foreground">Rows Processed</div>
              </div>
              <div className="space-y-2">
                <div className="text-4xl md:text-5xl font-bold text-primary">
                  50K+
                </div>
                <div className="text-muted-foreground">
                  Insights Generated
                </div>
              </div>
              <div className="space-y-2">
                <div className="text-4xl md:text-5xl font-bold text-primary">
                  99.9%
                </div>
                <div className="text-muted-foreground">Uptime</div>
              </div>
              <div className="space-y-2">
                <div className="text-4xl md:text-5xl font-bold text-primary">
                  24/7
                </div>
                <div className="text-muted-foreground">Support</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section className="bg-muted/50 py-20 md:py-32">
        <div className="container mx-auto px-4">
          <div className="max-w-5xl mx-auto">
            <div className="text-center space-y-4 mb-16">
              <Badge variant="outline" className="text-sm">
                How It Works
              </Badge>
              <h2 className="text-4xl md:text-5xl font-bold">
                Get started in minutes
              </h2>
              <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
                Simple steps to unlock the power of your data
              </p>
            </div>

            <div className="grid md:grid-cols-3 gap-8">
              <div className="relative">
                <div className="flex flex-col items-center text-center space-y-4">
                  <div className="w-16 h-16 rounded-full bg-primary text-primary-foreground flex items-center justify-center text-2xl font-bold">
                    1
                  </div>
                  <h3 className="text-xl font-semibold">Upload Your Data</h3>
                  <p className="text-muted-foreground">
                    Drag and drop your files or connect to your data sources.
                    We support all major formats.
                  </p>
                </div>
              </div>

              <div className="relative">
                <div className="flex flex-col items-center text-center space-y-4">
                  <div className="w-16 h-16 rounded-full bg-primary text-primary-foreground flex items-center justify-center text-2xl font-bold">
                    2
                  </div>
                  <h3 className="text-xl font-semibold">Analyze with AI</h3>
                  <p className="text-muted-foreground">
                    Our AI automatically analyzes your data and generates
                    insights in seconds.
                  </p>
                </div>
              </div>

              <div className="relative">
                <div className="flex flex-col items-center text-center space-y-4">
                  <div className="w-16 h-16 rounded-full bg-primary text-primary-foreground flex items-center justify-center text-2xl font-bold">
                    3
                  </div>
                  <h3 className="text-xl font-semibold">Share & Collaborate</h3>
                  <p className="text-muted-foreground">
                    Create visualizations, share insights, and make data-driven
                    decisions together.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Pricing Preview */}
      <section className="py-20 md:py-32">
        <div className="container mx-auto px-4">
          <div className="max-w-5xl mx-auto">
            <div className="text-center space-y-4 mb-16">
              <Badge variant="outline" className="text-sm">
                Pricing
              </Badge>
              <h2 className="text-4xl md:text-5xl font-bold">
                Plans for every team
              </h2>
              <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
                Start free, upgrade as you grow
              </p>
            </div>

            <div className="grid md:grid-cols-3 gap-6">
              {/* Free Plan */}
              <Card>
                <CardHeader>
                  <CardTitle>Free</CardTitle>
                  <div className="mt-4">
                    <span className="text-4xl font-bold">$0</span>
                    <span className="text-muted-foreground">/month</span>
                  </div>
                  <CardDescription>Perfect for getting started</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <ul className="space-y-2">
                    <li className="flex items-center gap-2">
                      <CheckCircle2 className="h-4 w-4 text-green-600" />
                      <span className="text-sm">5 datasets</span>
                    </li>
                    <li className="flex items-center gap-2">
                      <CheckCircle2 className="h-4 w-4 text-green-600" />
                      <span className="text-sm">1 GB storage</span>
                    </li>
                    <li className="flex items-center gap-2">
                      <CheckCircle2 className="h-4 w-4 text-green-600" />
                      <span className="text-sm">Basic visualizations</span>
                    </li>
                    <li className="flex items-center gap-2">
                      <CheckCircle2 className="h-4 w-4 text-green-600" />
                      <span className="text-sm">Community support</span>
                    </li>
                  </ul>
                  <Link href="/register">
                    <Button className="w-full" variant="outline">
                      Get Started
                    </Button>
                  </Link>
                </CardContent>
              </Card>

              {/* Pro Plan */}
              <Card className="border-primary border-2 relative">
                <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                  <Badge variant="default">Most Popular</Badge>
                </div>
                <CardHeader>
                  <CardTitle>Pro</CardTitle>
                  <div className="mt-4">
                    <span className="text-4xl font-bold">$29</span>
                    <span className="text-muted-foreground">/month</span>
                  </div>
                  <CardDescription>For growing teams</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <ul className="space-y-2">
                    <li className="flex items-center gap-2">
                      <CheckCircle2 className="h-4 w-4 text-green-600" />
                      <span className="text-sm">100 datasets</span>
                    </li>
                    <li className="flex items-center gap-2">
                      <CheckCircle2 className="h-4 w-4 text-green-600" />
                      <span className="text-sm">50 GB storage</span>
                    </li>
                    <li className="flex items-center gap-2">
                      <CheckCircle2 className="h-4 w-4 text-green-600" />
                      <span className="text-sm">Advanced AI insights</span>
                    </li>
                    <li className="flex items-center gap-2">
                      <CheckCircle2 className="h-4 w-4 text-green-600" />
                      <span className="text-sm">Priority support</span>
                    </li>
                    <li className="flex items-center gap-2">
                      <CheckCircle2 className="h-4 w-4 text-green-600" />
                      <span className="text-sm">10 team members</span>
                    </li>
                  </ul>
                  <Link href="/register">
                    <Button className="w-full">Start Free Trial</Button>
                  </Link>
                </CardContent>
              </Card>

              {/* Enterprise Plan */}
              <Card>
                <CardHeader>
                  <CardTitle>Enterprise</CardTitle>
                  <div className="mt-4">
                    <span className="text-4xl font-bold">$99</span>
                    <span className="text-muted-foreground">/month</span>
                  </div>
                  <CardDescription>For large organizations</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <ul className="space-y-2">
                    <li className="flex items-center gap-2">
                      <CheckCircle2 className="h-4 w-4 text-green-600" />
                      <span className="text-sm">Unlimited datasets</span>
                    </li>
                    <li className="flex items-center gap-2">
                      <CheckCircle2 className="h-4 w-4 text-green-600" />
                      <span className="text-sm">500 GB storage</span>
                    </li>
                    <li className="flex items-center gap-2">
                      <CheckCircle2 className="h-4 w-4 text-green-600" />
                      <span className="text-sm">Custom integrations</span>
                    </li>
                    <li className="flex items-center gap-2">
                      <CheckCircle2 className="h-4 w-4 text-green-600" />
                      <span className="text-sm">24/7 support</span>
                    </li>
                    <li className="flex items-center gap-2">
                      <CheckCircle2 className="h-4 w-4 text-green-600" />
                      <span className="text-sm">Unlimited users</span>
                    </li>
                  </ul>
                  <Link href="/register">
                    <Button className="w-full" variant="outline">
                      Contact Sales
                    </Button>
                  </Link>
                </CardContent>
              </Card>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="bg-primary text-primary-foreground py-20 md:py-32">
        <div className="container mx-auto px-4">
          <div className="max-w-3xl mx-auto text-center space-y-8">
            <h2 className="text-4xl md:text-5xl font-bold">
              Ready to transform your data?
            </h2>
            <p className="text-xl opacity-90">
              Join thousands of teams already making smarter decisions with
              DataPilot
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Link href="/register">
                <Button
                  size="lg"
                  variant="secondary"
                  className="text-lg h-12 px-8"
                >
                  Start Free Trial
                  <ArrowRight className="ml-2 h-5 w-5" />
                </Button>
              </Link>
              <Link href="/login">
                <Button
                  size="lg"
                  variant="outline"
                  className="text-lg h-12 px-8 border-primary-foreground text-primary-foreground hover:bg-primary-foreground hover:text-primary"
                >
                  Sign In
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t py-12 bg-muted/30">
        <div className="container mx-auto px-4">
          <div className="grid md:grid-cols-4 gap-8">
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <div className="p-2 rounded-lg bg-primary">
                  <BarChart3 className="h-5 w-5 text-primary-foreground" />
                </div>
                <span className="text-xl font-bold">DataPilot</span>
              </div>
              <p className="text-sm text-muted-foreground">
                AI-powered data analytics platform for modern teams
              </p>
            </div>

            <div>
              <h3 className="font-semibold mb-4">Product</h3>
              <ul className="space-y-2 text-sm text-muted-foreground">
                <li>
                  <Link href="#features" className="hover:text-foreground">
                    Features
                  </Link>
                </li>
                <li>
                  <Link href="/pricing" className="hover:text-foreground">
                    Pricing
                  </Link>
                </li>
                <li>
                  <Link href="/docs" className="hover:text-foreground">
                    Documentation
                  </Link>
                </li>
              </ul>
            </div>

            <div>
              <h3 className="font-semibold mb-4">Company</h3>
              <ul className="space-y-2 text-sm text-muted-foreground">
                <li>
                  <Link href="/about" className="hover:text-foreground">
                    About
                  </Link>
                </li>
                <li>
                  <Link href="/blog" className="hover:text-foreground">
                    Blog
                  </Link>
                </li>
                <li>
                  <Link href="/contact" className="hover:text-foreground">
                    Contact
                  </Link>
                </li>
              </ul>
            </div>

            <div>
              <h3 className="font-semibold mb-4">Legal</h3>
              <ul className="space-y-2 text-sm text-muted-foreground">
                <li>
                  <Link href="/privacy" className="hover:text-foreground">
                    Privacy Policy
                  </Link>
                </li>
                <li>
                  <Link href="/terms" className="hover:text-foreground">
                    Terms of Service
                  </Link>
                </li>
                <li>
                  <Link href="/security" className="hover:text-foreground">
                    Security
                  </Link>
                </li>
              </ul>
            </div>
          </div>

          <div className="mt-12 pt-8 border-t text-center text-sm text-muted-foreground">
            <p>© 2024 DataPilot. All rights reserved.</p>
          </div>
        </div>
      </footer>
    </div>
  );
}
