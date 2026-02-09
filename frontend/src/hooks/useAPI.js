/**
 * Custom React Query hooks for API calls
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../services/api';

/**
 * Hook for health check
 */
export function useHealthCheck() {
  return useQuery({
    queryKey: ['health'],
    queryFn: apiClient.healthCheck,
    refetchInterval: 120000, // Refetch every 2 minutes (reduced frequency)
    refetchOnWindowFocus: false, // Prevent refetch on tab focus
    retry: 2,
    retryDelay: 1000,
    staleTime: 60000, // Consider data fresh for 1 minute
    gcTime: 120000, // Keep in cache for 2 minutes
  });
}

/**
 * Hook for fetching SEC filings
 */
export function useFetchSECFilings() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ ticker, forms }) => apiClient.fetchSECFilings(ticker, forms),
    onSuccess: () => {
      // Invalidate relevant queries after successful fetch
      queryClient.invalidateQueries({ queryKey: ['filings'] });
    },
  });
}

/**
 * Hook for uploading files
 */
export function useUploadFile() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ file, ticker }) => apiClient.uploadFile(file, ticker),
    onSuccess: () => {
      // Invalidate relevant queries after successful upload
      queryClient.invalidateQueries({ queryKey: ['documents'] });
    },
  });
}

/**
 * Hook for chat
 */
export function useChat() {
  return useMutation({
    mutationFn: (payload) => {
      if (payload.streamMode) {
        return apiClient.chatStream(payload);
      }
      const { ticker, question, modelProvider, searchMode, sources, enable_rerank, enable_query_rewrite, enable_retrieval_cache, enable_section_boost, reranker_model, stream } = payload;
      return apiClient.chat({ ticker, question, modelProvider, searchMode, sources, enable_rerank, enable_query_rewrite, enable_retrieval_cache, enable_section_boost, reranker_model, stream });
    },
  });
}

export function useCompare() {
  return useMutation({
    mutationFn: (payload) => apiClient.compare(payload),
  });
}
