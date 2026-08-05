import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { domainsApi } from '../api/client'

export function useDomains() {
  return useQuery({
    queryKey: ['domains'],
    queryFn: () => domainsApi.getDomains(),
  })
}

export function useDomain(id: number) {
  return useQuery({
    queryKey: ['domain', id],
    queryFn: () => domainsApi.getDomain(id),
    enabled: !!id,
  })
}

export function useCreateDomain() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: (data: { url: string; name?: string; check_interval_minutes?: number }) =>
      domainsApi.createDomain(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['domains'] })
    },
  })
}

export function useUpdateDomain() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: any }) =>
      domainsApi.updateDomain(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['domains'] })
    },
  })
}

export function useDeleteDomain() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: (id: number) => domainsApi.deleteDomain(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['domains'] })
    },
  })
}

export function useDomainMetrics(domainId: number, limit: number = 50) {
  return useQuery({
    queryKey: ['metrics', domainId],
    queryFn: () => domainsApi.getMetrics(domainId, limit),
    enabled: !!domainId,
  })
}

export function useTriggerCheck() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: (domainId: number) => domainsApi.triggerCheck(domainId),
    onSuccess: (_, domainId) => {
      queryClient.invalidateQueries({ queryKey: ['metrics', domainId] })
    },
  })
}
