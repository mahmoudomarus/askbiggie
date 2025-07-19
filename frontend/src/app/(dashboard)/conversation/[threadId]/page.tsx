'use client';

import React, { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { ThreadSkeleton } from '@/components/thread/content/ThreadSkeleton';
import { ThreadContent } from '@/components/thread/content/ThreadContent';
import { ChatInput } from '@/components/thread/chat-input/chat-input';
import { useThreadQuery } from '@/hooks/react-query/threads/use-threads';
import { useMessagesQuery } from '@/hooks/react-query/threads/use-messages';
import { cn } from '@/lib/utils';
import { useIsMobile } from '@/hooks/use-mobile';
import { UnifiedMessage } from '@/app/(dashboard)/projects/[projectId]/thread/_types';
import { initiateAgent } from '@/lib/api';

interface ConversationPageProps {
  params: Promise<{ threadId: string }>;
}

export default function ConversationPage({ params }: ConversationPageProps) {
  const unwrappedParams = React.use(params);
  const { threadId } = unwrappedParams;
  const router = useRouter();
  const isMobile = useIsMobile();
  
  const [messages, setMessages] = useState<UnifiedMessage[]>([]);
  const [newMessage, setNewMessage] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const threadQuery = useThreadQuery(threadId);
  const messagesQuery = useMessagesQuery(threadId);

  useEffect(() => {
    if (threadQuery.data?.project_id) {
      // This thread has a project, redirect to project thread page
      router.replace(`/projects/${threadQuery.data.project_id}/thread/${threadId}`);
      return;
    }
  }, [threadQuery.data, threadId, router]);

  useEffect(() => {
    if (messagesQuery.data) {
      const unifiedMessages = (messagesQuery.data || [])
        .filter((msg: any) => msg.type !== 'status')
        .map((msg: any) => ({
          message_id: msg.message_id || null,
          thread_id: msg.thread_id || threadId,
          type: (msg.type || 'system') as UnifiedMessage['type'],
          is_llm_message: Boolean(msg.is_llm_message),
          content: msg.content || '',
          metadata: msg.metadata || '{}',
          created_at: msg.created_at || new Date().toISOString(),
          updated_at: msg.updated_at || new Date().toISOString(),
        }));

      setMessages(unifiedMessages);
      setIsLoading(false);
    }
  }, [messagesQuery.data, threadId]);

  // Ensure we reload messages when the page loads
  useEffect(() => {
    messagesQuery.refetch();
  }, [threadId]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmitMessage = async (message: string) => {
    if (!message.trim() || isSending) return;
    
    setIsSending(true);
    setNewMessage('');

    try {
      // Use the authenticated API function for Fast Biggie
      const formData = new FormData();
      formData.append('prompt', message);
      formData.append('model_name', 'claude-sonnet-4');
      formData.append('agent_id', 'fast_biggie');
      formData.append('thread_id', threadId); // continue existing thread
      formData.append('instance', 'single');

      const response = await initiateAgent(formData);

      // Refetch messages to get both user message and AI response
      await messagesQuery.refetch();
      scrollToBottom();
      
    } catch (error) {
      console.error('Error sending message:', error);
      alert(`Error: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setIsSending(false);
    }
  };

  if (isLoading || !threadQuery.data) {
    return <ThreadSkeleton isSidePanelOpen={false} />;
  }

  // If thread has project_id, let the redirect happen
  if (threadQuery.data.project_id) {
    return <ThreadSkeleton isSidePanelOpen={false} />;
  }

  return (
    <div className="flex h-screen flex-col">
      {/* Header */}
      <div className="border-b bg-background px-4 py-3">
        <div className="flex items-center justify-between">
          <h1 className="text-lg font-semibold">Fast Biggie Chat</h1>
          <button
            onClick={() => router.push('/dashboard')}
            className="text-sm text-muted-foreground hover:text-foreground"
          >
            ← Back to Dashboard
          </button>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-auto px-4 py-4">
        <ThreadContent
          messages={messages}
          streamingTextContent=""
          streamingToolCall={null}
          agentStatus="idle"
          handleToolClick={() => {}}
          handleOpenFileViewer={() => {}}
          readOnly={false}
          streamHookStatus="idle"
          sandboxId={null}
          project={null}
          debugMode={false}
          agentName="Fast Biggie"
          agentAvatar="🚀"
        />
        <div ref={messagesEndRef} />
      </div>

      {/* Chat Input */}
      <div className="border-t bg-background px-4 py-4">
        <div className={cn("mx-auto", isMobile ? "w-full" : "max-w-3xl")}>
          <ChatInput
            value={newMessage}
            onChange={setNewMessage}
            onSubmit={handleSubmitMessage}
            placeholder="Type your message..."
            loading={isSending}
            disabled={isSending}
            isAgentRunning={false}
            onStopAgent={() => {}}
            autoFocus={true}
            agentName="Fast Biggie"
            hideAttachments={true}
            hideAgentSelection={true}
          />
        </div>
      </div>
    </div>
  );
} 