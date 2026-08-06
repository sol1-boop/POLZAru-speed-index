import React, { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { Badge } from './ui/badge';
import { Loader2, Globe, TrendingUp, AlertCircle } from 'lucide-react';
import api from '../lib/api';

interface GeoLocation {
  key: string;
  name: string;
  city: string;
  country: string;
  timezone: string;
}

interface GeoResult {
  location: string;
  city: string;
  country: string;
  score: number;
  lcp: number;
  fid: number;
  cls: number;
}

interface GeoComparisonProps {
  domainId: number;
  url: string;
}

export const GeoComparison: React.FC<GeoComparisonProps> = ({ domainId, url }) => {
  const [selectedLocations, setSelectedLocations] = useState<string[]>(['moscow', 'london', 'new_york']);
  const [isRunning, setIsRunning] = useState(false);

  const { data: locations } = useQuery<GeoLocation[]>({
    queryKey: ['geo-locations'],
    queryFn: async () => {
      const response = await api.get('/api/v1/geo/locations');
      return response.data;
    }
  });

  const { data: lastResults, refetch } = useQuery<{ results: GeoResult[] }>({
    queryKey: ['geo-results', domainId],
    queryFn: async () => {
      const response = await api.get(`/api/v1/domains/${domainId}/geo-tests/latest`);
      return response.data;
    },
    enabled: false
  });

  const runTestMutation = useMutation({
    mutationFn: async (locs: string[]) => {
      const response = await api.post(`/api/v1/domains/${domainId}/geo-tests`, {
        url,
        locations: locs
      });
      return response.data;
    },
    onMutate: () => setIsRunning(true),
    onSuccess: () => {
      setIsRunning(false);
      refetch();
    },
    onError: () => setIsRunning(false)
  });

  const handleRunTest = () => {
    runTestMutation.mutate(selectedLocations);
  };

  const handleLocationToggle = (locationKey: string) => {
    setSelectedLocations(prev => 
      prev.includes(locationKey)
        ? prev.filter(l => l !== locationKey)
        : [...prev, locationKey]
    );
  };

  if (!locations) return null;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Globe className="w-5 h-5" />
          Гео-тестирование
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <div>
            <label className="text-sm font-medium mb-2 block">Выберите локации:</label>
            <div className="flex flex-wrap gap-2">
              {locations.map(loc => (
                <Button
                  key={loc.key}
                  variant={selectedLocations.includes(loc.key) ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => handleLocationToggle(loc.key)}
                >
                  {loc.city}, {loc.country}
                </Button>
              ))}
            </div>
          </div>

          <Button 
            onClick={handleRunTest} 
            disabled={isRunning || selectedLocations.length === 0}
            className="w-full"
          >
            {isRunning && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
            Запустить тесты из {selectedLocations.length} локаций
          </Button>

          {lastResults && lastResults.results && lastResults.results.length > 0 && (
            <div className="mt-6">
              <h4 className="font-semibold mb-3">Результаты:</h4>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {lastResults.results.map((result: GeoResult, idx: number) => (
                  <Card key={idx}>
                    <CardContent className="pt-4">
                      <div className="flex justify-between items-start mb-2">
                        <div>
                          <p className="font-medium">{result.city}</p>
                          <p className="text-xs text-muted-foreground">{result.country}</p>
                        </div>
                        <Badge variant={result.score >= 90 ? 'success' : result.score >= 75 ? 'warning' : 'destructive'}>
                          {result.score}
                        </Badge>
                      </div>
                      <div className="space-y-1 text-sm">
                        <div className="flex justify-between">
                          <span>LCP:</span>
                          <span>{result.lcp.toFixed(2)}s</span>
                        </div>
                        <div className="flex justify-between">
                          <span>FID:</span>
                          <span>{result.fid.toFixed(0)}ms</span>
                        </div>
                        <div className="flex justify-between">
                          <span>CLS:</span>
                          <span>{result.cls.toFixed(3)}</span>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>

              {lastResults.summary && (
                <Card className="mt-4 bg-blue-50">
                  <CardContent className="pt-4">
                    <div className="flex items-center gap-2 mb-2">
                      <TrendingUp className="w-4 h-4 text-blue-600" />
                      <span className="font-medium text-blue-900">Статистика</span>
                    </div>
                    <div className="grid grid-cols-3 gap-4 text-sm">
                      <div>
                        <span className="text-muted-foreground">Средний балл:</span>
                        <p className="font-semibold">{lastResults.summary.avg_score?.toFixed(1)}</p>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Разброс:</span>
                        <p className="font-semibold">{lastResults.summary.variance?.toFixed(1)}</p>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Локаций:</span>
                        <p className="font-semibold">{lastResults.results.length}</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
};

export default GeoComparison;
