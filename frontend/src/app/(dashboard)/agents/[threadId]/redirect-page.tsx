'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useThreadQuery } from '@/hooks/react-query/threads/use-threads';
import { ThreadSkeleton } from '@/components/thread/content/ThreadSkeleton';

interface RedirectPageProps {
  threadId: string;
}

export function RedirectPage({ threadId }: RedirectPageProps) {
  const router = useRouter();
  const threadQuery = useThreadQuery(threadId);

  useEffect(() => {
    if (threadQuery.data) {
      if (threadQuery.data.project_id) {
        // Thread has project - redirect to project thread page
        router.replace(`/projects/${threadQuery.data.project_id}/thread/${threadId}`);
      } else {
        // Fast Biggie thread without project - redirect to conversation page
        router.replace(`/conversation/${threadId}`);
      }
    }
  }, [threadQuery.data, threadId, router]);

  if (threadQuery.isError) {
    router.replace('/dashboard');
    return null;
  }
  return <ThreadSkeleton isSidePanelOpen={false} />;
} 