/**
 * Страница аналитики домена.
 * Отображает графики трендов и список аномалий.
 */
import React from 'react';
import { useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { PerformanceTrendsChart, CoreWebVitalsChart, AnomaliesList } from '@/components/analytics/TrendsChart';
import { Skeleton } from "@/components/ui/skeleton";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

// API запросы
const fetchDomainTrends = async (domainId: number, days: number = 30) => {
  const response = await fetch(`/api/analytics/domains/${domainId}/trends?days=${days}`);
  if (!response.ok) throw new Error('Failed to fetch trends');
  return response.json();
};

const fetchAnomalies = async (domainId: number) => {
  const response = await fetch(`/api/analytics/domains/${domainId}/anomalies`);
  if (!response.ok) throw new Error('Failed to fetch anomalies');
  return response.json();
};

export const DomainAnalyticsPage: React.FC = () => {
  const { domainId } = useParams<{ domainId: string }>();
  const id = parseInt(domainId || '0', 10);

  const { data: trendsData, isLoading: trendsLoading } = useQuery({
    queryKey: ['domainTrends', id],
    queryFn: () => fetchDomainTrends(id),
    enabled: !!id
  });

  const { data: anomaliesData, isLoading: anomaliesLoading } = useQuery({
    queryKey: ['domainAnomalies', id],
    queryFn: () => fetchAnomalies(id),
    enabled: !!id
  });

  if (trendsLoading || anomaliesLoading) {
    return (
      <div className="space-y-4 p-6">
        <Skeleton className="h-[400px] w-full" />
        <Skeleton className="h-[400px] w-full" />
        <Skeleton className="h-[200px] w-full" />
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold">Аналитика: {trendsData?.domain}</h1>
        <div className="text-sm text-muted-foreground">
          Данные за последние {trendsData?.period_days} дней ({trendsData?.data_points} замеров)
        </div>
      </div>

      {/* Блок аномалий */}
      {anomaliesData && (
        <AnomaliesList anomalies={anomaliesData.anomalies || []} />
      )}

      {/* Графики */}
      <div className="grid gap-6 md:grid-cols-2">
        {trendsData?.metrics && (
          <>
            <PerformanceTrendsChart 
              data={trendsData.metrics} 
              title="Общие метрики производительности" 
            />
            <CoreWebVitalsChart 
              data={trendsData.metrics} 
              title="Core Web Vitals (детально)" 
            />
          </>
        )}
      </div>

      {/* Сводная статистика */}
      <Card>
        <CardHeader>
          <CardTitle>Статистика периода</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="p-4 bg-slate-50 rounded-lg">
              <div className="text-sm text-muted-foreground">Средний Performance</div>
              <div className="text-2xl font-bold">
                {trendsData?.metrics?.length 
                  ? Math.round(trendsData.metrics.reduce((acc, m) => acc + m.performance, 0) / trendsData.metrics.length) 
                  : 0}
              </div>
            </div>
            <div className="p-4 bg-slate-50 rounded-lg">
              <div className="text-sm text-muted-foreground">Средний LCP</div>
              <div className="text-2xl font-bold">
                {trendsData?.metrics?.length 
                  ? Math.round(trendsData.metrics.reduce((acc, m) => acc + (m.lcp || 0), 0) / trendsData.metrics.length) 
                  : 0} ms
              </div>
            </div>
            <div className="p-4 bg-slate-50 rounded-lg">
              <div className="text-sm text-muted-foreground">Средний CLS</div>
              <div className="text-2xl font-bold">
                {trendsData?.metrics?.length 
                  ? (trendsData.metrics.reduce((acc, m) => acc + (m.cls || 0), 0) / trendsData.metrics.length).toFixed(3) 
                  : 0}
              </div>
            </div>
            <div className="p-4 bg-slate-50 rounded-lg">
              <div className="text-sm text-muted-foreground">Тренд</div>
              <div className="text-2xl font-bold text-green-600">
                {anomaliesData?.anomalies_detected === 0 ? 'Стабильный' : 'Деградация'}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};
