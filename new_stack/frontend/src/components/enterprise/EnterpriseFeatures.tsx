import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { AlertCircle, Globe, CheckCircle, XCircle, Loader2, Bot } from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../lib/api';

interface GeoRegion {
  name: string;
  score: number;
  latency: number;
}

interface GeoStats {
  global_avg_performance: number;
  worst_region: string;
  variance: number;
  regions: GeoRegion[];
}

export const GeoTestingPanel: React.FC<{ domainId: number }> = ({ domainId }) => {
  const [isRunning, setIsRunning] = useState(false);
  const queryClient = useQueryClient();

  const { data: stats, isLoading } = useQuery({
    queryKey: ['geo-stats', domainId],
    queryFn: async () => {
      const res = await api.get(`/domains/${domainId}/geo-stats`);
      return res.data.data as GeoStats;
    },
    enabled: !isRunning
  });

  const runGeoTest = useMutation({
    mutationFn: async () => {
      setIsRunning(true);
      return api.post(`/domains/${domainId}/geo-test`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['geo-stats', domainId] });
      setTimeout(() => setIsRunning(false), 2000);
    },
    onError: () => setIsRunning(false)
  });

  const getScoreColor = (score: number) => {
    if (score >= 90) return 'text-green-600';
    if (score >= 75) return 'text-yellow-600';
    return 'text-red-600';
  };

  if (isLoading) {
    return <div className="flex items-center justify-center p-8"><Loader2 className="animate-spin h-8 w-8" /></div>;
  }

  return (
    <Card className="mb-6">
      <CardHeader className="flex flex-row items-center justify-between">
        <div className="flex items-center gap-2">
          <Globe className="h-5 w-5 text-blue-600" />
          <CardTitle>Гео-тестирование</CardTitle>
        </div>
        <Button 
          onClick={() => runGeoTest.mutate()} 
          disabled={isRunning}
          size="sm"
        >
          {isRunning ? <Loader2 className="animate-spin h-4 w-4 mr-2" /> : <Globe className="h-4 w-4 mr-2" />}
          Запустить тесты
        </Button>
      </CardHeader>
      <CardContent>
        {stats && (
          <div className="space-y-4">
            <div className="grid grid-cols-3 gap-4 mb-4">
              <div className="text-center p-3 bg-gray-50 rounded-lg">
                <div className="text-sm text-gray-500">Средний балл</div>
                <div className={`text-2xl font-bold ${getScoreColor(stats.global_avg_performance)}`}>
                  {stats.global_avg_performance}
                </div>
              </div>
              <div className="text-center p-3 bg-gray-50 rounded-lg">
                <div className="text-sm text-gray-500">Вариативность</div>
                <div className="text-2xl font-bold text-gray-700">{stats.variance}%</div>
              </div>
              <div className="text-center p-3 bg-gray-50 rounded-lg">
                <div className="text-sm text-gray-500">Худший регион</div>
                <div className="text-lg font-bold text-red-600 capitalize">{stats.worst_region.replace('-', ' ')}</div>
              </div>
            </div>

            <div className="space-y-2">
              <h4 className="font-medium text-sm text-gray-500">Регионы</h4>
              {stats.regions.map((region) => (
                <div key={region.name} className="flex items-center justify-between p-2 border rounded hover:bg-gray-50">
                  <div className="flex items-center gap-2">
                    <Globe className="h-4 w-4 text-gray-400" />
                    <span className="capitalize font-medium">{region.name.replace('-', ' ')}</span>
                  </div>
                  <div className="flex items-center gap-4">
                    <span className="text-sm text-gray-500">{region.latency}ms</span>
                    <Badge variant={region.score >= 90 ? "default" : region.score >= 75 ? "secondary" : "destructive"}>
                      {region.score}
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

interface AIRecommendation {
  id: string;
  title: string;
  description: string;
  priority: 'high' | 'medium' | 'low';
  estimatedImprovement: string;
  codeExample?: string;
}

export const AIAssistantPanel: React.FC<{ domainId: number }> = ({ domainId }) => {
  const [recommendations, setRecommendations] = useState<AIRecommendation[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [aiStatus, setAiStatus] = useState<any>(null);

  // Проверка статуса AI при загрузке
  React.useEffect(() => {
    api.get('/ai/status').then(res => setAiStatus(res.data.data));
  }, []);

  const analyzeWithAI = useMutation({
    mutationFn: async () => {
      setIsLoading(true);
      const res = await api.post(`/domains/${domainId}/ai-analyze`, { metric_type: 'performance' });
      return res.data.data;
    },
    onSuccess: (data) => {
      setRecommendations(data.recommendations);
      setIsLoading(false);
    },
    onError: () => setIsLoading(false)
  });

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high': return 'bg-red-100 text-red-800 border-red-200';
      case 'medium': return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'low': return 'bg-blue-100 text-blue-800 border-blue-200';
      default: return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  return (
    <Card className="mb-6">
      <CardHeader className="flex flex-row items-center justify-between">
        <div className="flex items-center gap-2">
          <Bot className="h-5 w-5 text-purple-600" />
          <CardTitle>AI Ассистент</CardTitle>
        </div>
        <div className="flex items-center gap-2">
          {aiStatus && (
            <Badge variant={aiStatus.openai_configured ? "default" : "secondary"} className="text-xs">
              {aiStatus.openai_configured ? 'GPT-4o' : 'Rule-based'}
            </Badge>
          )}
          <Button onClick={() => analyzeWithAI.mutate()} disabled={isLoading} size="sm">
            {isLoading ? <Loader2 className="animate-spin h-4 w-4 mr-2" /> : <Bot className="h-4 w-4 mr-2" />}
            Анализировать
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {isLoading && (
          <div className="flex flex-col items-center justify-center py-8 text-gray-500">
            <Loader2 className="animate-spin h-8 w-8 mb-2" />
            <p>AI анализирует метрики и готовит рекомендации...</p>
          </div>
        )}

        {!isLoading && recommendations.length === 0 && (
          <div className="text-center py-8 text-gray-500">
            <Bot className="h-12 w-12 mx-auto mb-2 opacity-20" />
            <p>Нажмите "Анализировать", чтобы получить рекомендации по улучшению</p>
            {aiStatus && !aiStatus.openai_configured && (
              <p className="text-xs mt-2 text-yellow-600">Работает в режиме Rule-based (без OpenAI API ключа)</p>
            )}
          </div>
        )}

        <div className="space-y-4">
          {recommendations.map((rec) => (
            <div key={rec.id} className="border rounded-lg p-4 hover:shadow-md transition-shadow">
              <div className="flex items-start justify-between mb-2">
                <h4 className="font-semibold text-gray-900">{rec.title}</h4>
                <span className={`px-2 py-1 rounded-full text-xs font-medium border ${getPriorityColor(rec.priority)}`}>
                  {rec.priority === 'high' ? 'Высокий' : rec.priority === 'medium' ? 'Средний' : 'Низкий'} приоритет
                </span>
              </div>
              <p className="text-sm text-gray-600 mb-3">{rec.description}</p>
              
              {rec.codeExample && (
                <div className="bg-gray-900 text-gray-100 p-3 rounded-md text-xs font-mono overflow-x-auto mb-2">
                  <pre>{rec.codeExample}</pre>
                </div>
              )}
              
              <div className="flex items-center gap-2 text-xs text-green-600 font-medium">
                <CheckCircle className="h-3 w-3" />
                Потенциальное улучшение: {rec.estimatedImprovement}
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
};
