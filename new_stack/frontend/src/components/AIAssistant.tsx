import React, { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { AlertCircle, CheckCircle, Lightbulb, Download } from 'lucide-react';
import api from '../lib/api';

interface Issue {
  metric: string;
  severity: 'critical' | 'warning' | 'info';
  title: string;
  description: string;
  threshold: string;
  current_value: number;
}

interface AIAnalysis {
  summary: {
    total_issues: number;
    critical: number;
    warnings: number;
    performance_score: number;
  };
  issues: Issue[];
  recommendations: string[];
  priority_actions: string[];
}

interface AIAssistantProps {
  domainId: number;
  metrics: {
    performance_score: number;
    lcp: number;
    fid: number;
    cls: number;
    fcp: number;
  };
}

export const AIAssistant: React.FC<AIAssistantProps> = ({ domainId, metrics }) => {
  const [showReport, setShowReport] = useState(false);
  const [analysis, setAnalysis] = useState<AIAnalysis | null>(null);

  const analyzeMutation = useMutation({
    mutationFn: async () => {
      const response = await api.post(`/api/v1/domains/${domainId}/ai/analyze`, { metrics });
      return response.data as AIAnalysis;
    },
    onSuccess: (data) => {
      setAnalysis(data);
      setShowReport(true);
    }
  });

  const reportMutation = useMutation({
    mutationFn: async () => {
      const response = await api.post(`/api/v1/domains/${domainId}/ai/report`, { metrics });
      return response.data as { report: string };
    },
    onSuccess: (data) => {
      // Скачать отчет как TXT файл
      const blob = new Blob([data.report], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `performance-report-${domainId}-${new Date().toISOString().split('T')[0]}.txt`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    }
  });

  const handleAnalyze = () => {
    analyzeMutation.mutate();
  };

  const handleDownloadReport = () => {
    reportMutation.mutate();
  };

  if (!analysis && !showReport) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Lightbulb className="w-5 h-5 text-yellow-500" />
            AI-ассистент по оптимизации
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground mb-4">
            Получите персонализированные рекомендации по улучшению производительности вашего сайта.
          </p>
          <Button onClick={handleAnalyze} disabled={analyzeMutation.isPending}>
            {analyzeMutation.isPending ? 'Анализ...' : 'Запустить анализ'}
          </Button>
        </CardContent>
      </Card>
    );
  }

  if (!analysis) return null;

  return (
    <Card>
      <CardHeader>
        <div className="flex justify-between items-start">
          <CardTitle className="flex items-center gap-2">
            <Lightbulb className="w-5 h-5 text-yellow-500" />
            Рекомендации AI
          </CardTitle>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={handleDownloadReport}>
              <Download className="w-4 h-4 mr-2" />
              Отчет
            </Button>
            <Button variant="ghost" size="sm" onClick={() => setShowReport(false)}>
              Закрыть
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Summary */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Card>
            <CardContent className="pt-4">
              <p className="text-sm text-muted-foreground">Performance Score</p>
              <p className={`text-2xl font-bold ${
                analysis.summary.performance_score >= 90 ? 'text-green-600' :
                analysis.summary.performance_score >= 75 ? 'text-yellow-600' : 'text-red-600'
              }`}>
                {analysis.summary.performance_score.toFixed(0)}
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-4">
              <p className="text-sm text-muted-foreground">Проблем</p>
              <p className="text-2xl font-bold">{analysis.summary.total_issues}</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-4">
              <p className="text-sm text-muted-foreground">Критичных</p>
              <p className="text-2xl font-bold text-red-600">{analysis.summary.critical}</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-4">
              <p className="text-sm text-muted-foreground">Предупреждений</p>
              <p className="text-2xl font-bold text-yellow-600">{analysis.summary.warnings}</p>
            </CardContent>
          </Card>
        </div>

        {/* Issues */}
        {analysis.issues.length > 0 && (
          <div>
            <h4 className="font-semibold mb-3 flex items-center gap-2">
              <AlertCircle className="w-4 h-4" />
              Найденные проблемы
            </h4>
            <div className="space-y-3">
              {analysis.issues.map((issue, idx) => (
                <Card key={idx} className={issue.severity === 'critical' ? 'border-red-200 bg-red-50' : 'border-yellow-200 bg-yellow-50'}>
                  <CardContent className="pt-4">
                    <div className="flex items-start gap-3">
                      {issue.severity === 'critical' ? (
                        <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
                      ) : (
                        <AlertCircle className="w-5 h-5 text-yellow-600 flex-shrink-0 mt-0.5" />
                      )}
                      <div className="flex-1">
                        <div className="flex justify-between items-start">
                          <p className="font-medium">{issue.title}</p>
                          <Badge variant={issue.severity === 'critical' ? 'destructive' : 'warning'}>
                            {issue.severity === 'critical' ? 'Критично' : 'Внимание'}
                          </Badge>
                        </div>
                        <p className="text-sm text-muted-foreground mt-1">{issue.description}</p>
                        <p className="text-xs mt-2">
                          Текущее: <strong>{issue.current_value}</strong> | Порог: <strong>{issue.threshold}</strong>
                        </p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        )}

        {/* Priority Actions */}
        {analysis.priority_actions.length > 0 && (
          <div>
            <h4 className="font-semibold mb-3 flex items-center gap-2">
              <CheckCircle className="w-4 h-4 text-green-600" />
              Приоритетные действия
            </h4>
            <ol className="space-y-2">
              {analysis.priority_actions.map((action, idx) => (
                <li key={idx} className="flex items-start gap-3">
                  <span className="flex-shrink-0 w-6 h-6 rounded-full bg-green-100 text-green-800 text-sm font-medium flex items-center justify-center">
                    {idx + 1}
                  </span>
                  <span className="text-sm">{action}</span>
                </li>
              ))}
            </ol>
          </div>
        )}

        {/* All Recommendations */}
        {analysis.recommendations.length > 0 && (
          <div>
            <h4 className="font-semibold mb-3 flex items-center gap-2">
              <Lightbulb className="w-4 h-4 text-blue-600" />
              Все рекомендации
            </h4>
            <ul className="space-y-2">
              {analysis.recommendations.map((rec, idx) => (
                <li key={idx} className="flex items-start gap-2 text-sm">
                  <span className="text-blue-600 mt-1">•</span>
                  <span>{rec}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default AIAssistant;
