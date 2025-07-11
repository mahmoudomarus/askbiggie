import { agentPlaygroundFlagFrontend } from '@/flags';
import { isFlagEnabled } from '@/lib/feature-flags';
import { Metadata } from 'next';
import { redirect } from 'next/navigation';

export const metadata: Metadata = {
  title: 'Agent Conversation | Bignoodle AI',
  description: 'Interactive agent conversation powered by Bignoodle AI',
  openGraph: {
    title: 'Agent Conversation | Bignoodle AI',
    description: 'Interactive agent conversation powered by Bignoodle AI',
    type: 'website',
  },
};

export default async function AgentsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}
