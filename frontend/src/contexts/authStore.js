import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import api from '../services/api';

export const useAuthStore = create(
  persist(
    (set) => ({
      isAuthenticated: false,
      user: null,
      token: null,
      sessionUuid: null,
      
      login: async (username, password) => {
        try {
          const response = await api.post('/api/auth/login', { username, password });
          const { access_token, token_type, session_uuid } = response.data;
          
          // Set auth token in axios defaults for future requests
          api.defaults.headers.common['Authorization'] = `${token_type} ${access_token}`;
          
          // Get user info
          const userResponse = await api.get('/api/users/me');
          
          set({
            isAuthenticated: true,
            user: userResponse.data,
            token: access_token,
            sessionUuid: session_uuid,
          });
          
          return { success: true };
        } catch (error) {
          return { 
            success: false, 
            error: error.response?.data?.detail || 'Login failed. Please try again.'
          };
        }
      },
      
      register: async (username, email, password) => {
        try {
          await api.post('/api/auth/register', { username, email, password });
          return { success: true };
        } catch (error) {
          return { 
            success: false, 
            error: error.response?.data?.detail || 'Registration failed. Please try again.'
          };
        }
      },
      
      logout: () => {
        // Remove auth token from axios defaults
        delete api.defaults.headers.common['Authorization'];
        
        set({
          isAuthenticated: false,
          user: null,
          token: null,
          sessionUuid: null,
        });
      },
      
      // Setup auth on app init
      initAuth: () => {
        const state = useAuthStore.getState();
        if (state.token) {
          api.defaults.headers.common['Authorization'] = `Bearer ${state.token}`;
        }
      },
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({ 
        isAuthenticated: state.isAuthenticated,
        user: state.user,
        token: state.token,
        sessionUuid: state.sessionUuid,
      }),
    }
  )
);

// Initialize auth on import
useAuthStore.getState().initAuth();
