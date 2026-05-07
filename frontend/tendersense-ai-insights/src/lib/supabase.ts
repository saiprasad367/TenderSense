import { createClient } from '@supabase/supabase-js';

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || 'https://jzusgkywmhjbtjsdtmid.supabase.co';
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY || 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imp6dXNna3l3bWhqYnRqc2R0bWlkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzc4OTg1MDMsImV4cCI6MjA5MzQ3NDUwM30.h1ipPMjZGkRkre09XR99Z_lZVwpBkt9y-VS3qFmSBBs';

if (!supabaseUrl || !supabaseAnonKey) {
  console.warn('Supabase credentials missing. Auth will not work properly.');
}

export const supabase = createClient(
  supabaseUrl,
  supabaseAnonKey,
  {
    global: {
      headers: { 'Accept': 'application/json' }
    }
  }
);
