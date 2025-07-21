'use client';

import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  ReactNode,
} from 'react';
import { createClient } from '@/lib/supabase/client';
import { User, Session } from '@supabase/supabase-js';
import { SupabaseClient } from '@supabase/supabase-js';

type AuthContextType = {
  supabase: SupabaseClient;
  session: Session | null;
  user: User | null;
  isLoading: boolean;
  signOut: () => Promise<void>;
  refreshSession: () => Promise<void>;
};

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const supabase = createClient();
  const [session, setSession] = useState<Session | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Function to refresh session manually
  const refreshSession = async () => {
    try {
      console.log('[AUTH] Manually refreshing session...');
      const { data, error } = await supabase.auth.refreshSession();
      
      if (error) {
        console.error('[AUTH] Session refresh error:', error);
        // If refresh fails, try to get current session
        const { data: { session: currentSession } } = await supabase.auth.getSession();
        setSession(currentSession);
        setUser(currentSession?.user ?? null);
      } else {
        console.log('[AUTH] Session refreshed successfully');
        setSession(data.session);
        setUser(data.session?.user ?? null);
      }
    } catch (error) {
      console.error('[AUTH] Error refreshing session:', error);
    }
  };

  useEffect(() => {
    const getInitialSession = async () => {
      try {
        console.log('[AUTH] Getting initial session...');
        const {
          data: { session: currentSession },
          error
        } = await supabase.auth.getSession();
        
        if (error) {
          console.error('[AUTH] Error getting session:', error);
        }
        
        console.log('[AUTH] Initial session:', currentSession ? 'Found' : 'None');
        setSession(currentSession);
        setUser(currentSession?.user ?? null);
      } catch (error) {
        console.error('[AUTH] Failed to get initial session:', error);
      } finally {
        setIsLoading(false);
      }
    };

    getInitialSession();

    const { data: authListener } = supabase.auth.onAuthStateChange(
      (event, newSession) => {
        console.log('[AUTH] Auth state change:', event, newSession ? 'Session exists' : 'No session');
        
        setSession(newSession);
        setUser(newSession?.user ?? null);
        
        // Update loading state only on initial load
        if (isLoading) setIsLoading(false);
        
        // Handle token refresh events
        if (event === 'TOKEN_REFRESHED' && newSession) {
          console.log('[AUTH] Token refreshed successfully');
        } else if (event === 'SIGNED_OUT') {
          console.log('[AUTH] User signed out');
        } else if (event === 'SIGNED_IN' && newSession) {
          console.log('[AUTH] User signed in');
        }
      },
    );

    // Set up periodic session check
    const sessionCheckInterval = setInterval(async () => {
      const { data: { session: currentSession } } = await supabase.auth.getSession();
      
      // Check if session is about to expire (within 5 minutes)
      if (currentSession?.expires_at) {
        const expiresAt = new Date(currentSession.expires_at * 1000);
        const now = new Date();
        const fiveMinutesFromNow = new Date(now.getTime() + 5 * 60 * 1000);
        
        if (expiresAt < fiveMinutesFromNow) {
          console.log('[AUTH] Session expiring soon, refreshing...');
          await refreshSession();
        }
      }
    }, 60000); // Check every minute

    return () => {
      authListener?.subscription.unsubscribe();
      clearInterval(sessionCheckInterval);
    };
  }, [supabase, isLoading]);

  const signOut = async () => {
    console.log('[AUTH] Signing out...');
    await supabase.auth.signOut();
    // State updates will be handled by onAuthStateChange
  };

  const value = {
    supabase,
    session,
    user,
    isLoading,
    signOut,
    refreshSession,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
