import React, { createContext, useContext, useEffect, useState } from 'react';
import { User } from '@supabase/supabase-js';
import { supabase } from "@/lib/supabase";
import { api } from '@/lib/api';

interface AuthContextType {
  user: User | null;
  role: string | null;
  department: string | null;
  loading: boolean;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [role, setRole] = useState<string | null>(null);
  const [department, setDepartment] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check active sessions and sets the user
    const initAuth = async () => {
      try {
        const { data: { session } } = await supabase.auth.getSession();
        if (session?.user) {
          setUser(session.user);
          // Don't await here to prevent blocking the entire app if the profile fetch is slow
          fetchProfile(session.user);
        }
      } catch (err) {
        console.error("Initial auth failed:", err);
      } finally {
        setLoading(false);
      }
    };

    initAuth();

    // Listen for changes on auth state (sign in, sign out, etc.)
    const { data: { subscription } } = supabase.auth.onAuthStateChange(async (event, session) => {
      if (session?.user) {
        setUser(session.user);
        fetchProfile(session.user);
      } else {
        setUser(null);
        setRole(null);
        setDepartment(null);
      }
      setLoading(false);
    });

    return () => subscription.unsubscribe();
  }, []);

  const fetchProfile = async (currentUser: User) => {
    try {
      // 1. Initial fallback from metadata (available immediately after login/signup)
      const metaRole = currentUser.user_metadata?.role;
      const metaDept = currentUser.user_metadata?.department;
      
      if (metaRole) setRole(metaRole);
      if (metaDept) setDepartment(metaDept);

      // 2. Fetch from DB for ground truth
      const { data, error } = await supabase
        .from('users')
        .select('role, department')
        .eq('id', currentUser.id)
        .single();
      
      if (error) {
        console.warn('Profile sync in progress or inaccessible:', error.message);
        // If we don't have metadata role and DB fetch failed, then default to viewer
        if (!metaRole) setRole('viewer');
        return;
      }
      
      if (data) {
        setRole(data.role);
        setDepartment(data.department);
      }
    } catch (err) {
      console.error('Error fetching user profile:', err);
      if (!role) setRole('viewer');
    }
  };

  const signOut = async () => {
    await supabase.auth.signOut();
  };

  return (
    <AuthContext.Provider value={{ user, role, department, loading, signOut }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
